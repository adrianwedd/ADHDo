import time
from datetime import datetime, timedelta

import pytest

from adhdolib import db, schedule
from adhdolib.binload import load_bin_module
from adhdolib.envelope import ToolError

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

# --- _parse_at (bin/wake) -------------------------------------------------

@pytest.fixture(scope="module")
def parse_at():
    return load_bin_module("wake")._parse_at


def test_parse_at_full_iso_datetime(parse_at):
    assert parse_at("2026-07-12T09:30:00") == datetime(2026, 7, 12, 9, 30).timestamp()


def test_parse_at_iso_datetime_with_space(parse_at):
    assert parse_at("2026-07-12 09:30:00") == datetime(2026, 7, 12, 9, 30).timestamp()


def test_parse_at_iso_date_only_is_midnight(parse_at):
    assert parse_at("2026-07-12") == datetime(2026, 7, 12).timestamp()


def test_parse_at_hh_mm_future_today(parse_at):
    soon = (datetime.now() + timedelta(minutes=5)).replace(second=0, microsecond=0)
    got = parse_at(soon.strftime("%H:%M"))
    assert got == soon.timestamp()


def test_parse_at_hh_mm_past_rolls_to_tomorrow(parse_at):
    past = (datetime.now() - timedelta(minutes=5)).replace(second=0, microsecond=0)
    got = parse_at(past.strftime("%H:%M"))
    assert got == (past + timedelta(days=1)).timestamp()
    assert got > time.time()


def test_parse_at_iso_time_with_seconds(parse_at):
    soon = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)
    got = parse_at(soon.strftime("%H:%M:%S"))
    assert got == soon.timestamp()


def test_parse_at_unpadded_hour(parse_at):
    # "9:30" style (not strict ISO) must keep working
    soon = (datetime.now() + timedelta(minutes=5)).replace(second=0, microsecond=0)
    got = parse_at("%d:%02d" % (soon.hour, soon.minute))
    expected = soon if soon.timestamp() > time.time() else soon + timedelta(days=1)
    assert got == expected.timestamp()


@pytest.mark.parametrize("bad", ["nonsense", "25:00", "12:60", "2026-13-01", ":", "12:", "1:2:3:4"])
def test_parse_at_invalid_raises_usage_error(parse_at, bad):
    with pytest.raises(ToolError) as exc:
        parse_at(bad)
    assert exc.value.code == "usage"
