"""Run deliberately opt-in live checks, returning nonzero on fallback or incomplete checks."""

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.utils import now
from app.domain.models import GateAssessment, Project
from app.persistence.store import Store
from app.services.integration_validation import validate_ollama
from app.services.miro.adapter import RestMiroAdapter, MiroError
from app.services.miro.scene import build_board_scene
from app.services.miro.verification import board_id_from_url, unrelated_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["ollama", "miro-read", "miro-publication"])
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "llama3.2:1b"))
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--board", default=os.getenv("MIRO_BOARD_ID", ""))
    parser.add_argument("--assessment-id")
    parser.add_argument("--approval-id")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = run_validation(args)
    except (MiroError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        result = {
            "target": args.target,
            "status": "FAILED",
            "timestamp": now(),
            "reason": "Validation did not complete; check configuration and the redacted audit trail",
            "error_type": type(exc).__name__,
        }
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "PASSED" else 2


def run_validation(args) -> dict:
    if args.target == "ollama":
        result = validate_ollama(args.model, args.timeout)
    else:
        token = os.getenv("MIRO_OAUTH_TOKEN", "")
        if not token or not args.board:
            result = {
                "target": args.target,
                "status": "BLOCKED",
                "reason": "MIRO_OAUTH_TOKEN and a test board ID/URL are required",
            }
        else:
            board = board_id_from_url(args.board)
            store = Store("data/integration-validation.sqlite3")
            adapter = RestMiroAdapter(store, token, enabled=True)
            info = adapter.get_board(board)
            before = adapter.list_board_items(board)
            result = {
                "target": args.target,
                "status": "PASSED",
                "timestamp": now(),
                "board_id": board,
                "board_accessible": str(info.get("id")) == board,
                "remote_item_count": len(before),
            }
            if not result["board_accessible"]:
                raise MiroError("Unexpected board returned")
            if args.target == "miro-publication":
                if os.getenv("ALLOW_LIVE_MIRO", "false").lower() != "true":
                    raise ValueError(
                        "Set ALLOW_LIVE_MIRO=true only after authorising writes to the test board"
                    )
                if not args.assessment_id or not args.approval_id:
                    raise ValueError(
                        "Provide an existing reviewed assessment and its approved publication ID"
                    )
                server = urlparse(args.server)
                if (
                    server.scheme != "http"
                    or server.hostname not in ["127.0.0.1", "localhost"]
                    or server.username
                    or server.password
                    or server.path not in ["", "/"]
                    or server.query
                    or server.fragment
                ):
                    raise ValueError(
                        "The validation server must be a local loopback HTTP origin"
                    )
                with httpx.Client(
                    base_url=args.server, timeout=180, trust_env=False
                ) as client:

                    def call(method, path, body=None):
                        response = client.request(method, "/api/v1" + path, json=body)
                        if response.is_error:
                            raise ValueError(
                                f"Local workflow rejected validation ({response.status_code}); inspect the local audit trail"
                            )
                        return response.json()

                    call("POST", "/demo-sessions", {"role": "Publisher"})
                    cap = call("GET", "/capabilities")
                    if cap["miro_mode"] != "live" or cap["destination_board"] != board:
                        raise ValueError(
                            "Server live mode and configured destination must match the authorised board"
                        )
                    prefix = f"/assessments/{args.assessment_id}"
                    state = call("GET", prefix + "/publication")
                    approval = next(
                        (
                            p
                            for p in state["approvals"]
                            if p["id"] == args.approval_id and p["status"] == "APPROVED"
                        ),
                        None,
                    )
                    if not approval:
                        raise ValueError(
                            "Current APPROVED publication permission is required"
                        )
                    managed_before = {m["remote_id"] for m in state["mappings"]}
                    unrelated = unrelated_snapshot(before, managed_before)
                    first = call(
                        "POST", prefix + "/publish", {"approval_id": args.approval_id}
                    )
                    mapped = call("GET", prefix + "/publication")["mappings"]
                    first_ids = {m["key"]: m["remote_id"] for m in mapped}
                    second = call(
                        "POST", prefix + "/publish", {"approval_id": args.approval_id}
                    )
                    final = call("GET", prefix + "/publication")
                    final_ids = {m["key"]: m["remote_id"] for m in final["mappings"]}
                    all_after = adapter.list_board_items(board)
                    after_snapshot = unrelated_snapshot(all_after, set())
                    preserved = set(unrelated) <= set(after_snapshot) and all(
                        after_snapshot[key] == body for key, body in unrelated.items()
                    )
                    assessment = GateAssessment.model_validate(call("GET", prefix))
                    project = call("GET", f"/projects/{assessment.project_id}")
                    source_project = {
                        k: project[k]
                        for k in ["id", "name", "gate_id", "synthetic", "participants"]
                    }
                    value = call("GET", f"/projects/{assessment.project_id}/value-case")
                    scene = build_board_scene(
                        assessment, Project.model_validate(source_project), value
                    )
                    verified = adapter.verify_managed_items(board, scene)
                    passed = (
                        first["status"] == "PUBLISHED"
                        and second["status"] == "PUBLISHED"
                        and second["result"]["created"] == 0
                        and second["result"]["updated"] == 0
                        and first_ids == final_ids
                        and preserved
                    )
                    result.update(
                        status="PASSED" if passed else "FAILED",
                        first_publication=first["result"],
                        repeat_publication=second["result"],
                        managed_ids_stable=first_ids == final_ids,
                        unrelated_items_preserved=preserved,
                        unrelated_items_checked=len(unrelated),
                        **verified,
                    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
