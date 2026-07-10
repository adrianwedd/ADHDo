import sqlite3
from datetime import datetime, timedelta


def add(conn, due_ts: float, tag: str) -> bool:
    try:
        conn.execute("INSERT INTO schedule(due_ts, tag) VALUES(?,?)", (due_ts, tag))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def due(conn, now: float):
    return conn.execute(
        "SELECT id, tag FROM schedule WHERE delivered=0 AND due_ts<=?",
        (now,)).fetchall()


def mark_delivered(conn, ids):
    conn.executemany("UPDATE schedule SET delivered=1 WHERE id=?",
                     [(i,) for i in ids])
    conn.commit()


def consolidate_missed(conn, fixed_events, last_wake_ts: float, now: float):
    missed = []
    start = datetime.fromtimestamp(last_wake_ts)
    end = datetime.fromtimestamp(now)
    for ev in fixed_events:
        h, m = map(int, ev["time"].split(":"))
        day = start.replace(hour=h, minute=m, second=0, microsecond=0)
        while day <= end:
            if start < day <= end:
                missed.append(f"{ev['tag']} ({ev['time']})")
                break
            day += timedelta(days=1)
    if not missed:
        return None
    return "Missed while offline: " + ", ".join(missed)
