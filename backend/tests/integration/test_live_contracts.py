from copy import deepcopy
import json
import httpx
import pytest
from app.core.config import Settings
from app.main import create_app
from app.persistence.store import Store
from app.domain.models import Project
from app.services.assessment.engine import assess
from app.services.evidence.index import load_fixtures, snapshot
from app.services.ai.explainer import LLMExplainer
from app.services.miro.adapter import RestMiroAdapter, MockMiroAdapter, MiroError
from app.services.miro.scene import build_board_scene
from app.services.miro.verification import payload_mismatches, board_id_from_url, unrelated_snapshot
from app.services.value.calculator import value_case
from fastapi.testclient import TestClient


def setup_scene():
    s = Store(":memory:")
    load_fixtures(s)
    a = assess(snapshot(s, "PRJ-NORTHSTAR"))
    scene = build_board_scene(a, Project.model_validate(s.all("project")[0]), value_case(s, a.project_id))
    return s, a, scene


def test_readback_matches_approved_fields_and_detects_drift():
    s, a, scene = setup_scene()
    mock = MockMiroAdapter(s)
    board = mock.create_board("readback")
    mock.reconcile_publication(board["id"], scene)
    for mapping in s.all("mapping"):
        mapping["mode"] = "live"
        s.put("mapping", mapping["id"], mapping)
    remote = {i["id"]: i for i in s.all("mock_item")}

    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json=remote[request.url.path.rsplit("/", 1)[1]])

    rest = RestMiroAdapter(
        s,
        "fake",
        True,
        httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler)),
    )
    assert rest.verify_managed_items(board["id"], scene)["verified_items"] == 56
    shape = next(i for i in remote.values() if i["type"] == "shape")
    shape["data"]["content"] = "Someone edited this remote content"
    with pytest.raises(MiroError):
        rest.verify_managed_items(board["id"], scene)
    assert any(e["event"] == "readback_mismatch" for e in s.all("audit"))


def test_pagination_reads_items_and_connectors_with_opaque_cursors():
    calls = []
    s = Store(":memory:")

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/connectors"):
            return httpx.Response(200, json={"data": [{"id": "c", "type": "connector"}]})
        if request.url.params.get("cursor"):
            return httpx.Response(200, json={"data": [{"id": "2", "type": "text"}]})
        return httpx.Response(200, json={"data": [{"id": "1", "type": "shape"}], "cursor": "opaque+/=cursor"})

    rest = RestMiroAdapter(
        s,
        "fake",
        True,
        httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler)),
    )
    assert {i["id"] for i in rest.list_board_items("board")} == {"1", "2", "c"}
    assert calls[1].url.params["cursor"] == "opaque+/=cursor"
    assert all(r.method == "GET" for r in calls)


@pytest.mark.parametrize("case", ["loop", "malformed", "budget", "wrong_id"])
def test_invalid_remote_reads_fail_validation(case):
    s = Store(":memory:")

    def handler(request):
        if case == "wrong_id":
            return httpx.Response(200, json={"id": "wrong"})
        if case == "malformed":
            return httpx.Response(200, json={"data": [None]})
        return httpx.Response(200, json={"data": [{"id": "1"}], "cursor": "same"})

    rest = RestMiroAdapter(
        s,
        "fake",
        True,
        httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(MiroError):
        if case == "wrong_id":
            rest.get_item("board", "expected", "shape")
        else:
            rest.list_board_items("board", max_pages=1 if case == "budget" else 3)


def test_html_and_numeric_normalisation_and_unrelated_snapshots():
    assert not payload_mismatches(
        {"data": {"content": "Hello<br>world"}, "geometry": {"width": 340}, "style": {"fontSize": "14"}},
        {
            "data": {"content": "<p>Hello<br/>world</p>"},
            "geometry": {"width": 340.0, "height": 220},
            "style": {"fontSize": "14.0"},
        },
    )
    assert payload_mismatches({"startItem": {"id": "1"}}, {"startItem": {"id": "2"}}) == ["startItem.id"]
    assert board_id_from_url("https://miro.com/app/board/abc%3D/?share_link_id=1") == "abc="
    with pytest.raises(ValueError):
        board_id_from_url("https://evil.example/app/board/id/")
    assert unrelated_snapshot(
        [{"id": "1", "data": {"content": "manual"}, "modifiedAt": "x"}, {"id": "managed"}], {"managed"}
    ) == {"1": {"data": {"content": "manual"}}}


def test_source_failure_never_calls_model():
    s, a, scene = setup_scene()
    bad = deepcopy(a.source_records["evidence"])
    bad[0]["content_hash"] = "invalid"

    def handler(request):
        raise AssertionError("Invalid source must not reach model")

    result = LLMExplainer("test", httpx.Client(transport=httpx.MockTransport(handler))).generate(a, bad)
    assert result.runtime_status == "fallback" and result.fallback_reason == "source_validation_failed"


def test_api_model_use_and_cache_without_repeat_inference(monkeypatch):
    calls = []

    def handler(request):
        body = json.loads(request.content)
        findings = json.loads(body["messages"][1]["content"])["findings"]
        calls.append(body)
        plan = {
            "focus": "quality",
            "findings": [{"finding_id": f["finding_id"], "question": "quality"} for f in findings],
        }
        return httpx.Response(200, json={"done": True, "message": {"content": json.dumps(plan)}})

    import app.main as main

    original = LLMExplainer
    monkeypatch.setattr(
        main,
        "LLMExplainer",
        lambda model, timeout_seconds: original(model, httpx.Client(transport=httpx.MockTransport(handler))),
    )
    with TestClient(create_app(Settings(database_path=":memory:", llm_enabled=True))) as client:
        client.post("/api/v1/demo-sessions", json={"role": "Analyst"})
        a = client.post("/api/v1/projects/PRJ-NORTHSTAR/assessments").json()
        url = f"/api/v1/assessments/{a['id']}/explanation"
        first = client.get(url)
        second = client.get(url)
        assert first.status_code == second.status_code == 200
        assert first.json()["runtime_status"] == "model_used"
        assert first.json() == second.json() and len(calls) == 1


def test_validation_failure_overwrites_old_success_artifact(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    import sys

    path = Path(__file__).resolve().parents[3] / "scripts" / "validate_integrations.py"
    spec = importlib.util.spec_from_file_location("validation_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "result.json"
    output.write_text('{"status":"PASSED"}', encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["validate_integrations.py", "ollama", "--timeout", "0", "--output", str(output)]
    )
    assert module.main() == 2
    assert json.loads(output.read_text())["status"] == "FAILED"
