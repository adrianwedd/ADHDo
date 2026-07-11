import json, threading, urllib.error, urllib.request
from http.server import ThreadingHTTPServer

import pytest
from adhdolib import db
from adhdolib.binload import load_bin_module
from adhdolib.config import load_config

FAKE_STATE = {"ts": 1000.0, "day_part": "afternoon",
              "devices": [{"name": "office", "online": True, "now_playing": None}],
              "last": {"med": 60.0, "meal": None, "break": None, "nudge": None},
              "scheduled": [], "disk": {"pct": 50.0, "warn": False}}

@pytest.fixture
def dash(adhdo_home, monkeypatch):
    mod = load_bin_module("adhdo-dashboard")
    monkeypatch.setattr(mod, "get_state", lambda: dict(FAKE_STATE))
    return mod

@pytest.fixture
def server(dash):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), dash.DashboardHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()

def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read().decode()

def test_config_defaults(adhdo_home):
    cfg = load_config()
    assert cfg["dashboard"]["port"] == 8766
    assert cfg["dashboard"]["bind"] is None  # falls back to lan_ip

def test_html_page(server):
    status, ctype, body = _get(server + "/")
    assert status == 200
    assert ctype.startswith("text/html")
    assert "ADHDo" in body
    assert "/api/state" in body and "/api/journal" in body  # self-contained JS

def test_api_state(server):
    status, ctype, body = _get(server + "/api/state")
    assert status == 200
    assert ctype.startswith("application/json")
    assert json.loads(body) == FAKE_STATE

def test_api_journal_reads_db(server):
    conn = db.connect()
    db.log_event(conn, "session", "med", "morning dose")
    db.log_event(conn, "tool", "nudge", json.dumps({"text": "hi", "urgency": "low"}))
    conn.close()
    status, _, body = _get(server + "/api/journal")
    assert status == 200
    events = json.loads(body)["events"]
    assert len(events) == 2
    assert events[0]["type"] == "nudge"          # newest first
    assert events[0]["payload"]["urgency"] == "low"
    assert events[1]["payload"] == "morning dose"

def test_journal_secrets_scrubbed(server):
    conn = db.connect()
    db.log_event(conn, "session", "error", "jellyfin call failed: api_key=supersecret123")
    conn.close()
    _, _, body = _get(server + "/api/journal")
    assert "supersecret123" not in body
    assert "REDACTED" in body

def test_unknown_path_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(server + "/nope")
    assert e.value.code == 404

def test_write_methods_rejected(server):
    for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
        req = urllib.request.Request(server + "/api/state", data=b"{}", method=method)
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 405
        assert json.loads(e.value.read())["error"] == "method_not_allowed"

def test_state_failure_returns_500_envelope(server, dash, monkeypatch):
    def boom():
        raise RuntimeError("scan exploded")
    monkeypatch.setattr(dash, "get_state", boom)
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(server + "/api/state")
    assert e.value.code == 500
    payload = json.loads(e.value.read())
    assert payload["error"] == "internal"
    assert "RuntimeError" in payload["detail"]
