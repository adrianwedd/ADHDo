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
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev: None)
    from adhdolib import db
    out = cast.run(["play", "http://x/y.mp3", "--device", "office"],
                   _test_conn=db.connect(),
                   _test_cfg={**CFG, "devices": {"office": "Nest Hub Max"},
                              "default_device": "office"})
    np = json.loads((adhdo_home / "data" / "now_playing.json").read_text())
    assert np["url"] == "http://x/y.mp3" and np["device"] == "Nest Hub Max"

def test_play_result_redacts_api_key(adhdo_home, monkeypatch):
    cast = load_cast()
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev: None)
    from adhdolib import db
    out = cast.run(["play", "http://x/y.mp3?api_key=SECRET123", "--device", "office"],
                   _test_conn=db.connect(),
                   _test_cfg={**CFG, "devices": {"office": "Nest Hub Max"},
                              "default_device": "office"})
    assert "SECRET123" not in out["playing"]
    assert "api_key=REDACTED" in out["playing"]
    np = json.loads((adhdo_home / "data" / "now_playing.json").read_text())
    assert "SECRET123" in np["url"]  # real URL kept for resume

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
