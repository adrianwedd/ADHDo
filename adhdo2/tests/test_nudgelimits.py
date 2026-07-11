from datetime import datetime
from adhdolib.config import DEFAULTS
from adhdolib.nudgelimits import check_allowed

DAY = datetime(2026, 7, 10, 14, 0)      # 2pm
NIGHT = datetime(2026, 7, 10, 23, 30)   # 11:30pm
EARLY = datetime(2026, 7, 10, 6, 30)    # 6:30am (still quiet)

def test_normal_daytime_ok():
    assert check_allowed(DAY, "low", None, 0, DEFAULTS) == (True, "ok")

def test_hourly_cap():
    assert check_allowed(DAY, "low", None, 4, DEFAULTS) == (False, "rate_limited")

def test_quiet_hours_block_low():
    assert check_allowed(NIGHT, "low", None, 0, DEFAULTS) == (False, "quiet_hours")
    assert check_allowed(EARLY, "low", None, 0, DEFAULTS) == (False, "quiet_hours")

def test_high_urgency_bypasses_quiet_hours_only():
    assert check_allowed(NIGHT, "high", "medication", 0, DEFAULTS) == (True, "ok")
    assert check_allowed(NIGHT, "high", "medication", 4, DEFAULTS) == (False, "rate_limited")

def test_high_urgency_requires_enumerated_event():
    assert check_allowed(NIGHT, "high", "party", 0, DEFAULTS) == (False, "bad_override")
    assert check_allowed(NIGHT, "high", None, 0, DEFAULTS) == (False, "bad_override")

# --- quiet-hours boundary semantics: half-open [start, end) ----------------

def _quiet(hh, mm, window):
    from adhdolib.nudgelimits import _in_quiet_hours
    return _in_quiet_hours(datetime(2026, 7, 10, hh, mm), window)

WRAP = ["22:00", "07:00"]     # wraps midnight (the default)
DAYTIME = ["13:00", "14:00"]  # non-wrapping window

def test_wrap_exactly_at_start_is_quiet():
    assert _quiet(22, 0, WRAP) is True

def test_wrap_just_before_start_is_not_quiet():
    assert _quiet(21, 59, WRAP) is False

def test_wrap_exactly_at_end_is_not_quiet():
    assert _quiet(7, 0, WRAP) is False

def test_wrap_just_before_end_is_quiet():
    assert _quiet(6, 59, WRAP) is True

def test_wrap_midnight_is_quiet():
    assert _quiet(0, 0, WRAP) is True

def test_nonwrap_exactly_at_start_is_quiet():
    assert _quiet(13, 0, DAYTIME) is True

def test_nonwrap_exactly_at_end_is_not_quiet():
    assert _quiet(14, 0, DAYTIME) is False

def test_nonwrap_inside_and_outside():
    assert _quiet(13, 30, DAYTIME) is True
    assert _quiet(12, 59, DAYTIME) is False
    assert _quiet(14, 1, DAYTIME) is False

def test_equal_start_end_window_is_never_quiet():
    assert _quiet(3, 0, ["07:00", "07:00"]) is False
    assert _quiet(7, 0, ["07:00", "07:00"]) is False

def test_check_allowed_at_quiet_start_boundary_blocks_low():
    at_start = datetime(2026, 7, 10, 22, 0)
    assert check_allowed(at_start, "low", None, 0, DEFAULTS) == (False, "quiet_hours")

def test_check_allowed_at_quiet_end_boundary_allows_low():
    at_end = datetime(2026, 7, 10, 7, 0)
    assert check_allowed(at_end, "low", None, 0, DEFAULTS) == (True, "ok")
