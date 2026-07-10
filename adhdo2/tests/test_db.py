from adhdolib import db
import pytest

def test_schema_created(adhdo_home):
    conn = db.connect()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "audit", "schedule", "rollups"} <= names

def test_log_event_and_audit(adhdo_home):
    conn = db.connect()
    db.log_event(conn, "session", "decision", "played focus music")
    db.audit(conn, "cast", ["play", "focus"], True, "ok")
    assert conn.execute("SELECT type FROM events").fetchone()[0] == "decision"
    assert conn.execute("SELECT tool, ok FROM audit").fetchone() == ("cast", 1)

def test_invalid_event_type_rejected(adhdo_home):
    conn = db.connect()
    with pytest.raises(ValueError):
        db.log_event(conn, "session", "bogus", "x")
