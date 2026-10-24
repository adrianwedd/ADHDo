import sqlite3

import pytest

from adhdolib.db import backup


def test_backup_contains_committed_wal_rows(tmp_path):
    source = tmp_path / "journal.db"
    destination = tmp_path / "backup" / "journal.db"
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE evidence(value TEXT)")
        writer.execute("INSERT INTO evidence VALUES ('committed in WAL')")
        writer.commit()
        assert source.with_name("journal.db-wal").stat().st_size > 0
        backup(source, destination)
        with sqlite3.connect(destination) as restored:
            assert restored.execute("SELECT value FROM evidence").fetchall() == [
                ("committed in WAL",)]
    assert destination.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("broken", ["missing", "corrupt", "timeout"])
def test_failed_backup_preserves_previous_snapshot(tmp_path, broken):
    source, destination = tmp_path / "journal.db", tmp_path / "backup.db"
    destination.write_bytes(b"previous snapshot")
    if broken == "corrupt":
        source.write_bytes(b"not a database")
    elif broken == "timeout":
        with sqlite3.connect(source) as conn:
            conn.execute("CREATE TABLE evidence(value)")
    with pytest.raises((sqlite3.Error, TimeoutError)):
        backup(source, destination, timeout=0 if broken == "timeout" else 30)
    assert destination.read_bytes() == b"previous snapshot"
    assert not list(tmp_path.glob(".journal-*"))
    if broken == "missing":
        assert not source.exists()
