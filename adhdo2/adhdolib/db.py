import json, os, pathlib, sqlite3, tempfile, time
from contextlib import closing
from .config import home

EVENT_TYPES = frozenset({"nudge", "cast", "med", "meal", "break",
                         "decision", "outcome", "feedback", "wake", "error"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, ts REAL NOT NULL,
  source TEXT NOT NULL, type TEXT NOT NULL, payload_json TEXT);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, ts REAL NOT NULL,
  tool TEXT NOT NULL, argv TEXT, ok INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS schedule(
  id INTEGER PRIMARY KEY, due_ts REAL NOT NULL,
  tag TEXT, delivered INTEGER DEFAULT 0,
  UNIQUE(due_ts, tag));
CREATE TABLE IF NOT EXISTS rollups(
  day TEXT NOT NULL, metric TEXT NOT NULL, value_json TEXT,
  PRIMARY KEY(day, metric));
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, ts);
"""

def connect() -> sqlite3.Connection:
    path = home() / "data" / "journal.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=3.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.executescript(SCHEMA)
    return conn

def backup(source, destination, timeout=30):
    """Atomically retain a consistent snapshot, including committed WAL rows.

    Open the source read-only: a missing journal must not become an empty
    successful backup. Keep the previous snapshot if any operation fails.
    """
    source, destination = pathlib.Path(source), pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".journal-", suffix=".db",
                                dir=destination.parent)
    os.close(fd)
    temporary = pathlib.Path(name)
    deadline = time.monotonic() + timeout

    def progress(status, remaining, total):
        if time.monotonic() >= deadline:
            raise TimeoutError("journal backup exceeded its time limit")

    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst, pages=256, progress=progress, sleep=0.05)
                if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise sqlite3.DatabaseError("journal backup integrity check failed")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    root = home() / "data"
    backup(root / "journal.db", root / "backup" / "journal.db")

def log_event(conn, source: str, type: str, payload: str):
    if type not in EVENT_TYPES:
        raise ValueError(f"unknown event type: {type}")
    if isinstance(payload, str):
        try:
            json.loads(payload)
            payload_json = payload
        except (ValueError, TypeError):
            payload_json = json.dumps(payload)
    else:
        payload_json = json.dumps(payload)
    conn.execute("INSERT INTO events(ts, source, type, payload_json) VALUES(?,?,?,?)",
                 (time.time(), source, type, payload_json))
    conn.commit()

def audit(conn, tool: str, argv: list, ok: bool, detail: str = ""):
    conn.execute("INSERT INTO audit(ts, tool, argv, ok, detail) VALUES(?,?,?,?,?)",
                 (time.time(), tool, json.dumps(argv), int(ok), detail))
    conn.commit()
