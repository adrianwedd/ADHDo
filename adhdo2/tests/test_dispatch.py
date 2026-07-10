import importlib.machinery, importlib.util, pathlib, time
from adhdolib import db, schedule

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "adhdo-dispatch"

def load_dispatch():
    loader = importlib.machinery.SourceFileLoader("dispatch_cli", str(BIN))
    spec = importlib.util.spec_from_file_location("dispatch_cli", BIN, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_delivers_pending_and_due(adhdo_home, monkeypatch):
    d = load_dispatch()
    sent = []
    monkeypatch.setattr(d, "inject", lambda t: sent.append(t) or "sent")
    (adhdo_home / "data" / "pending.txt").write_text("queued msg\n")
    conn = db.connect()
    schedule.add(conn, time.time() - 5, "checkin")
    out = d.run(_test_conn=conn)
    assert out == {"delivered": 2}
    assert not (adhdo_home / "data" / "pending.txt").exists()
    assert schedule.due(conn, time.time()) == []

def test_requeues_when_busy(adhdo_home, monkeypatch):
    d = load_dispatch()
    monkeypatch.setattr(d, "inject", lambda t: "queued")
    (adhdo_home / "data" / "pending.txt").write_text("msg\n")
    conn = db.connect()
    out = d.run(_test_conn=conn)
    assert out == {"delivered": 0}
