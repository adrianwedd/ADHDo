import importlib.machinery, importlib.util, pathlib, time
from adhdolib import db

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "wake"

def load_wake():
    loader = importlib.machinery.SourceFileLoader("wake_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("wake_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_inject_sends_literal_then_enter(adhdo_home, monkeypatch):
    wake = load_wake()
    sent = []
    monkeypatch.setattr(wake, "run_tmux", lambda args: sent.append(args))
    assert wake.inject("hello; `x`\nworld") == "sent"
    assert sent[0][:4] == ["send-keys", "-t", "adhdo", "-l"]
    assert sent[0][4] == "hello; `x`\\nworld"
    assert sent[1] == ["send-keys", "-t", "adhdo", "Enter"]

def test_busy_marker_queues(adhdo_home, monkeypatch):
    wake = load_wake()
    monkeypatch.setattr(wake, "run_tmux", lambda args: None)
    busy = adhdo_home / "data" / "busy"
    busy.write_text("")
    assert wake.inject("later") == "queued"
    assert "later" in (adhdo_home / "data" / "pending.txt").read_text()

def test_stale_busy_marker_ignored(adhdo_home, monkeypatch):
    import os
    wake = load_wake()
    sent = []
    monkeypatch.setattr(wake, "run_tmux", lambda args: sent.append(args))
    busy = adhdo_home / "data" / "busy"
    busy.write_text("")
    old = time.time() - 16 * 60
    os.utime(busy, (old, old))
    assert wake.inject("now") == "sent"
    assert not busy.exists()

def test_at_writes_schedule_row(adhdo_home, monkeypatch):
    wake = load_wake()
    conn = db.connect()
    out = wake.run(["--at", "23:59", "--tag", "checkin"], _test_conn=conn)
    assert out["scheduled"] == "checkin"
    assert conn.execute("SELECT COUNT(*) FROM schedule").fetchone()[0] == 1
