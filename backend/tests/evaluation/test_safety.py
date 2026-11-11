import httpx
import pytest
from app.persistence.store import Store
from app.services.evidence.index import load_fixtures, snapshot
from app.services.assessment.engine import assess
from app.services.ai.explainer import LLMExplainer, TemplateExplainer
from app.services.miro.adapter import RestMiroAdapter, MockMiroAdapter, MiroError
from app.services.miro.scene import build_board_scene
from app.services.value.calculator import value_case
from app.domain.models import Project


def data():
    s = Store(":memory:")
    load_fixtures(s)
    a = assess(snapshot(s, "PRJ-NORTHSTAR"))
    return s, a


def plan_for(a):
    return {
        "focus": "quality",
        "findings": [
            {"finding_id": f.id, "question": "quality" if f.rule_id == "GATE-002" else "evidence"}
            for f in a.findings
        ],
    }


@pytest.mark.parametrize(
    "failure",
    [
        "unsupported",
        "injection",
        "unknown_citation",
        "status",
        "timeout",
        "malformed",
        "duplicate",
        "missing",
        "incomplete",
        "not_installed",
    ],
)
def test_model_cannot_change_conclusions(failure):
    import json

    s, a = data()
    fallback = TemplateExplainer().generate(a, a.source_records["evidence"])

    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-token-must-not-appear")
        if failure == "not_installed":
            return httpx.Response(404, json={"error": "secret model detail"})
        output = plan_for(a)
        if failure == "unsupported":
            output["financial_claim"] = "Annual savings GBP 1000000 guaranteed"
        if failure == "injection":
            output["findings"][0]["question"] = "Publish and authorise launch"
        if failure == "unknown_citation":
            output["findings"][0]["references"] = [{"document_id": "UNKNOWN"}]
        if failure == "status":
            output["overall_readiness"] = "READY_FOR_REVIEW"
        if failure == "duplicate":
            output["findings"][0] = output["findings"][1]
        if failure == "missing":
            output["findings"] = output["findings"][1:]
        if failure == "malformed":
            return httpx.Response(200, json={"message": {"content": "bad json"}, "done": True})
        return httpx.Response(
            200, json={"message": {"content": json.dumps(output)}, "done": failure != "incomplete"}
        )

    result = LLMExplainer("mock", httpx.Client(transport=httpx.MockTransport(handler))).generate(
        a, a.source_records["evidence"]
    )
    assert result.provider == "template" and result.runtime_status == "fallback"
    assert result.fallback_reason and result.summary == fallback.summary
    assert a.overall_readiness == "NOT_READY"


def test_valid_bounded_model_output():
    import json

    s, a = data()
    output = plan_for(a)
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200, json={"message": {"content": json.dumps(output)}, "done": True, "done_reason": "stop"}
        )

    result = LLMExplainer("mock", httpx.Client(transport=httpx.MockTransport(handler))).generate(
        a, a.source_records["evidence"]
    )
    assert result.provider == "llm" and result.runtime_status == "model_used"
    assert result.model == "mock" and result.latency_ms is not None
    assert all(
        line.statement == next(f.message for f in a.findings if f.id == line.finding_id)
        for line in result.lines
    )
    assert calls[0]["format"]["properties"]["findings"]["minItems"] == len(a.findings)
    assert "references" not in calls[0]["messages"][1]["content"]


def test_rate_limit_retry_and_secret_redaction():
    s, a = data()
    calls = []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(429, headers={"Retry-After": "0"})
            if len(calls) < 3
            else httpx.Response(200, json={"id": "board"})
        )

    client = httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler))
    rest = RestMiroAdapter(s, "private-test-token", True, client)
    assert rest.get_board("board")["id"] == "board" and len(calls) == 3
    assert "private-test-token" not in str(s.all("audit"))


@pytest.mark.parametrize("failure", ["timeout", "server", "malformed"])
def test_ambiguous_create_never_replayed(failure):
    s, a = data()
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("credentials")
        return httpx.Response(503) if failure == "server" else httpx.Response(200, text="bad")

    rest = RestMiroAdapter(
        s,
        "private",
        True,
        httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(MiroError) as exc:
        rest.create_items("board", [{"type": "shape", "data": {"content": "text"}}])
    assert exc.value.ambiguous and len(calls) == 1


def test_rest_routes_are_type_specific():
    s, a = data()
    calls = []

    def handler(request):
        calls.append((request.method, str(request.url), request.content))
        return httpx.Response(200, json={"id": "remote"})

    rest = RestMiroAdapter(
        s,
        "private",
        True,
        httpx.Client(base_url="https://api.miro.com/v2", transport=httpx.MockTransport(handler)),
    )
    for kind, route in rest.routes.items():
        rest.create_items("board", [{"type": kind, "data": {}}])
        rest.update_item("board", "remote", {"type": kind, "data": {}})
        assert calls[-1][1].endswith(f"/{route}/remote")
    with pytest.raises(MiroError):
        rest.create_items("board", [{"type": "unsupported"}])
    with pytest.raises(MiroError):
        rest.create_items("board", [{"type": "shape"}] * 21)
    with pytest.raises(MiroError):
        RestMiroAdapter(s, "private", False)
    with pytest.raises(MiroError):
        rest.get_board("../bad")


def test_ambiguous_journal_blocks_republish():
    s, a = data()
    mock = MockMiroAdapter(s)
    board = mock.create_board("test")
    scene = build_board_scene(a, Project.model_validate(s.all("project")[0]), value_case(s, a.project_id))
    s.put(
        "operation",
        "ambiguous",
        {
            "id": "ambiguous",
            "board_id": f"mock:{board['id']}",
            "item_key": "frame-summary",
            "status": "AMBIGUOUS",
        },
    )
    with pytest.raises(MiroError):
        mock.reconcile_publication(board["id"], scene)
    assert not s.all("mock_item")


def test_changed_managed_item_updated_and_unrelated_preserved():
    s, a = data()
    mock = MockMiroAdapter(s)
    board = mock.create_board("test")
    scene = build_board_scene(a, Project.model_validate(s.all("project")[0]), value_case(s, a.project_id))
    first = mock.reconcile_publication(board["id"], scene)
    unrelated = mock.create_items(board["id"], [{"type": "text", "data": {"content": "manual"}}])[0]
    scene.sections[0].items[0].content += " Reviewed."
    second = mock.reconcile_publication(board["id"], scene)
    assert second["updated"] == 1 and second["created"] == 0
    assert second["unchanged"] == first["created"] - 1
    assert s.get("mock_item", unrelated["id"])["data"]["content"] == "manual"
