import importlib.machinery, importlib.util, json, pathlib, time
import pytest
from adhdolib import db
from adhdolib.envelope import ToolError

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "nudge"

def load_nudge():
    loader = importlib.machinery.SourceFileLoader("nudge_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("nudge_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_rate_limited_returns_distinct_code(adhdo_home, monkeypatch):
    nudge = load_nudge()
    conn = db.connect()
    for _ in range(4):
        db.log_event(conn, "nudge", "nudge", json.dumps({"urgency": "low"}))
    with pytest.raises(ToolError) as e:
        nudge.run(["hello"], _test_conn=conn)
    assert e.value.code == "rate_limited"

def test_successful_nudge_audits_and_journals(adhdo_home, monkeypatch):
    (adhdo_home / "config.yaml").write_text("default_device: office\n")
    nudge = load_nudge()
    monkeypatch.setattr(nudge, "synthesize", lambda text, d: d / "x.mp3")
    monkeypatch.setattr(nudge, "play_url_on_device", lambda url, dev, cfg: None)
    conn = db.connect()
    out = nudge.run(["step away", "--urgency", "med"], _test_conn=conn)
    assert out["nudged"] is True
    assert conn.execute("SELECT COUNT(*) FROM events WHERE type='nudge'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM audit WHERE tool='nudge'").fetchone()[0] == 1

def test_wait_until_idle_called_between_play_and_resume(adhdo_home, monkeypatch):
    (adhdo_home / "config.yaml").write_text("default_device: office\n")
    nudge = load_nudge()
    order = []
    monkeypatch.setattr(nudge, "synthesize", lambda text, d: d / "x.mp3")
    monkeypatch.setattr(nudge, "play_url_on_device",
                        lambda url, dev, cfg: order.append("play"))
    monkeypatch.setattr(nudge, "wait_until_idle",
                        lambda dev, cfg, timeout=30: order.append("wait") or True)
    monkeypatch.setattr(nudge, "_resume_previous",
                        lambda cfg: order.append("resume") or False)
    conn = db.connect()
    out = nudge.run(["step away"], _test_conn=conn)
    assert order == ["play", "wait", "resume"]

def test_tts_failure_enveloped(adhdo_home, monkeypatch):
    (adhdo_home / "config.yaml").write_text("default_device: office\n")
    nudge = load_nudge()
    def boom(text, d): raise ToolError("tts_failed", "no engine")
    monkeypatch.setattr(nudge, "synthesize", boom)
    conn = db.connect()
    with pytest.raises(ToolError) as e:
        nudge.run(["hi"], _test_conn=conn)
    assert e.value.code == "tts_failed"
    assert conn.execute("SELECT ok FROM audit WHERE tool='nudge'").fetchone()[0] == 0

def test_prune_cache_removes_only_stale_mp3s(adhdo_home):
    import os, time as _t
    nudge = load_nudge()
    cache = adhdo_home / "tts-cache"
    cache.mkdir()
    old = cache / "old.mp3"; old.write_bytes(b"x")
    os.utime(old, (_t.time() - 90000, _t.time() - 90000))
    fresh = cache / "fresh.mp3"; fresh.write_bytes(b"x")
    other = cache / "old.wav"; other.write_bytes(b"x")
    os.utime(other, (_t.time() - 90000, _t.time() - 90000))
    assert nudge.prune_cache(cache) == 1
    assert not old.exists() and fresh.exists() and other.exists()

def test_prune_cache_missing_dir_is_noop(adhdo_home):
    nudge = load_nudge()
    assert nudge.prune_cache(adhdo_home / "nope") == 0

def test_prune_runs_on_every_nudge_even_with_cache_hit(adhdo_home, monkeypatch):
    import os, time as _t
    (adhdo_home / "config.yaml").write_text("default_device: office\n")
    nudge = load_nudge()
    cache = adhdo_home / "tts-cache"
    cache.mkdir()
    stale = cache / "stale.mp3"; stale.write_bytes(b"x")
    os.utime(stale, (_t.time() - 90000, _t.time() - 90000))
    # cache-hit path: synthesize returns an existing file without pruning
    monkeypatch.setattr(nudge, "synthesize", lambda text, d: d / "hit.mp3")
    monkeypatch.setattr(nudge, "play_url_on_device", lambda url, dev, cfg: None)
    monkeypatch.setattr(nudge, "wait_until_idle", lambda dev, cfg, timeout=30: True)
    conn = db.connect()
    out = nudge.run(["hello there"], _test_conn=conn)
    assert out["nudged"] is True
    assert not stale.exists()

def test_non_toolerrror_crash_audited(adhdo_home, monkeypatch):
    (adhdo_home / "config.yaml").write_text("default_device: office\n")
    nudge = load_nudge()
    def boom(text, d): raise RuntimeError("boom")
    monkeypatch.setattr(nudge, "synthesize", boom)
    conn = db.connect()
    with pytest.raises(RuntimeError) as e:
        nudge.run(["hi"], _test_conn=conn)
    assert str(e.value) == "boom"
    audit_row = conn.execute("SELECT ok, detail FROM audit WHERE tool='nudge'").fetchone()
    assert audit_row is not None
    assert audit_row[0] == 0  # ok = False
    assert "crash: RuntimeError" in audit_row[1]  # detail contains crash info
