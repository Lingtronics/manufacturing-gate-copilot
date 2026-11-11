import pytest
from pydantic import ValidationError
from app.domain.models import ValueScenario, EvidenceReference
from app.persistence.store import Store
from app.services.evidence.index import load_fixtures, snapshot, EvidenceIndex
from app.services.assessment.engine import assess


def test_fixture_counts_and_rules():
    store = Store(":memory:")
    load_fixtures(store)
    assert [len(store.all(k)) for k in ["requirement", "evidence", "issue", "change", "action"]] == [
        15,
        11,
        8,
        5,
        8,
    ]
    a = assess(snapshot(store, "PRJ-NORTHSTAR"))
    assert a.overall_readiness == "NOT_READY"
    assert str(a.requirement_coverage) == "60.00"
    assert a.blocker_count == 4
    assert a.warning_count == 4
    index = EvidenceIndex(store.all("evidence"))
    assert all(index.validate(r) for r in a.evidence_references)
    assert len(index.exact("DOC-004")) == 2
    assert index.search("DOC-004") == index.exact("DOC-004")
    assert index.search("calibration")
    assert not index.validate(
        EvidenceReference(
            id="bad", document_id="unknown", revision="A", location="x", quote="x", content_hash="x"
        )
    )


def test_domain_rejects_invalid_percent():
    with pytest.raises(ValidationError):
        ValueScenario(
            id="v",
            name="x",
            assumption_version="1",
            preparation_reduction="1.1",
            collection_reduction=0,
            implementation_cost=0,
            annual_operating_cost=0,
            adoption_rate=1,
            annual_review_volume=1,
        )
