import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app
from app.services.miro.adapter import MockMiroAdapter

PID = "PRJ-NORTHSTAR"


@pytest.fixture
def client():
    with TestClient(create_app(Settings(database_path=":memory:"))) as c:
        yield c


def login(c, role):
    assert c.post("/api/v1/demo-sessions", json={"role": role}).status_code == 200


def prepared(c):
    login(c, "Analyst")
    a = c.post(f"/api/v1/projects/{PID}/assessments").json()
    aid = a["id"]
    login(c, "Reviewer")
    assert (
        c.post(
            f"/api/v1/assessments/{aid}/review",
            json={
                "decision": "ACKNOWLEDGED",
                "note": "Evidence reviewed; blockers require human closure. Publication documents current risks only.",
            },
        ).status_code
        == 200
    )
    login(c, "Publisher")
    assert (
        c.post(
            f"/api/v1/assessments/{aid}/publication-approvals",
            json={"action": "request", "destination_board": "mock-northstar"},
        ).status_code
        == 200
    )
    approval = c.post(
        f"/api/v1/assessments/{aid}/publication-approvals",
        json={"action": "approve", "destination_board": "mock-northstar"},
    )
    assert approval.status_code == 200
    return aid, approval.json()["id"]


def test_full_offline_flow(client):
    c = client
    assert c.get("/health").json()["miro_mode"] == "mock"
    assert c.get("/api/v1/projects").status_code == 401
    login(c, "Analyst")
    assert len(c.get("/api/v1/projects").json()) == 1
    assert len(c.get(f"/api/v1/projects/{PID}/requirements").json()) == 15
    assert len(c.get(f"/api/v1/projects/{PID}/evidence?q=DOC-004").json()) == 2
    aid, approval = prepared(c)
    assert c.get(f"/api/v1/assessments/{aid}/board-preview").status_code == 200
    scene = c.get(f"/api/v1/assessments/{aid}/scene").json()
    assert len(scene["sections"]) == 7
    first = c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval})
    assert first.status_code == 200, first.text
    assert first.json()["mode"] == "mock" and first.json()["board_url"] is None
    assert first.json()["result"]["created"] > 40
    store = c.app.state.store
    adapter = c.app.state.adapter
    unrelated = adapter.create_items(
        "mock-northstar", [{"type": "text", "data": {"content": "Unrelated manual note"}}]
    )[0]
    second = c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval})
    assert second.status_code == 200
    assert second.json()["result"]["created"] == 0
    assert second.json()["result"]["updated"] == 0
    assert store.get("mock_item", unrelated["id"])["data"]["content"] == "Unrelated manual note"
    assert len(store.all("mapping")) == first.json()["result"]["created"]
    value = c.get(f"/api/v1/projects/{PID}/value-case").json()
    assert value["scenarios"][1]["annual_hours_saved"] == "238.08"
    report = c.get(f"/api/v1/projects/{PID}/executive-report")
    assert report.status_code == 200 and "## 10." in report.text
    assert "publication_published" in [e["event"] for e in c.get("/api/v1/audit").json()]


def test_permissions_and_separation(client):
    c = client
    login(c, "Analyst")
    aid = c.post(f"/api/v1/projects/{PID}/assessments").json()["id"]
    assert (
        c.post(
            f"/api/v1/assessments/{aid}/review", json={"decision": "ACKNOWLEDGED", "note": "review"}
        ).status_code
        == 403
    )
    assert (
        c.post(
            f"/api/v1/assessments/{aid}/publish",
            json={"approval_id": "fake"},
            headers={"X-Role": "Publisher"},
        ).status_code
        == 403
    )
    login(c, "Publisher")
    assert (
        c.post(
            f"/api/v1/assessments/{aid}/publication-approvals",
            json={"action": "request", "destination_board": "mock-northstar"},
        ).status_code
        == 409
    )
    assert (
        c.post(
            "/api/v1/demo-sessions", json={"role": "Publisher"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert c.get("/health", headers={"Host": "evil.example"}).status_code == 400
    assert c.get("/api/v1/projects/missing").status_code == 404


def test_approval_invalidated_by_review(client):
    c = client
    aid, approval = prepared(c)
    login(c, "Reviewer")
    c.post(
        f"/api/v1/assessments/{aid}/review",
        json={"decision": "CHANGES_REQUESTED", "note": "Additional evidence needed"},
    )
    login(c, "Publisher")
    assert c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval}).status_code == 409
    assert c.app.state.store.get("approval", approval)["status"] == "SUPERSEDED"


def test_sources_and_new_assessment_invalidate(client):
    c = client
    aid, approval = prepared(c)
    store = c.app.state.store
    req = store.get("requirement", "REQ-015")
    req["criteria"] += " Updated."
    store.put("requirement", req["id"], req)
    assert c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval}).status_code == 409
    login(c, "Analyst")
    a2 = c.post(f"/api/v1/projects/{PID}/assessments").json()
    assert a2["assessment_version"] == 2
    assert store.get("approval", approval)["status"] == "SUPERSEDED"


def test_partial_failure_recovery_no_duplicates(client):
    c = client
    aid, approval = prepared(c)
    c.app.state.adapter = MockMiroAdapter(c.app.state.store, fail_after=3)
    failure = c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval})
    assert failure.status_code == 502
    assert len(c.app.state.store.all("mapping")) == 3
    c.app.state.adapter = MockMiroAdapter(c.app.state.store)
    retry = c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval})
    assert retry.status_code == 200
    assert retry.json()["result"]["unchanged"] == 3
    assert len(c.app.state.store.all("mock_item")) == len(c.app.state.store.all("mapping"))


def test_value_change_invalidates_scene_approval(client):
    c = client
    aid, approval = prepared(c)
    store = c.app.state.store
    value = store.get("scenario", "VALUE-2")
    value["adoption_rate"] = "0.5"
    store.put("scenario", value["id"], value)
    assert c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval}).status_code == 409
    assert store.get("approval", approval)["status"] == "SUPERSEDED"


def test_production_fails_closed():
    with pytest.raises(RuntimeError):
        create_app(Settings(app_mode="production", database_path=":memory:"))


def test_openapi_and_offline_docs(client):
    schema = client.get("/openapi.json").json()
    assert "GateAssessment" in schema["components"]["schemas"]
    assert schema["paths"]["/api/v1/projects/{pid}/assessments"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("GateAssessment")
    docs = client.get("/docs")
    assert docs.status_code == 200 and "Offline API reference" in docs.text
    assert "<script" not in docs.text


def test_error_is_redacted_and_correlated(client, caplog):
    c = client
    login(c, "Analyst")
    # Bad internal source data produces a redacted error, never a raw traceback.
    c.app.state.store.put("evidence", "DOC-001@A", {"id": "DOC-001", "private": "secret-must-not-appear"})
    response = c.get(f"/api/v1/projects/{PID}/evidence")
    assert response.status_code == 500
    assert "secret-must-not-appear" not in response.text
    assert response.headers["x-correlation-id"] == response.json()["correlation_id"]


def test_publication_recovery_lock_is_persisted(client):
    c = client
    aid, approval = prepared(c)
    store = c.app.state.store
    store.put("publication", "stalled", {"id": "stalled", "status": "PUBLISHING"})
    assert c.post(f"/api/v1/assessments/{aid}/publish", json={"approval_id": approval}).status_code == 409
    assert not store.all("mapping")
