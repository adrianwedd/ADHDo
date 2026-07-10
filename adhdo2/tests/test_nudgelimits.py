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
