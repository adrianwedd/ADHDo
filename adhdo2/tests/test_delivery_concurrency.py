from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
import time

from adhdolib import db, schedule
from adhdolib.binload import load_bin_module


def test_dispatch_cannot_race_catchup(adhdo_home, monkeypatch):
    catchup = load_bin_module('adhdo-catchup')
    dispatch = load_bin_module('adhdo-dispatch')
    conn = db.connect()
    schedule.add(conn, time.time() - 60, 'only once')
    conn.close()
    entered, release, second_started, duplicated = Event(), Event(), Event(), Event()
    calls = []
    def first_inject(text):
        calls.append(text)
        entered.set()
        assert release.wait(5)
        return 'sent'
    def duplicate(text):
        duplicated.set()
        calls.append(text)
        return 'sent'
    monkeypatch.setattr(catchup, 'load_bin_module', lambda _: SimpleNamespace(inject=first_inject))
    monkeypatch.setattr(dispatch, 'inject', duplicate)
    def second():
        second_started.set()
        return dispatch.run()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(catchup.run)
        assert entered.wait(5)
        other = pool.submit(second)
        assert second_started.wait(5)
        try:
            # The second consumer must block until the first has acknowledged.
            assert not duplicated.wait(0.2)
            assert not other.done()
        finally:
            release.set()
        assert first.result(timeout=5)['scheduled'] == 1
        assert other.result(timeout=5) == {'delivered': 0, 'queued': 0}
    assert len(calls) == 1
