import json

import pytest

from cvmatch.cli import main

from tests.conftest import ROOT

CV = str(ROOT / "data" / "sample_cv.md")
OFFER = str(ROOT / "data" / "sample_offer.txt")


def test_cli_writes_markdown_and_json(tmp_path, capsys):
    out, js = tmp_path / "rapport.md", tmp_path / "rapport.json"
    rc = main(["--cv", CV, "--offer", OFFER, "--out", str(out), "--json", str(js), "--provider", "fake"])
    assert rc == 0
    assert "# Analyse CV ↔ offre" in out.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["score_actual"]["score"] > 0 and len(data["assessments"]) == 16
    assert "mode démo" in capsys.readouterr().err


def test_cli_interactive_review(monkeypatch, capsys):
    answers = iter(["o", "n", "t"])  # accepter la 1re, refuser la 2e, accepter toutes les restantes
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert main(["--cv", CV, "--offer", OFFER, "--review", "--provider", "fake"]) == 0
    out = capsys.readouterr().out
    assert "Validation des reformulations" in out
    assert out.count("appliquée ✅") == 4 and out.count("non retenue") == 1


def test_api_endpoints():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from cvmatch.api import app

    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    body = {"cv_text": open(CV, encoding="utf-8").read(), "offer_text": open(OFFER, encoding="utf-8").read()}
    r = client.post("/analyze", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["score_actual"]["score"] > 0 and data["report_md"].startswith("# Analyse")
    assert client.post("/analyze", json={"cv_text": "court", "offer_text": "court"}).status_code == 422


def _client(monkeypatch, **env):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    import cvmatch.api as api
    from cvmatch.limits import Limits, UsageGuard

    monkeypatch.setenv("LLM_PROVIDER", "fake")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(api, "guard", UsageGuard(Limits(per_client_per_hour=2)))
    return TestClient(api.app)


def test_api_upload_and_score(monkeypatch):
    client = _client(monkeypatch)
    with open(CV, "rb") as f:
        r = client.post("/analyze/upload", files={"cv_file": ("cv.md", f)}, data={"offer_text": open(OFFER, encoding="utf-8").read()})
    assert r.status_code == 200
    data = r.json()
    sid = data["suggestions"][0]["id"]
    none = client.post("/score", json={"assessments": data["assessments"], "approved_ids": []}).json()
    one = client.post("/score", json={"assessments": data["assessments"], "approved_ids": [sid]}).json()
    assert none["score"] == data["score_actual"]["score"] < one["score"] <= data["score_potential"]["score"]


def test_api_limits_and_key(monkeypatch):
    client = _client(monkeypatch, API_KEY="secret")
    body = {"cv_text": open(CV, encoding="utf-8").read(), "offer_text": open(OFFER, encoding="utf-8").read()}
    assert client.post("/analyze", json=body).status_code == 401
    ok = {"X-API-Key": "secret"}
    assert client.post("/analyze", json={**body, "cv_text": "x" * 100_000}, headers=ok).status_code == 413
    assert [client.post("/analyze", json=body, headers=ok).status_code for _ in range(3)] == [200, 200, 429]
    assert client.get("/health").status_code == 200  # /health reste public


def _sse_events(text):
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if not line.startswith(":"))
        if lines:
            events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_api_stream_reports_progress_then_result(monkeypatch):
    client = _client(monkeypatch)
    with open(CV, "rb") as f:
        r = client.post("/analyze/stream", files={"cv_file": ("cv.md", f)}, data={"offer_text": open(OFFER, encoding="utf-8").read()})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(r.text)
    kinds = [k for k, _ in events]
    assert kinds[-1] == "result" and kinds.count("progress") > 16
    skills = [d for k, d in events if k == "progress" and d["step"] == "assess_skill"]
    assert skills[-1]["done"] == skills[-1]["total"] == 16
    assert events[-1][1]["score_actual"]["score"] > 0


def test_api_stream_accepts_pasted_text_and_rejects_bad_input_before_streaming(monkeypatch):
    client = _client(monkeypatch)
    offer = open(OFFER, encoding="utf-8").read()
    r = client.post("/analyze/stream", data={"cv_text": open(CV, encoding="utf-8").read(), "offer_text": offer})
    assert _sse_events(r.text)[-1][0] == "result"
    r = client.post("/analyze/stream", data={"cv_text": "", "offer_text": offer})
    assert r.status_code == 422 and "CV" in r.json()["detail"]


def test_api_stream_error_event_when_llm_fails(monkeypatch):
    client = _client(monkeypatch)
    import cvmatch.api as api

    def boom(*a, **kw):
        raise RuntimeError("secret CV content")

    monkeypatch.setattr(api, "analyze", boom)
    r = client.post("/analyze/stream", data={"cv_text": open(CV, encoding="utf-8").read(), "offer_text": open(OFFER, encoding="utf-8").read()})
    [(kind, data)] = _sse_events(r.text)
    assert kind == "error" and "secret" not in data["detail"]


def test_api_example_report_and_cors(monkeypatch):
    monkeypatch.chdir(ROOT)
    client = _client(monkeypatch)
    ex = client.get("/example").json()
    assert "Python" in ex["cv_text"] and len(ex["offer_text"]) > 20
    result = client.post("/analyze", json=ex).json()
    sid = result["suggestions"][0]["id"]
    report = client.post("/report", json={"result": result, "approved_ids": [sid, "sg-inventee"]}).text
    assert report.startswith("# Analyse") and report.count("appliquée ✅") == 1
    pre = client.options("/analyze/stream", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert pre.headers["access-control-allow-origin"] == "http://localhost:3000"
