import html
import ipaddress
import json
import logging
import secrets
import time
from pathlib import Path
from threading import RLock
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import Settings
from app.core.utils import uid, digest
from app.domain.models import (
    Role,
    GateAssessment,
    Project,
    ReviewDecision,
    ReviewStatus,
    PublicationStatus,
    PublicationApproval,
    MiroPublication,
    GateRequirement,
    EvidenceDocument,
    AssessmentFinding,
    AuditEvent,
)
from app.persistence.store import Store
from app.schemas.responses import ProjectDetail, ValueCaseResponse
from app.schemas.requests import DemoLogin, ReviewRequest, ApprovalRequest, PublishRequest
from app.services.evidence.index import load_fixtures, snapshot, snapshot_hash, EvidenceIndex
from app.services.assessment.engine import assess
from app.services.ai.explainer import TemplateExplainer, LLMExplainer, Explanation
from app.services.miro.scene import build_board_scene, render_html
from app.services.miro.adapter import MockMiroAdapter, RestMiroAdapter, MiroError
from app.services.value.calculator import value_case
from app.services.report import executive_report

logger = logging.getLogger("copilot")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    if config.app_mode != "demo":
        raise RuntimeError("Production mode requires a real identity provider; demo sessions are disabled")
    if config.miro_mode not in ["mock", "live"]:
        raise RuntimeError("Unsupported Miro mode")
    store = Store(config.database_path)
    load_fixtures(store)
    adapter = (
        RestMiroAdapter(store, config.miro_token, config.allow_live_miro)
        if config.miro_mode == "live"
        else MockMiroAdapter(store)
    )
    if config.miro_mode == "mock":
        store.put(
            "mock_board",
            config.miro_board,
            {"id": config.miro_board, "name": "Northstar · Mock workspace", "mode": "mock"},
        )
    app = FastAPI(
        title="Manufacturing Gate Copilot",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        responses={
            401: {"description": "Demo session required"},
            403: {"description": "Permission denied"},
            404: {"description": "Record not found"},
            409: {"description": "Workflow conflict or stale version"},
        },
    )
    app.state.store = store
    app.state.adapter = adapter
    app.state.settings = config
    sessions: dict[str, dict] = {}
    workflow_lock = RLock()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        request.state.correlation_id = uid("REQ")
        private_client = False
        if request.client and config.demo_allow_private_clients:
            try:
                private_client = ipaddress.ip_address(request.client.host).is_private
            except ValueError:
                pass
        if (
            request.client
            and request.client.host not in ["127.0.0.1", "::1", "testclient"]
            and not private_client
        ):
            return JSONResponse(status_code=403, content={"detail": "Demo accepts loopback clients only"})
        origin = request.headers.get("origin")
        if (
            request.method not in ["GET", "HEAD", "OPTIONS"]
            and origin
            and origin
            not in [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            ]
        ):
            return JSONResponse(status_code=403, content={"detail": "Origin not authorised"})
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "request_failure",
                        "type": type(exc).__name__,
                        "correlation_id": request.state.correlation_id,
                    }
                )
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Request failed; inspect audit trail",
                    "correlation_id": request.state.correlation_id,
                },
            )
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
        )
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "correlation_id": request.state.correlation_id,
                }
            )
        )
        return response

    @app.exception_handler(KeyError)
    async def missing(request: Request, exc: KeyError):
        return JSONResponse(
            status_code=404,
            content={"detail": "Record not found", "correlation_id": request.state.correlation_id},
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.error(
            json.dumps(
                {
                    "event": "request_failure",
                    "type": type(exc).__name__,
                    "correlation_id": request.state.correlation_id,
                }
            )
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Request failed; inspect audit trail",
                "correlation_id": request.state.correlation_id,
            },
        )

    def identity(request: Request) -> dict:
        token = request.cookies.get("copilot_session", "")
        session = sessions.get(token)
        if not session or session["expires"] < time.time():
            raise HTTPException(401, "Sign in with a local demo identity")
        return session

    User = Annotated[dict, Depends(identity)]

    def permit(user: dict, *roles: Role) -> None:
        if user["role"] not in roles:
            raise HTTPException(403, "This demo identity does not have the required permission")

    def get_assessment(aid: str) -> GateAssessment:
        return GateAssessment.model_validate(store.get("assessment", aid))

    def latest(project_id: str) -> GateAssessment | None:
        records = [a for a in store.all("assessment") if a["project_id"] == project_id]
        return (
            GateAssessment.model_validate(max(records, key=lambda a: a["assessment_version"]))
            if records
            else None
        )

    def ensure_current(a: GateAssessment) -> None:
        newest = latest(a.project_id)
        if (
            not newest
            or newest.id != a.id
            or a.source_snapshot_hash != snapshot_hash(snapshot(store, a.project_id))
        ):
            supersede(a.id, "system", "snapshot-check")
            raise HTTPException(409, "Assessment superseded or sources changed; run a fresh assessment")

    def scene_for(a: GateAssessment):
        return build_board_scene(
            a, Project.model_validate(store.get("project", a.project_id)), value_case(store, a.project_id)
        )

    def supersede(aid: str, actor: str, cid: str) -> None:
        for raw in store.all("approval"):
            if raw["assessment_id"] == aid and raw["status"] not in ["SUPERSEDED"]:
                raw["status"] = "SUPERSEDED"
                store.put("approval", raw["id"], raw)
                store.audit(actor, "approval_superseded", raw["id"], cid)
        store.put("workspace", aid, {"assessment_id": aid, "status": "PREVIEW"})

    @app.get("/health")
    def health():
        return {"status": "ok", "synthetic": True, "miro_mode": config.miro_mode}

    @app.get("/api/v1/capabilities")
    def capabilities():
        return {
            "identity_mode": "Local demo — non-production",
            "miro_mode": config.miro_mode,
            "destination_board": config.miro_board,
            "llm_enabled": config.llm_enabled,
        }

    @app.post("/api/v1/demo-sessions")
    def login(body: DemoLogin, response: Response):
        token = secrets.token_urlsafe(32)
        sessions[token] = {
            "actor": f"demo-{body.role.value.lower()}",
            "role": body.role,
            "expires": time.time() + 8 * 3600,
        }
        response.set_cookie("copilot_session", token, httponly=True, samesite="strict", max_age=8 * 3600)
        return {"actor": sessions[token]["actor"], "role": body.role, "non_production": True}

    @app.get("/api/v1/session")
    def session(user: User):
        return {"actor": user["actor"], "role": user["role"], "non_production": True}

    @app.delete("/api/v1/demo-sessions")
    def logout(request: Request, response: Response, user: User):
        sessions.pop(request.cookies.get("copilot_session", ""), None)
        response.delete_cookie("copilot_session")
        return {"signed_out": True}

    @app.get("/api/v1/projects", response_model=list[Project])
    def projects(user: User):
        return store.all("project")

    @app.get("/api/v1/projects/{pid}", response_model=ProjectDetail)
    def project(pid: str, user: User):
        return {
            **store.get("project", pid),
            "gate": store.get("gate", store.get("project", pid)["gate_id"]),
            "latest_assessment": latest(pid),
        }

    @app.get("/api/v1/projects/{pid}/requirements", response_model=list[GateRequirement])
    def requirements(pid: str, user: User):
        store.get("project", pid)
        return [r for r in store.all("requirement") if r["project_id"] == pid]

    @app.get("/api/v1/projects/{pid}/evidence", response_model=list[EvidenceDocument])
    def evidence(pid: str, user: User, q: str = ""):
        index = EvidenceIndex(snapshot(store, pid)["evidence"])
        return index.search(q) if q else index.documents

    @app.get("/api/v1/projects/{pid}/records")
    def records(pid: str, user: User):
        s = snapshot(store, pid)
        return {k: s[k] for k in ["issue", "change", "action", "policy"]}

    @app.post("/api/v1/projects/{pid}/assessments", status_code=201, response_model=GateAssessment)
    def run_assessment(pid: str, request: Request, user: User):
        permit(user, Role.ANALYST)
        with workflow_lock:
            current = latest(pid)
            a = assess(snapshot(store, pid), current.assessment_version + 1 if current else 1)
            if current:
                supersede(current.id, user["actor"], request.state.correlation_id)
            store.put("assessment", a.id, a)
            store.put("workspace", a.id, {"assessment_id": a.id, "status": "PREVIEW"})
            store.audit(
                user["actor"],
                "assessed",
                a.id,
                request.state.correlation_id,
                version=a.assessment_version,
                snapshot=a.source_snapshot_hash,
            )
        return a

    @app.get("/api/v1/assessments/{aid}", response_model=GateAssessment)
    def assessment(aid: str, user: User):
        return get_assessment(aid)

    @app.get("/api/v1/assessments/{aid}/findings", response_model=list[AssessmentFinding])
    def findings(aid: str, user: User):
        return get_assessment(aid).findings

    @app.get("/api/v1/assessments/{aid}/explanation", response_model=Explanation)
    def explanation(aid: str, request: Request, user: User):
        a = get_assessment(aid)
        cache_id = digest(
            {"assessment": a.model_dump(mode="json"), "model": config.llm_model, "contract": "plan-v2"}
        )
        if config.llm_enabled:
            cached = next((e for e in store.all("explanation") if e["cache_id"] == cache_id), None)
            if cached:
                return Explanation.model_validate(cached["result"])
        explainer = (
            LLMExplainer(config.llm_model, timeout_seconds=config.llm_timeout_seconds)
            if config.llm_enabled
            else TemplateExplainer()
        )
        result = explainer.generate(a, a.source_records["evidence"])
        if config.llm_enabled:
            store.audit(
                user["actor"],
                "explanation_generated",
                aid,
                request.state.correlation_id,
                provider=result.provider,
                runtime_status=result.runtime_status,
                model=result.model,
                fallback_reason=result.fallback_reason,
            )
            if result.runtime_status == "model_used":
                store.put(
                    "explanation", cache_id, {"cache_id": cache_id, "result": result.model_dump(mode="json")}
                )
        return result

    @app.get("/api/v1/assessments/{aid}/scene")
    def scene(aid: str, user: User):
        result = scene_for(get_assessment(aid))
        return {**result.model_dump(mode="json"), "content_hash": result.content_hash}

    @app.get("/api/v1/assessments/{aid}/board-preview", response_class=HTMLResponse)
    def preview(aid: str, user: User):
        return render_html(scene_for(get_assessment(aid)))

    @app.post("/api/v1/assessments/{aid}/review", response_model=GateAssessment)
    def review(aid: str, body: ReviewRequest, request: Request, user: User):
        permit(user, Role.REVIEWER)
        with workflow_lock:
            a = get_assessment(aid)
            ensure_current(a)
            d = ReviewDecision(
                id=uid("DEC"),
                assessment_id=aid,
                assessment_version=a.assessment_version,
                actor=user["actor"],
                decision=body.decision,
                note=body.note,
            )
            a.decisions.append(d)
            a.review_status = ReviewStatus.REVIEWED
            supersede(aid, user["actor"], request.state.correlation_id)
            store.put("decision", d.id, d)
            store.put("assessment", aid, a)
            store.audit(user["actor"], "reviewed", aid, request.state.correlation_id, decision=body.decision)
        return a

    @app.post("/api/v1/assessments/{aid}/publication-approvals", response_model=PublicationApproval)
    def approval(aid: str, body: ApprovalRequest, request: Request, user: User):
        with workflow_lock:
            a = get_assessment(aid)
            ensure_current(a)
            if body.destination_board != config.miro_board:
                raise HTTPException(400, "Destination must match the configured authorised board")
            if not a.decisions or a.decisions[-1].decision != "ACKNOWLEDGED":
                raise HTTPException(
                    409, "Reviewer acknowledgement required; changes requested remain unresolved"
                )
            scene = scene_for(a)
            if body.action == "request":
                permit(user, Role.ANALYST, Role.PUBLISHER)
                supersede(aid, user["actor"], request.state.correlation_id)
                p = PublicationApproval(
                    id=uid("APR"),
                    assessment_id=aid,
                    assessment_version=a.assessment_version,
                    scene_content_hash=scene.content_hash,
                    actor=user["actor"],
                    destination_board=body.destination_board,
                    status=PublicationStatus.APPROVAL_PENDING,
                )
            else:
                permit(user, Role.PUBLISHER)
                candidates = [
                    v
                    for v in store.all("approval")
                    if v["assessment_id"] == aid and v["status"] == "APPROVAL_PENDING"
                ]
                if len(candidates) != 1:
                    raise HTTPException(409, "Request publication approval first")
                p = PublicationApproval.model_validate(candidates[0])
                if (
                    p.scene_content_hash != scene.content_hash
                    or p.assessment_version != a.assessment_version
                    or p.destination_board != body.destination_board
                ):
                    p.status = PublicationStatus.SUPERSEDED
                    store.put("approval", p.id, p)
                    raise HTTPException(409, "Scene changed; request approval again")
                p.actor = user["actor"]
                p.status = PublicationStatus.APPROVED
            store.put("approval", p.id, p)
            store.put("workspace", aid, {"assessment_id": aid, "status": p.status, "approval_id": p.id})
            store.audit(
                user["actor"],
                f"publication_{p.status.value.lower()}",
                p.id,
                request.state.correlation_id,
                scene_hash=p.scene_content_hash,
                destination=p.destination_board,
            )
        return p

    @app.get("/api/v1/assessments/{aid}/publication")
    def publication_state(aid: str, user: User):
        get_assessment(aid)
        return {
            "workspace": store.get("workspace", aid),
            "approvals": [p for p in store.all("approval") if p["assessment_id"] == aid],
            "publications": sorted(
                [p for p in store.all("publication") if p["assessment_id"] == aid],
                key=lambda p: p["timestamp"],
            ),
            "mappings": app.state.adapter.list_managed_items(config.miro_board),
            "mode": config.miro_mode,
        }

    @app.post("/api/v1/assessments/{aid}/publish", response_model=MiroPublication)
    def publish(aid: str, body: PublishRequest, request: Request, user: User):
        permit(user, Role.PUBLISHER)
        with workflow_lock:
            a = get_assessment(aid)
            ensure_current(a)
            p = PublicationApproval.model_validate(store.get("approval", body.approval_id))
            scene = scene_for(a)
            if (
                p.assessment_id != aid
                or p.status != PublicationStatus.APPROVED
                or p.assessment_version != a.assessment_version
                or p.destination_board != config.miro_board
                or p.scene_content_hash != scene.content_hash
            ):
                if p.assessment_id == aid and p.status == PublicationStatus.APPROVED:
                    p.status = PublicationStatus.SUPERSEDED
                    store.put("approval", p.id, p)
                    store.audit(user["actor"], "approval_superseded", p.id, request.state.correlation_id)
                raise HTTPException(409, "Valid scene-bound approval required")
            if not store.get("project", a.project_id)["synthetic"]:
                raise HTTPException(403, "Only synthetic data may be published")
            publication = MiroPublication(
                id=uid("PUB"),
                assessment_id=aid,
                approval_id=p.id,
                destination_board=p.destination_board,
                status=PublicationStatus.PUBLISHING,
                mode="live" if config.miro_mode == "live" else "mock",
                scene_content_hash=scene.content_hash,
            )
            if not store.claim_publication(publication.model_dump(mode="json")):
                raise HTTPException(409, "Publication already in progress or requires recovery")
            store.put("workspace", aid, {"assessment_id": aid, "status": "PUBLISHING", "approval_id": p.id})
            store.audit(user["actor"], "publication_publishing", publication.id, request.state.correlation_id)
            try:
                publication.result = app.state.adapter.reconcile_publication(p.destination_board, scene)
                if config.miro_mode == "live":
                    publication.result.update(
                        app.state.adapter.verify_managed_items(p.destination_board, scene)
                    )
                publication.status = PublicationStatus.PUBLISHED
                publication.board_url = (
                    f"https://miro.com/app/board/{p.destination_board}/"
                    if config.miro_mode == "live"
                    else None
                )
            except (MiroError, KeyError) as exc:
                publication.status = PublicationStatus.FAILED
                publication.result = {
                    "message": "Publication incomplete; inspect item operation journal",
                    "ambiguous": getattr(exc, "ambiguous", False),
                }
            store.put("publication", publication.id, publication)
            store.put(
                "workspace", aid, {"assessment_id": aid, "status": publication.status, "approval_id": p.id}
            )
            store.audit(
                user["actor"],
                f"publication_{publication.status.value.lower()}",
                publication.id,
                request.state.correlation_id,
                result=publication.result,
            )
            if publication.status == PublicationStatus.FAILED:
                return JSONResponse(status_code=502, content=publication.model_dump(mode="json"))
        return publication

    @app.get("/api/v1/projects/{pid}/value-case", response_model=ValueCaseResponse)
    def value(pid: str, user: User):
        store.get("project", pid)
        return value_case(store, pid)

    @app.get("/api/v1/projects/{pid}/executive-report", response_class=PlainTextResponse)
    def report(pid: str, user: User):
        a = latest(pid)
        if not a:
            raise HTTPException(409, "Run an assessment before generating the report")
        return PlainTextResponse(
            executive_report(a, Project.model_validate(store.get("project", pid)), value_case(store, pid)),
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="northstar-executive-report.md"'},
        )

    @app.get("/api/v1/audit", response_model=list[AuditEvent])
    def audit(user: User):
        return sorted(store.all("audit"), key=lambda e: e["timestamp"])

    @app.get("/api/v1/publication-operations")
    def operations(user: User):
        permit(user, Role.PUBLISHER)
        return store.all("operation")

    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def local_api_docs():
        schema = app.openapi()
        rows = []
        for path, methods in schema["paths"].items():
            for verb, contract in methods.items():
                rows.append(
                    f"<tr><td>{html.escape(verb.upper())}</td><td><code>{html.escape(path)}</code></td><td>{html.escape(contract.get('summary', ''))}</td></tr>"
                )
        schemas = html.escape(json.dumps(schema.get("components", {}), indent=2))
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Copilot API reference</title><style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#243d43}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}pre{overflow:auto;background:#f1f5f3;padding:20px}a{color:#26735b}</style><h1>Manufacturing Gate Copilot · API v1</h1><p>Offline API reference. <a href="/openapi.json">Download OpenAPI JSON</a>. Sign in through the local demo UI. State-changing endpoints require the appropriate server-issued demo session.</p><table><thead><tr><th>Method</th><th>Endpoint</th><th>Operation</th></tr></thead><tbody>'
            + "".join(rows)
            + "</tbody></table><details><summary>Validated request and response schemas</summary><pre>"
            + schemas
            + "</pre></details></html>"
        )

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def frontend():
            return FileResponse(dist / "index.html")

    return app


app = create_app()
