import importlib.machinery, importlib.util, json, pathlib
import pytest
from adhdolib.envelope import ToolError

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "cast"

def load_cast():
    loader = importlib.machinery.SourceFileLoader("cast_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("cast_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

CFG = {"moods": {"focus": {"jellyfin_playlist": None,
                           "streams": ["http://stream.example/focus"]}},
       "jellyfin": {"url": None, "api_key": None}}

def test_resolve_mood_stream_fallback():
    cast = load_cast()
    url, source = cast.resolve_mood("focus", CFG)
    assert url == "http://stream.example/focus" and source == "stream"

def test_resolve_unknown_mood():
    cast = load_cast()
    with pytest.raises(ToolError) as e:
        cast.resolve_mood("rave", CFG)
    assert e.value.code == "unknown_mood"

def test_raw_url_passthrough():
    cast = load_cast()
    url, source = cast.resolve_mood("http://x/y.mp3", CFG)
    assert source == "url"

def test_play_writes_now_playing(adhdo_home, monkeypatch):
    cast = load_cast()
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev, real: None)
    from adhdolib import db
    out = cast.run(["play", "http://x/y.mp3", "--device", "office"],
                   _test_conn=db.connect(),
                   _test_cfg={**CFG, "devices": {"office": "Nest Hub Max"},
                              "default_device": "office"})
    np = json.loads((adhdo_home / "data" / "now_playing.json").read_text())
    assert np["url"] == "http://x/y.mp3" and np["device"] == "Nest Hub Max"

def test_play_result_redacts_api_key(adhdo_home, monkeypatch):
    cast = load_cast()
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev, real: None)
    from adhdolib import db
    out = cast.run(["play", "http://x/y.mp3?api_key=SECRET123", "--device", "office"],
                   _test_conn=db.connect(),
                   _test_cfg={**CFG, "devices": {"office": "Nest Hub Max"},
                              "default_device": "office"})
    assert "SECRET123" not in out["playing"]
    assert "api_key=REDACTED" in out["playing"]
    np = json.loads((adhdo_home / "data" / "now_playing.json").read_text())
    assert "SECRET123" in np["url"]  # real URL kept for resume

class _FakeBrowser:
    def __init__(self, log):
        self._log = log
    def stop_discovery(self):
        self._log.append(True)

def _fake_pychromecast(casts, stopped):
    class FakePychromecast:
        @staticmethod
        def get_listed_chromecasts(friendly_names=None):
            return list(casts), _FakeBrowser(stopped)
    return FakePychromecast()

class _FakeMC:
    def __init__(self):
        self.stopped = False
        self.status = None
    def stop(self):
        self.stopped = True

class _FakeCast:
    def __init__(self, name="Nest Hub Max"):
        self.name = name
        self.media_controller = _FakeMC()
        self.volume = None
    def wait(self, timeout=None):
        pass
    def set_volume(self, level):
        self.volume = level

CFG_DEV = {**CFG, "devices": {"office": "Nest Hub Max"}, "default_device": "office"}

def _events(conn):
    return [json.loads(r[0]) for r in
            conn.execute("SELECT payload_json FROM events WHERE type='cast'")]

def test_stop_journals_event(adhdo_home, monkeypatch):
    cast = load_cast()
    import sys
    stopped = []
    cc = _FakeCast()
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([cc], stopped))
    from adhdolib import db
    conn = db.connect()
    out = cast.run(["stop"], _test_conn=conn, _test_cfg=CFG_DEV)
    assert out == {"stopped": True, "device": "office",
                   "cast_name": "Nest Hub Max"}
    assert cc.media_controller.stopped
    assert {"action": "stop", "device": "office"} in _events(conn)
    assert stopped == [True]

def test_play_journals_action(adhdo_home, monkeypatch):
    cast = load_cast()
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev, real: None)
    from adhdolib import db
    conn = db.connect()
    out = cast.run(["play", "http://x/y.mp3"], _test_conn=conn, _test_cfg=CFG_DEV)
    assert out["device"] == "office" and out["cast_name"] == "Nest Hub Max"
    assert {"action": "play", "mood": "http://x/y.mp3",
            "device": "office"} in _events(conn)

@pytest.mark.parametrize("argv", [["play", "http://x/y.mp3"],
                                  ["stop"],
                                  ["volume", "0.5"]])
def test_device_not_found_symmetric(adhdo_home, monkeypatch, argv):
    cast = load_cast()
    import sys
    stopped = []
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([], stopped))
    from adhdolib import db
    with pytest.raises(ToolError) as e:
        cast.run(argv, _test_conn=db.connect(), _test_cfg=CFG_DEV)
    assert e.value.code == "no_devices"
    assert e.value.detail == "device 'office' ('Nest Hub Max') not found"
    assert stopped == [True]  # discovery always cleaned up

def test_device_not_found_unaliased_name(adhdo_home, monkeypatch):
    cast = load_cast()
    import sys
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([], []))
    from adhdolib import db
    with pytest.raises(ToolError) as e:
        cast.run(["stop", "--device", "garage"],
                 _test_conn=db.connect(), _test_cfg=CFG_DEV)
    assert e.value.code == "no_devices"
    assert e.value.detail == "device 'garage' not found"

def test_stop_clears_now_playing_when_device_not_found(adhdo_home, monkeypatch):
    """stop must clear now_playing.json even when the device is
    undiscoverable, so a later nudge's resume can't restart music the
    user tried to stop. The clear is journaled."""
    cast = load_cast()
    import sys
    np = adhdo_home / "data" / "now_playing.json"
    np.parent.mkdir(parents=True, exist_ok=True)
    np.write_text(json.dumps({"url": "http://x/y.mp3", "device": "Nest Hub Max"}))
    stopped = []
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([], stopped))
    from adhdolib import db
    conn = db.connect()
    with pytest.raises(ToolError) as e:
        cast.run(["stop"], _test_conn=conn, _test_cfg=CFG_DEV)
    assert e.value.code == "no_devices"
    assert not np.exists()
    assert {"action": "stop_cleared_now_playing",
            "device": "office"} in _events(conn)
    assert stopped == [True]

def test_stop_device_not_found_no_now_playing_no_journal(adhdo_home, monkeypatch):
    """When nothing was playing, the not-found stop path raises without
    journaling a spurious clear event."""
    cast = load_cast()
    import sys
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([], []))
    from adhdolib import db
    conn = db.connect()
    with pytest.raises(ToolError) as e:
        cast.run(["stop"], _test_conn=conn, _test_cfg=CFG_DEV)
    assert e.value.code == "no_devices"
    assert _events(conn) == []

def test_volume_reports_logical_device(adhdo_home, monkeypatch):
    cast = load_cast()
    import sys
    cc = _FakeCast()
    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([cc], []))
    from adhdolib import db
    out = cast.run(["volume", "0.3"], _test_conn=db.connect(), _test_cfg=CFG_DEV)
    assert out == {"volume": 0.3, "device": "office",
                   "cast_name": "Nest Hub Max"}
    assert cc.volume == 0.3

def test_volume_non_numeric_is_usage_error(adhdo_home, monkeypatch):
    cast = load_cast()
    from adhdolib import db
    with pytest.raises(ToolError) as e:
        cast.run(["volume", "loud"], _test_conn=db.connect(), _test_cfg=CFG_DEV)
    assert e.value.code == "usage"

def test_jellyfin_fallthrough_to_stream(monkeypatch):
    """When Jellyfin is configured but unreachable, resolve_mood falls
    through to the mood's stream list instead of erroring."""
    cast = load_cast()
    import urllib.request

    def boom(*a, **k):
        raise OSError("jellyfin down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    cfg = {"moods": {"focus": {"jellyfin_playlist": "pl1",
                               "streams": ["http://stream.example/focus"]}},
           "jellyfin": {"url": "http://jf.local:8096", "api_key": "K"}}
    url, source = cast.resolve_mood("focus", cfg)
    assert url == "http://stream.example/focus" and source == "stream"

def test_jellyfin_empty_playlist_falls_through(monkeypatch):
    """Jellyfin reachable but playlist empty -> stream fallback too."""
    cast = load_cast()
    import io, urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(b'{"Items": []}'))
    cfg = {"moods": {"focus": {"jellyfin_playlist": "pl1",
                               "streams": ["http://stream.example/focus"]}},
           "jellyfin": {"url": "http://jf.local:8096", "api_key": "K"}}
    url, source = cast.resolve_mood("focus", cfg)
    assert url == "http://stream.example/focus" and source == "stream"

def test_jellyfin_used_when_available(monkeypatch):
    cast = load_cast()
    import io, urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(b'{"Items": [{"Id": "abc"}]}'))
    cfg = {"moods": {"focus": {"jellyfin_playlist": "pl1",
                               "streams": ["http://stream.example/focus"]}},
           "jellyfin": {"url": "http://jf.local:8096", "api_key": "K"}}
    url, source = cast.resolve_mood("focus", cfg)
    assert source == "jellyfin"
    assert url.startswith("http://jf.local:8096/Audio/abc/universal")

def test_status_reports_logical_and_real_names(monkeypatch):
    cast = load_cast()
    import sys

    class MC:
        status = None

    class CC:
        name = "Nest Hub Max"
        media_controller = MC()
        def wait(self, timeout=None):
            pass

    monkeypatch.setitem(sys.modules, "pychromecast",
                        _fake_pychromecast([CC()], []))
    result = cast.device_status({"devices": {"office": "Nest Hub Max"}})
    assert result == [{"device": "office", "name": "Nest Hub Max",
                       "online": True, "now_playing": None}]

def test_device_status_isolates_offline_device(monkeypatch):
    cast = load_cast()

    class FakeMediaController:
        status = None

    class GoodCast:
        name = "Good Speaker"
        media_controller = FakeMediaController()
        def wait(self, timeout=None):
            pass

    class BadCast:
        name = "Bad Speaker"
        def wait(self, timeout=None):
            raise RuntimeError("device unreachable")

    stopped = []

    class FakeBrowser:
        def stop_discovery(self):
            stopped.append(True)

    class FakePychromecast:
        @staticmethod
        def get_listed_chromecasts(friendly_names=None):
            return [GoodCast(), BadCast()], FakeBrowser()

    monkeypatch.setitem(__import__("sys").modules, "pychromecast", FakePychromecast())
    cfg = {"devices": {"a": "Good Speaker", "b": "Bad Speaker"}}
    result = cast.device_status(cfg)
    by_name = {d["name"]: d for d in result}
    assert by_name["Good Speaker"]["online"] is True
    assert by_name["Bad Speaker"]["online"] is False
    assert by_name["Bad Speaker"]["now_playing"] is None
    assert stopped == [True]  # finally block still ran discovery stop
