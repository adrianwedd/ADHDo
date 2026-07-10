from datetime import datetime, time as dtime

def _in_quiet_hours(now: datetime, quiet: list[str]) -> bool:
    start = dtime(*map(int, quiet[0].split(":")))
    end = dtime(*map(int, quiet[1].split(":")))
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # wraps midnight

def check_allowed(now, urgency, event, nudges_last_hour, cfg):
    ncfg = cfg["nudge"]
    if nudges_last_hour >= ncfg["max_per_hour"]:
        return (False, "rate_limited")
    if _in_quiet_hours(now, ncfg["quiet_hours"]):
        if urgency != "high":
            return (False, "quiet_hours")
        if event not in ncfg["high_urgency_events"]:
            return (False, "bad_override")
    return (True, "ok")
