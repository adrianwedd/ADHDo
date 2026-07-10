import time
from adhdolib import db, schedule

def test_add_dedup_and_due(adhdo_home):
    conn = db.connect()
    now = time.time()
    assert schedule.add(conn, now - 10, "meds") is True
    assert schedule.add(conn, now - 10, "meds") is False
    due = schedule.due(conn, now)
    assert [t for _, t in due] == ["meds"]
    schedule.mark_delivered(conn, [i for i, _ in due])
    assert schedule.due(conn, now) == []

def test_consolidate_missed(adhdo_home):
    conn = db.connect()
    now = time.time()
    fixed = [{"tag": "meds", "time": "08:00"}, {"tag": "bedtime", "time": "22:30"}]
    msg = schedule.consolidate_missed(conn, fixed, last_wake_ts=now - 86400, now=now)
    assert msg is not None and "meds" in msg and "bedtime" in msg

def test_consolidate_none_when_recent(adhdo_home):
    conn = db.connect()
    now = time.time()
    msg = schedule.consolidate_missed(conn, [{"tag": "meds", "time": "08:00"}],
                                      last_wake_ts=now - 60, now=now)
    assert msg is None
