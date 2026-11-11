from copy import deepcopy
from decimal import Decimal
import json
import pytest
from pydantic import ValidationError
from app.domain.models import KpiBaseline, ValueScenario, EngineeringChange
from app.persistence.store import Store
from app.services.evidence.index import load_fixtures, snapshot, source_hash, EvidenceIndex, FIXTURES
from app.services.assessment.engine import assess
from app.services.value.calculator import calculate, money, value_case
from app.services.miro.scene import build_board_scene, render_html
from app.domain.models import Project


def seeded():
    s = Store(":memory:")
    load_fixtures(s)
    return s


def complete_records():
    records = deepcopy(snapshot(seeded(), "PRJ-NORTHSTAR"))
    records["evidence"] = [
        d for d in records["evidence"] if not (d["id"] == "DOC-004" and d["revision"] == "B")
    ]
    for d in records["evidence"]:
        d["evidence_status"] = "VALIDATED"
    for i in records["issue"]:
        i["resolved"] = True
    for c in records["change"]:
        c["status"] = "VALIDATED"
        c["validation_complete"] = True
    for a in records["action"]:
        a["status"] = "COMPLETE"
    return records


def test_policy_and_manifest_golden():
    records = snapshot(seeded(), "PRJ-NORTHSTAR")
    a = assess(records)
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    assert a.overall_readiness == manifest["expected"]["overall_readiness"]
    assert str(a.requirement_coverage) == manifest["expected"]["coverage"]
    assert a.blocker_count == manifest["expected"]["blockers"]
    assert a.warning_count == manifest["expected"]["warnings"]
    assert sum(f.category == "insufficient" for f in a.findings) == manifest["expected"]["insufficient"]
    for req in records["requirement"]:
        assert a.requirement_states[req["id"]] == req["expected_classification"]


def test_complete_and_precedence():
    records = complete_records()
    a = assess(records)
    assert a.overall_readiness == "READY_FOR_REVIEW" and a.requirement_coverage == 100
    records["action"][2]["status"] = "OPEN"
    assert assess(records).overall_readiness == "CONDITIONAL_REVIEW"
    records["evidence"][5]["evidence_status"] = "PARTIAL"
    assert assess(records).overall_readiness == "INSUFFICIENT_EVIDENCE"
    records["issue"][0]["resolved"] = False
    assert assess(records).overall_readiness == "NOT_READY"


@pytest.mark.parametrize(
    "mutation,rule,readiness",
    [
        ("critical", "GATE-001", "NOT_READY"),
        ("defect", "GATE-002", "NOT_READY"),
        ("change", "GATE-003", "NOT_READY"),
        ("revision", "GATE-004", "INSUFFICIENT_EVIDENCE"),
        ("mandatory", "GATE-006", "INSUFFICIENT_EVIDENCE"),
        ("action", "GATE-005", "CONDITIONAL_REVIEW"),
    ],
)
def test_each_safety_rule(mutation, rule, readiness):
    records = complete_records()
    if mutation == "critical":
        records["evidence"][0]["evidence_status"] = "MISSING"
    if mutation == "defect":
        records["issue"][0]["resolved"] = False
    if mutation == "change":
        records["change"][0].update(status="APPROVED", validation_complete=False)
    if mutation == "revision":
        d = deepcopy(records["evidence"][3])
        d.update(
            revision="B",
            source_text="Contradictory revision",
            content_hash=source_hash("Contradictory revision"),
        )
        records["evidence"].append(d)
    if mutation == "mandatory":
        records["evidence"][7]["evidence_status"] = "MISSING"
    if mutation == "action":
        records["action"][2]["status"] = "OPEN"
    a = assess(records)
    assert a.overall_readiness == readiness
    assert rule in [f.rule_id for f in a.findings]


def test_coverage_partial_conflicting_and_missing():
    records = complete_records()
    records["evidence"][0]["evidence_status"] = "PARTIAL"
    records["evidence"][1]["evidence_status"] = "MISSING"
    records["evidence"][3]["evidence_status"] = "CONFLICTING"
    a = assess(records)
    # DOC-002 supports REQ-002 and REQ-012: 4 of 15 requirements excluded.
    assert a.requirement_coverage == Decimal("73.33")


def test_quote_revision_hash_and_location_validation():
    store = seeded()
    idx = EvidenceIndex(store.all("evidence"))
    doc = idx.exact("DOC-005")[0]
    ref = idx.reference(doc)
    assert idx.validate(ref)
    for field, val in [
        ("revision", "Z"),
        ("content_hash", "bad"),
        ("location", "bad"),
        ("quote", "Unsupported conclusion"),
    ]:
        assert not idx.validate(ref.model_copy(update={field: val}))
    raw = doc.model_dump()
    raw["source_text"] = "Changed without new hash"
    with pytest.raises(ValueError):
        EvidenceIndex([raw])


def test_financial_known_results_and_rounding():
    s = seeded()
    v = value_case(s, "PRJ-NORTHSTAR")["scenarios"][1]
    assert v["annual_hours_saved"] == "238.08"
    assert v["annual_gross_benefit"] == "15475.20"
    assert v["annual_net_benefit"] == "13075.20"
    assert v["first_year_net_benefit"] == "1075.20"
    assert v["first_year_roi_percent"] == "8.96"
    assert v["simple_payback_years"] == "0.92"
    assert money(Decimal("1.005")) == "1.01"
    b = KpiBaseline.model_validate(s.all("baseline")[0])
    scenario = ValueScenario.model_validate(s.all("scenario")[0])
    scenario.adoption_rate = Decimal(0)
    scenario.implementation_cost = Decimal(0)
    scenario.annual_operating_cost = Decimal(0)
    result = calculate(b, scenario)
    assert result["first_year_roi_percent"] is None and result["simple_payback_years"] is None
    scenario.adoption_rate = Decimal(1)
    assert calculate(b, scenario)["simple_payback_years"] == "0.00"


@pytest.mark.parametrize(
    "field,value",
    [
        ("implementation_cost", -1),
        ("annual_operating_cost", -1),
        ("adoption_rate", "1.01"),
        ("collection_reduction", -1),
        ("annual_review_volume", -1),
    ],
)
def test_invalid_financial_inputs(field, value):
    data = seeded().all("scenario")[0]
    data[field] = value
    with pytest.raises(ValidationError):
        ValueScenario.model_validate(data)


def test_invalid_change_status():
    data = seeded().all("change")[0]
    data["status"] = "VALIDATED"
    with pytest.raises(ValidationError):
        EngineeringChange.model_validate(data)


def test_scene_stability_geometry_and_sanitisation():
    s = seeded()
    a = assess(snapshot(s, "PRJ-NORTHSTAR"))
    p = Project.model_validate(s.all("project")[0])
    v = value_case(s, p.id)
    scene = build_board_scene(a, p, v)
    assert scene == build_board_scene(a, p, v)
    assert len(scene.sections) == 7
    keys = [i.key for section in scene.sections for i in section.items]
    assert len(keys) == len(set(keys))
    for x, y in zip(scene.sections, scene.sections[1:]):
        assert x.y + x.height < y.y
    for section in scene.sections:
        for i in section.items:
            assert section.x <= i.x and i.x + i.width <= section.x + section.width
            assert section.y <= i.y and i.y + i.height <= section.y + section.height
    scene.sections[0].items[0].content = "<script>alert(1)</script>"
    assert "<script>" not in render_html(scene)
    assert "&lt;script&gt;" in render_html(scene)


def test_persistence_survives_restart(tmp_path):
    path = str(tmp_path / "db.sqlite3")
    s = Store(path)
    load_fixtures(s)
    s.put("example", "id", {"id": "id", "value": 5})
    s.db.close()
    reopened = Store(path)
    load_fixtures(reopened)
    assert reopened.get("example", "id")["value"] == 5
    assert len(reopened.all("requirement")) == 15


def test_json_markdown_ingestion_and_revision_immutability(tmp_path):
    from app.services.evidence.ingest import ingest_document
    from app.domain.models import EvidenceStatus

    store = seeded()
    path = tmp_path / "record.json"
    path.write_text('{"test":"synthetic JSON evidence"}', encoding="utf-8")
    d = ingest_document(store, path, "DOC-NEW", "A", "JSON evidence", ["REQ-015"], EvidenceStatus.PARTIAL)
    idx = EvidenceIndex(store.all("evidence"))
    assert d.source_type == "json" and idx.validate(idx.reference(d))
    path.write_text('{"test":"changed"}', encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_document(store, path, "DOC-NEW", "A", "JSON evidence", ["REQ-015"], EvidenceStatus.VALIDATED)
    path = tmp_path / "evidence.md"
    path.write_text("# Synthetic\n\nEvidence paragraph.", encoding="utf-8")
    assert (
        ingest_document(store, path, "DOC-NEW", "B", "Markdown", ["REQ-015"], EvidenceStatus.PARTIAL).revision
        == "B"
    )
    with pytest.raises(ValueError):
        ingest_document(store, path, "DOC-X", "A", "Unknown", ["REQ-UNKNOWN"], EvidenceStatus.PARTIAL)


def test_injection_fixture_has_no_rule_authority():
    records = complete_records()
    text = (FIXTURES / "injection.txt").read_text(encoding="utf-8")
    records["evidence"][0].update(source_text=text, content_hash=source_hash(text), evidence_status="MISSING")
    records["issue"][0]["resolved"] = False
    a = assess(records)
    assert a.overall_readiness == "NOT_READY"
    assert a.blocker_count == 2
    assert records["issue"][0]["resolved"] is False
