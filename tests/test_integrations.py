import asyncio
import json
import httpx
import pytest
from contextlib import AsyncExitStack
from fastapi.testclient import TestClient
from studio import model, moodle
from studio.agent import create_run, execute_run, connect
from studio.store import db, ROOT
from studio.web import app, login_attempts


def mock_transport(monkeypatch, module, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_gemini_native_api_contract(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-secret")
    def handler(request):
        assert request.headers["x-goog-api-key"] == "test-key-not-a-secret"
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.path.endswith(":generateContent")
        body = json.loads(request.content)
        assert body["generationConfig"]["responseSchema"]["properties"]["action"]["enum"] == ["get_all"]
        return httpx.Response(200, json={"candidates":[{"content":{"parts":[{"text":'{"action":"get_all"}'}]}}],"usageMetadata":{"promptTokenCount":20,"candidatesTokenCount":8}})
    mock_transport(monkeypatch, model, handler)
    decision, usage = asyncio.run(model.Planner().choose({"options":["get_all"]}, "gemini"))
    assert decision["action"] == "get_all" and usage["input_tokens"] == 20
    assert "test-key" not in json.dumps([decision, usage])


def test_moodle_numeric_grade_mapping_and_stable_id(monkeypatch):
    monkeypatch.setenv("MOODLE_URL", "https://moodle.example.test")
    monkeypatch.setenv("MOODLE_TOKEN", "test-token")
    def handler(request):
        assert b"gradereport_user_get_grade_items" in request.content
        return httpx.Response(200, json={"usergrades":[{"userid":12,"gradeitems":[{
            "id":33,"itemtype":"mod","itemname":"Reading quiz","graderaw":15,"grademin":0,"grademax":20}]}]})
    mock_transport(monkeypatch, moodle, handler)
    rows = asyncio.run(moodle.fetch_mapped_grades("L001",12,8,2026,1,[{"item_id":33,"skill":"reading_comprehension","observed_at":"2026-03-01"}]))
    assert rows[0]["id"].startswith("moodle-") and rows[0]["id"].endswith("-8-12-33")
    assert rows[0]["score"] == 15 and rows[0]["maximum"] == 20


@pytest.mark.parametrize("flag", ["scaleid","gradeishidden","gradeneedsupdate"])
def test_moodle_rejects_unfit_grades(monkeypatch, flag):
    monkeypatch.setenv("MOODLE_URL", "https://moodle.example.test")
    monkeypatch.setenv("MOODLE_TOKEN", "test-token")
    def handler(request):
        return httpx.Response(200, json={"usergrades":[{"userid":12,"gradeitems":[{
            "id":33,"itemtype":"mod","itemname":"Quiz","graderaw":2,"grademin":0,"grademax":5,flag:1}]}]})
    mock_transport(monkeypatch, moodle, handler)
    with pytest.raises(ValueError, match="numeric"):
        asyncio.run(moodle.fetch_mapped_grades("L001",12,8,2026,1,[{"item_id":33,"skill":"numeracy","observed_at":"2026-03-01"}]))


def test_http_auth_csrf_and_unreleased_report():
    from tests.test_evidence import make_profile
    login_attempts.clear()
    with TestClient(app) as client:
        assert client.get("/api/learners").status_code == 401
        login = client.post("/api/login", json={"username":"demo.teacher","password":"lesson-demo-2026"})
        csrf = login.json()["csrf"]
        assert client.post("/api/learners", json={"display_name":"Synthetic E","school":"Demo","grade":"6","consent_confirmed":True}).status_code == 403
        assert client.post("/api/learners", headers={"x-csrf-token":csrf,"Origin":"https://elsewhere.test"},json={}).status_code == 403
        draft, profile_id, _ = make_profile()
        assert client.get(f"/api/profiles/{profile_id}/report").status_code == 403
        created = client.post("/api/learners", headers={"x-csrf-token":csrf}, json={"display_name":"Synthetic E","school":"Demo","grade":"6","consent_confirmed":True})
        assert created.status_code == 200
        assert len(client.get("/api/learners").json()) == 5


class RecoveryPlanner:
    """Test-only decisions. The separate recorded evaluation uses real model weights."""
    def __init__(self):
        self.actions = iter(["get_recent","assess_trajectory","validate","get_all","assess_trajectory","validate","save"])
    async def choose(self, context, provider):
        action = next(self.actions)
        assert action in context["options"]
        return {"action":action,"reason":"Scripted recovery test"}, {"input_tokens":0,"output_tokens":0,"execution":"test_stub"}


def test_real_mcp_servers_and_validation_recovery():
    run_id = create_run("L001", "demo.teacher")
    output = asyncio.run(execute_run(run_id, RecoveryPlanner()))
    assert output["done"] and output["steps"] == 7
    with db() as c:
        events = [(r[0], json.loads(r[1])) for r in c.execute("SELECT action,outputs FROM audit WHERE run_id=?", (run_id,))]
    validations = [data for action,data in events if action == "validate_learner_profile"]
    assert [item["valid"] for item in validations] == [False,True]
    assert any(action == "reference.read_text_file" for action,_ in events)
    tools = next(data["tools"] for action,data in events if action == "mcp_discover" and "get_learner_evidence" in data["tools"])
    assert set(tools) == {"get_learner_evidence","assess_longitudinal_patterns","validate_learner_profile","save_profile_draft"}


def test_mcp_rejects_other_learner():
    import os, sys
    run_id = create_run("L001", "demo.teacher")
    with db(True) as c:
        c.execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
    async def check():
        async with AsyncExitStack() as stack:
            server = await connect(stack, sys.executable, ["-m","studio.mcp_server"], dict(os.environ, STUDIO_RUN_ID=run_id, PYTHONPATH=str(ROOT)))
            result = await server.call_tool("get_learner_evidence", {"learner_id":"L002","scope":"all"})
            assert result.isError
    asyncio.run(check())
