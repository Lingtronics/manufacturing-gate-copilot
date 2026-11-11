import html
import re
from typing import Literal
from pydantic import Field
from app.core.utils import digest
from app.domain.models import Model, GateAssessment, Project


def clean(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", re.sub(r"<[^>]*>", "", text))[:600]


class BoardStyle(Model):
    fill: str = "#ffffff"
    state: str = "neutral"


class BoardItem(Model):
    key: str
    kind: Literal["shape", "text", "sticky_note"] = "shape"
    content: str
    x: float
    y: float
    width: float = 340
    height: float = 220
    style: BoardStyle = Field(default_factory=BoardStyle)
    evidence_reference_ids: list[str] = []


class BoardSection(Model):
    key: str
    title: str
    x: float
    y: float
    width: float
    height: float
    items: list[BoardItem]


class BoardConnector(Model):
    key: str
    start_key: str
    end_key: str


class BoardScene(Model):
    id: str
    assessment_id: str
    assessment_version: int
    synthetic: bool = True
    sections: list[BoardSection]
    connectors: list[BoardConnector] = []

    @property
    def content_hash(self) -> str:
        return digest(self)


class PublicationOperation(Model):
    id: str
    board_id: str
    item_key: str
    operation: Literal["create", "update"]
    payload_hash: str
    status: Literal["STARTED", "SUCCEEDED", "FAILED", "AMBIGUOUS"]
    remote_id: str | None = None


def build_board_scene(assessment: GateAssessment, project: Project, value_case: dict) -> BoardScene:
    a = assessment
    groups: list[tuple[str, str, list[tuple[str, str, str, list[str]]]]] = []
    groups.append(
        (
            "summary",
            "01 · Executive summary",
            [
                (
                    "summary",
                    f"{project.name}\n{a.overall_readiness}\nCoverage {a.requirement_coverage}% · {a.blocker_count} blockers · {a.warning_count} warnings\nSynthetic decision support. Human review required.",
                    "blocker" if a.blocker_count else "neutral",
                    [],
                )
            ],
        )
    )
    groups.append(
        (
            "requirements",
            "02 · Requirements and evidence",
            [
                (
                    r["id"],
                    f"{r['id']} · {r['title']}\n{a.requirement_states[r['id']]}\nSources: {', '.join(r['evidence_ids'])}",
                    str(a.requirement_states[r["id"]]),
                    [ref.id for ref in a.evidence_references if ref.document_id in r["evidence_ids"]],
                )
                for r in a.source_records["requirement"]
            ],
        )
    )
    groups.append(
        (
            "quality",
            "03 · Quality risk register",
            [
                (
                    r["id"],
                    f"{r['id']} · {r['title']}\n{r['severity']} · {'Resolved' if r['resolved'] else 'Unresolved'}\nRequirements: {', '.join(r['requirement_ids'])}",
                    "blocker" if not r["resolved"] and r["severity"] in ["HIGH", "CRITICAL"] else "neutral",
                    [ref.id for ref in a.evidence_references if ref.document_id in r["evidence_ids"]],
                )
                for r in a.source_records["issue"]
            ],
        )
    )
    groups.append(
        (
            "changes",
            "04 · Engineering changes",
            [
                (
                    r["id"],
                    f"{r['id']} · {r['title']}\n{r['status']} · Validation {'complete' if r['validation_complete'] else 'incomplete'}",
                    "warning" if not r["validation_complete"] else "VALIDATED",
                    [],
                )
                for r in a.source_records["change"]
            ],
        )
    )
    groups.append(
        (
            "actions",
            "05 · Corrective actions",
            [
                (
                    r["id"],
                    f"{r['id']} · {r['title']}\nOwner: {r['owner']} · Due {r['due_date']}\n{r['status']}",
                    "warning" if r["status"] != "COMPLETE" else "VALIDATED",
                    [],
                )
                for r in a.source_records["action"]
            ],
        )
    )
    decisions: list[tuple[str, str, str, list[str]]] = [
        (d.id, f"{d.actor}: {d.decision}\n{d.note}\n{d.timestamp}", "neutral", []) for d in a.decisions
    ]
    groups.append(
        (
            "decisions",
            "06 · Human decision log",
            decisions
            or [("no-decision", "No human review recorded. No production launch authorised.", "neutral", [])],
        )
    )
    groups.append(
        (
            "value",
            "07 · Business-value summary",
            [
                (
                    s["scenario_id"],
                    f"{s['name']} · modelled GBP\nAnnual hours saved: {s['annual_hours_saved']}\nAnnual net benefit: £{s['annual_net_benefit']}\nFirst-year ROI: {s['first_year_roi_percent']}%\nSynthetic assumptions; no achieved savings.",
                    "neutral",
                    [],
                )
                for s in value_case["scenarios"]
            ],
        )
    )
    sections: list[BoardSection] = []
    for n, (key, title, items) in enumerate(groups):
        # Each section occupies its own full row; dynamic height prevents any overlap.
        y = sum(s.height + 60 for s in sections)
        height = 100 + ((len(items) + 2) // 3) * 260
        rendered = []
        for i, (item_key, text, state, refs) in enumerate(items):
            fill = (
                "#fff0ed"
                if state in ["blocker", "MISSING", "CONFLICTING"]
                else "#fff8dd"
                if state in ["warning", "PARTIAL"]
                else "#eaf7f1"
                if state == "VALIDATED"
                else "#ffffff"
            )
            rendered.append(
                BoardItem(
                    key=item_key,
                    content=clean(text),
                    x=30 + (i % 3) * 370,
                    y=y + 80 + (i // 3) * 260,
                    style=BoardStyle(fill=fill, state=state),
                    evidence_reference_ids=refs,
                )
            )
        sections.append(
            BoardSection(key=key, title=title, x=0, y=y, width=1140, height=height, items=rendered)
        )
    connectors = [
        BoardConnector(key=f"link-{q['id']}-{r}", start_key=q["id"], end_key=r)
        for q in a.source_records["issue"]
        for r in q["requirement_ids"]
    ]
    return BoardScene(
        id=f"SCENE-{a.id}",
        assessment_id=a.id,
        assessment_version=a.assessment_version,
        sections=sections,
        connectors=connectors,
    )


def render_html(scene: BoardScene) -> str:
    sections: list[str] = []
    for s in scene.sections:
        cards = "".join(
            f'<article style="background:{i.style.fill}"><b>{html.escape(i.key)}</b><pre>{html.escape(i.content)}</pre><small>{html.escape(", ".join(i.evidence_reference_ids))}</small></article>'
            for i in s.items
        )
        sections.append(f'<section><h2>{html.escape(s.title)}</h2><div class="grid">{cards}</div></section>')
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Local board preview</title><style>body{font:15px system-ui;background:#eef2f4;color:#203340;padding:24px}section{background:#f9fbfc;padding:24px;margin:24px 0;border:1px solid #ccd7dc;border-radius:16px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}article{padding:20px;border:1px solid #dce3e6;border-radius:8px;min-height:180px}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}small{font-size:10px;overflow-wrap:anywhere}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style><h1>Gate 3 · Local board preview</h1><p>Synthetic data · Miro has not been called · No launch authorised</p>'
        + "".join(sections)
        + "</html>"
    )
