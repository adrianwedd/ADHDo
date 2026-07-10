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
    assert sent[0][:5] == ["send-keys", "-t", "adhdo", "-l", "--"]
    assert sent[0][5] == "hello; `x`\\nworld"
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

def test_busy_marker_race_treated_as_idle(adhdo_home, monkeypatch):
    # marker vanishes between exists() and stat() (or unlink) -> treat as idle
    import pathlib as _pathlib
    wake = load_wake()
    sent = []
    monkeypatch.setattr(wake, "run_tmux", lambda args: sent.append(args))
    data = adhdo_home / "data"
    data.mkdir(parents=True, exist_ok=True)
    real_busy = data / "busy"
    real_busy.write_text("")

    orig_stat = _pathlib.Path.stat

    def flaky_stat(self, *a, **kw):
        if self == real_busy:
            raise FileNotFoundError()
        return orig_stat(self, *a, **kw)

    monkeypatch.setattr(_pathlib.Path, "stat", flaky_stat)
    assert wake.inject("now") == "sent"
    assert sent  # tmux was actually invoked, not queued

def test_at_writes_schedule_row(adhdo_home, monkeypatch):
    wake = load_wake()
    conn = db.connect()
    out = wake.run(["--at", "23:59", "--tag", "checkin"], _test_conn=conn)
    assert out["scheduled"] == "checkin"
    assert conn.execute("SELECT COUNT(*) FROM schedule").fetchone()[0] == 1
