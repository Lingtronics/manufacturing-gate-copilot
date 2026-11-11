import hashlib
import json
import re
from pathlib import Path
from app.core.utils import digest
from app.domain.models import (
    EvidenceDocument,
    EvidenceReference,
    GateRequirement,
    Project,
    GateDefinition,
    QualityIssue,
    EngineeringChange,
    CorrectiveAction,
    KpiBaseline,
    ValueScenario,
    Model,
)
from app.persistence.store import Store

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures" / "northstar"
MODELS: dict[str, type[Model]] = {
    "project": Project,
    "gate": GateDefinition,
    "requirement": GateRequirement,
    "evidence": EvidenceDocument,
    "issue": QualityIssue,
    "change": EngineeringChange,
    "action": CorrectiveAction,
    "baseline": KpiBaseline,
    "scenario": ValueScenario,
}
FILES = {
    "project": "project.json",
    "gate": "gate.json",
    "requirement": "requirements/requirements.json",
    "evidence": "evidence/index.json",
    "issue": "quality/issues.json",
    "change": "changes/changes.json",
    "action": "actions/actions.json",
    "baseline": "kpis/baseline.json",
    "scenario": "kpis/scenarios.json",
}


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_fixtures(store: Store, root: Path = FIXTURES) -> None:
    if store.all("project"):
        return
    records: dict[str, list[dict]] = {}
    for kind, file in FILES.items():
        raw = json.loads((root / file).read_text(encoding="utf-8"))
        values = raw if isinstance(raw, list) else [raw]
        records[kind] = [MODELS[kind].model_validate(v).model_dump(mode="json") for v in values]
    req_ids = {r["id"] for r in records["requirement"]}
    doc_ids = {d["id"] for d in records["evidence"]}
    for d in records["evidence"]:
        text = (root / d["location"]).read_text(encoding="utf-8")
        if source_hash(text) != d["content_hash"] or text != d["source_text"]:
            raise ValueError("Source content hash mismatch")
        if not set(d["requirement_ids"]) <= req_ids:
            raise ValueError("Unknown requirement in evidence")
    for kind in ["requirement", "issue", "change"]:
        for record in records[kind]:
            if not set(record["evidence_ids"]) <= doc_ids:
                raise ValueError("Unknown evidence document")
            if not set(record.get("requirement_ids", [])) <= req_ids:
                raise ValueError("Unknown requirement")
    issues = {i["id"]: i for i in records["issue"]}
    for action in records["action"]:
        issue = issues.get(action["issue_id"])
        if not issue:
            raise ValueError("Unknown corrective action issue")
        if (
            action["blocking"]
            and action["status"] != "COMPLETE"
            and (issue["resolved"] or issue["severity"] not in ["HIGH", "CRITICAL"])
        ):
            raise ValueError("Blocking action requires an unresolved high-severity issue")
    with store.lock, store.db:
        for kind, values in records.items():
            for value in values:
                key = f"{value['id']}@{value['revision']}" if kind == "evidence" else value["id"]
                store.db.execute("INSERT INTO records VALUES(?,?,?)", (kind, key, json.dumps(value)))
        policy = (root / "policy.md").read_text(encoding="utf-8")
        store.db.execute(
            "INSERT INTO records VALUES(?,?,?)",
            (
                "policy",
                "POLICY-001",
                json.dumps({"id": "POLICY-001", "source_text": policy, "content_hash": source_hash(policy)}),
            ),
        )


class EvidenceIndex:
    def __init__(self, documents: list[dict]):
        self.documents = [EvidenceDocument.model_validate(d) for d in documents]
        for d in self.documents:
            if source_hash(d.source_text) != d.content_hash:
                raise ValueError("Evidence content hash mismatch")

    def exact(self, document_id: str, revision: str | None = None) -> list[EvidenceDocument]:
        return [
            d for d in self.documents if d.id == document_id and (revision is None or d.revision == revision)
        ]

    def search(self, query: str) -> list[EvidenceDocument]:
        if self.exact(query):
            return self.exact(query)
        terms = set(re.findall(r"\w+", query.lower()))
        ranked = [
            (sum(t in (d.title + " " + d.source_text).lower() for t in terms), d) for d in self.documents
        ]
        return [d for score, d in sorted(ranked, key=lambda x: (-x[0], x[1].id, x[1].revision)) if score]

    def reference(self, doc: EvidenceDocument) -> EvidenceReference:
        paragraphs = [p.strip() for p in doc.source_text.split("\n\n") if p.strip()]
        paragraph = 2 if len(paragraphs) > 1 else 1
        return EvidenceReference(
            id=f"REF-{doc.id}-{doc.revision}-{paragraph}",
            document_id=doc.id,
            revision=doc.revision,
            location=f"{doc.location}#paragraph-{paragraph}",
            quote=paragraphs[paragraph - 1],
            content_hash=doc.content_hash,
        )

    def validate(self, ref: EvidenceReference) -> bool:
        docs = self.exact(ref.document_id, ref.revision)
        if not docs:
            return False
        doc = docs[0]
        paragraphs = [p.strip() for p in doc.source_text.split("\n\n") if p.strip()]
        locations = {f"{doc.location}#paragraph-{i + 1}": p for i, p in enumerate(paragraphs)}
        quote = " ".join(ref.quote.split())
        return bool(
            quote
            and ref.content_hash == doc.content_hash
            and quote in " ".join(locations.get(ref.location, "").split())
        )


def snapshot(store: Store, project_id: str) -> dict[str, list[dict]]:
    project = store.get("project", project_id)
    gate = store.get("gate", project["gate_id"])
    requirements = [r for r in store.all("requirement") if r["project_id"] == project_id]
    doc_ids = {e for r in requirements for e in r["evidence_ids"]}
    return {
        "project": [project],
        "gate": [gate],
        "policy": [store.get("policy", gate["policy_document_id"])],
        "requirement": requirements,
        "evidence": [d for d in store.all("evidence") if d["id"] in doc_ids],
        **{
            k: [v for v in store.all(k) if v["project_id"] == project_id]
            for k in ["issue", "change", "action"]
        },
    }


def snapshot_hash(records: dict) -> str:
    return digest(records)
