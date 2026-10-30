import importlib.machinery, importlib.util, json, pathlib, time
import pytest
from datetime import datetime
from adhdolib import db
from adhdolib.envelope import ToolError

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "nudge"

def load_nudge():
    loader = importlib.machinery.SourceFileLoader("nudge_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("nudge_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # These tests exercise delivery/cache/audit, not the wall-clock policy.
    # Keep them outside quiet hours on both UTC CI and Australian hosts.
    class Midday(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 24, 12, tzinfo=tz)
    mod.datetime = Midday
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
    monkeypatch.setattr(nudge, "wait_until_idle", lambda *a, **k: True)
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
                        lambda dev, cfg, timeout=30, **kw: order.append("wait") or True)
    monkeypatch.setattr(nudge, "_resume_previous",
                        lambda cfg, interrupted: order.append("resume") or False)
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

def test_prune_cache_tolerates_concurrent_deletion(adhdo_home, monkeypatch):
    """A concurrent nudge may delete a cached mp3 between glob and
    stat/unlink; prune_cache must skip it instead of crashing."""
    import os, time as _t
    nudge = load_nudge()
    cache = adhdo_home / "tts-cache"
    cache.mkdir()
    racy = cache / "racy.mp3"; racy.write_bytes(b"x")
    stale = cache / "stale.mp3"; stale.write_bytes(b"x")
    os.utime(stale, (_t.time() - 90000, _t.time() - 90000))
    orig_stat = pathlib.Path.stat
    def racy_stat(self, **kw):
        if self.name == "racy.mp3":
            # simulate the other process deleting it mid-scan
            if os.path.exists(str(self)):
                os.unlink(str(self))
            raise FileNotFoundError(str(self))
        return orig_stat(self, **kw)
    monkeypatch.setattr(pathlib.Path, "stat", racy_stat)
    assert nudge.prune_cache(cache) == 1
    monkeypatch.undo()
    assert not stale.exists()

def test_prune_cache_tolerates_unlink_race(adhdo_home, monkeypatch):
    """File vanishes between stat and unlink: unlink(missing_ok=True)
    must swallow it and still count/continue."""
    import os, time as _t
    nudge = load_nudge()
    cache = adhdo_home / "tts-cache"
    cache.mkdir()
    a = cache / "a.mp3"; a.write_bytes(b"x")
    b = cache / "b.mp3"; b.write_bytes(b"x")
    old = (_t.time() - 90000, _t.time() - 90000)
    os.utime(a, old); os.utime(b, old)
    orig_stat = pathlib.Path.stat
    def stat_then_delete(self, **kw):
        st = orig_stat(self, **kw)
        if self.name == "a.mp3":
            os.unlink(str(self))  # concurrent prune wins the race
        return st
    monkeypatch.setattr(pathlib.Path, "stat", stat_then_delete)
    assert nudge.prune_cache(cache) == 2
    monkeypatch.undo()
    assert not a.exists() and not b.exists()

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
    monkeypatch.setattr(nudge, "wait_until_idle", lambda dev, cfg, timeout=30, **kw: True)
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

@pytest.mark.parametrize('state,content,record_device,finished,expected', [
    ('IDLE', 'http://music/track.mp3', 'Nest', True, False),
    ('PAUSED', 'http://music/track.mp3', 'Nest', True, False),
    ('PLAYING', 'http://other/track.mp3', 'Nest', True, False),
    ('PLAYING', 'http://music/track.mp3', 'Other Nest', True, False),
    ('PLAYING', 'http://music/track.mp3', 'Nest', False, False),
    ('PLAYING', 'http://music/track.mp3', 'Nest', True, True),
])
def test_resume_only_interrupted_content(adhdo_home, monkeypatch, state, content,
                                         record_device, finished, expected):
    import sys
    from types import SimpleNamespace
    (adhdo_home / 'config.yaml').write_text('default_device: office\ndevices: {office: Nest}\n')
    record = adhdo_home / 'data' / 'now_playing.json'
    record.parent.mkdir(exist_ok=True)
    record.write_text(json.dumps({'url': 'http://music/track.mp3', 'device': record_device}))
    calls, discoveries = [], []
    status = SimpleNamespace(player_state=state, content_id=content,
                             current_time=42.5, stream_type='BUFFERED')
    class MC:
        def __init__(self):
            self.status = status
        def play_media(self, url, content_type, **kwargs):
            calls.append((url, content_type, kwargs))
            self.status = SimpleNamespace(player_state='PLAYING', content_id=url, current_time=0)
        def block_until_active(self, timeout):
            pass
    cc = SimpleNamespace(media_controller=MC(), wait=lambda **kw: None)
    def discover(friendly_names):
        assert friendly_names == ['Nest']
        return [cc], SimpleNamespace(stop_discovery=lambda: discoveries.append(True))
    monkeypatch.setitem(sys.modules, 'pychromecast', SimpleNamespace(get_listed_chromecasts=discover))
    nudge = load_nudge()
    monkeypatch.setattr(nudge, 'synthesize', lambda text, d: d / 'x.mp3')
    monkeypatch.setattr(nudge, 'wait_until_idle', lambda *a, **kw: finished)
    out = nudge.run(['hello'], _test_conn=db.connect())
    assert out['resumed'] is expected
    assert len(calls) == (2 if expected else 1)
    if expected:
        assert calls[-1] == ('http://music/track.mp3', 'audio/mpeg', {'current_time': 42.5, 'stream_type': 'BUFFERED'})
    assert discoveries

@pytest.mark.parametrize('state,content,expected', [
    ('IDLE', 'http://nudge', True),
    ('PLAYING', 'http://nudge', False),
    ('UNKNOWN', 'http://nudge', False),
    ('IDLE', 'http://someone-else', False),
    ('IDLE', None, False),
])
def test_wait_requires_target_nudge_idle(monkeypatch, state, content, expected):
    import sys
    from types import SimpleNamespace
    nudge = load_nudge()
    stopped = []
    status = SimpleNamespace(player_state=state, content_id=content)
    cc = SimpleNamespace(wait=lambda **kw: None, media_controller=SimpleNamespace(status=status))
    monkeypatch.setitem(sys.modules, 'pychromecast', SimpleNamespace(
        get_listed_chromecasts=lambda **kw: ([cc], SimpleNamespace(stop_discovery=lambda: stopped.append(True)))))
    clock = iter([0, 0, 2])
    monkeypatch.setattr(nudge.time, 'time', lambda: next(clock))
    monkeypatch.setattr(nudge.time, 'sleep', lambda _: None)
    assert nudge.wait_until_idle('Nest', {}, timeout=1, expected_url='http://nudge') is expected
    assert stopped == [True]


@pytest.mark.parametrize('changed', [None, {'url': 'http://new', 'device': 'Nest'}])
def test_restore_honours_stop_or_new_play(adhdo_home, monkeypatch, changed):
    nudge = load_nudge()
    record = adhdo_home / 'data' / 'now_playing.json'
    original = {'url': 'http://music', 'device': 'Nest'}
    if changed is not None:
        record.write_text(json.dumps(changed))
    monkeypatch.setattr(nudge, 'play_url_on_device', lambda *a, **kw: pytest.fail('must not resume'))
    assert not nudge._resume_previous({}, (original, 42.5, 'BUFFERED'))


def test_live_restore_has_no_seek(adhdo_home, monkeypatch):
    nudge = load_nudge()
    original = {'url': 'http://stream', 'device': 'Nest'}
    (adhdo_home / 'data' / 'now_playing.json').write_text(json.dumps(original))
    calls = []
    monkeypatch.setattr(nudge, 'play_url_on_device', lambda *a, **kw: calls.append((a, kw)))
    assert nudge._resume_previous({}, (original, None, 'LIVE'))
    assert calls == [(('http://stream', 'Nest', {}), {'current_time': None, 'stream_type': 'LIVE'})]
