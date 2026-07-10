import importlib.machinery, importlib.util, json, pathlib, time
import pytest
from adhdolib import db

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "state"

def load_state():
    loader = importlib.machinery.SourceFileLoader("state_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("state_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_schema_and_last_events(adhdo_home, monkeypatch):
    st = load_state()
    monkeypatch.setattr(st, "scan_devices", lambda cfg: [])
    conn = db.connect()
    db.log_event(conn, "session", "med", "dose")
    out = st.run([], _test_conn=conn)
    for k in ("ts", "day_part", "devices", "last", "scheduled", "disk"):
        assert k in out
    assert out["last"]["med"] is not None and out["last"]["med"] < 5
    assert out["last"]["meal"] is None
    assert isinstance(out["disk"]["pct"], (int, float))

def test_device_cache_used(adhdo_home, monkeypatch):
    st = load_state()
    calls = []
    monkeypatch.setattr(st, "scan_devices", lambda cfg: calls.append(1) or [])
    conn = db.connect()
    st.run([], _test_conn=conn)
    st.run([], _test_conn=conn)
    assert len(calls) == 1  # second call served from 60s cache

def test_non_toolerrror_crash_audited(adhdo_home, monkeypatch):
    st = load_state()
    def boom(cfg): raise RuntimeError("boom")
    monkeypatch.setattr(st, "scan_devices", boom)
    conn = db.connect()
    with pytest.raises(RuntimeError) as e:
        st.run([], _test_conn=conn)
    assert str(e.value) == "boom"
    audit_row = conn.execute("SELECT ok, detail FROM audit WHERE tool='state'").fetchone()
    assert audit_row is not None
    assert audit_row[0] == 0  # ok = False
    assert "crash: RuntimeError" in audit_row[1]  # detail contains crash info
