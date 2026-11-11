"""Local source ingestion. Input text is data and never interpreted as instructions."""

import json
from pathlib import Path
from app.domain.models import EvidenceDocument, EvidenceStatus
from app.persistence.store import Store
from app.services.evidence.index import source_hash


def ingest_document(
    store: Store,
    path: Path,
    document_id: str,
    revision: str,
    title: str,
    requirement_ids: list[str],
    status: EvidenceStatus,
) -> EvidenceDocument:
    if path.suffix.lower() not in [".json", ".md"]:
        raise ValueError("Only JSON and Markdown sources are supported")
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("Source document is empty")
    if path.suffix.lower() == ".json":
        json.loads(text)  # Syntax validation; preserve the original source text.
    known = {r["id"] for r in store.all("requirement")}
    if not requirement_ids or not set(requirement_ids) <= known:
        raise ValueError("Evidence must link to known requirements")
    document = EvidenceDocument(
        id=document_id,
        revision=revision,
        source_type="json" if path.suffix.lower() == ".json" else "markdown",
        title=title,
        source_text=text,
        requirement_ids=requirement_ids,
        location=path.name,
        content_hash=source_hash(text),
        evidence_status=status,
        expected_classification=status.value,
    )
    key = f"{document_id}@{revision}"
    previous = next(
        (d for d in store.all("evidence") if d["id"] == document_id and d["revision"] == revision), None
    )
    if previous and previous["content_hash"] != document.content_hash:
        raise ValueError("An existing revision is immutable; provide a new revision")
    store.put("evidence", key, document)
    return document
