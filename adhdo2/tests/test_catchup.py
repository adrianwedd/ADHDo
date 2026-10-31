import time
from types import SimpleNamespace

import pytest
from adhdolib import db, schedule
from adhdolib.binload import load_bin_module


def test_failed_catchup_keeps_reminders_due(adhdo_home, monkeypatch):
    catchup = load_bin_module('adhdo-catchup')
    conn = db.connect()
    schedule.add(conn, time.time() - 60, 'check in')
    def broken(text):
        raise RuntimeError('tmux unavailable')
    monkeypatch.setattr(catchup, 'load_bin_module', lambda _: SimpleNamespace(inject=broken))
    with pytest.raises(RuntimeError, match='tmux unavailable'):
        catchup.run(_test_conn=conn)
    assert len(schedule.due(conn, time.time())) == 1
    assert conn.execute("SELECT COUNT(*) FROM events WHERE type='wake'").fetchone()[0] == 0


@pytest.mark.parametrize('delivery', ['sent', 'queued'])
def test_catchup_acknowledges_only_after_delivery(adhdo_home, monkeypatch, delivery):
    catchup = load_bin_module('adhdo-catchup')
    conn = db.connect()
    schedule.add(conn, time.time() - 60, 'first')
    schedule.add(conn, time.time() - 50, 'second')
    sent = []
    def inject(text):
        assert len(schedule.due(conn, time.time())) == 2
        sent.append(text)
        return delivery
    monkeypatch.setattr(catchup, 'load_bin_module', lambda _: SimpleNamespace(inject=inject))
    assert catchup.run(_test_conn=conn) == {'catchup': delivery, 'scheduled': 2}
    assert len(sent) == 1 and 'first, second' in sent[0]
    assert schedule.due(conn, time.time()) == []
    assert catchup.run(_test_conn=conn) == {'catchup': 'nothing_due'}
    assert len(sent) == 1
