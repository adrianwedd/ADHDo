#!/usr/bin/env bash
# @reboot: deliver one consolidated missed-events wake after the session is up.
sleep 120
~/adhdo2/venv/bin/python - <<'EOF'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.home() / "adhdo2"))

import time
from adhdolib import db, schedule
from adhdolib.config import load_config
from adhdolib.binload import load_bin_module
wake = load_bin_module("wake")
conn = db.connect()
row = conn.execute("SELECT MAX(ts) FROM events WHERE type='wake'").fetchone()
last = row[0] or (time.time() - 86400)
now = time.time()
fixed = [{"tag": "meds", "time": "08:00"}, {"tag": "bedtime", "time": "22:30"}]
msg = schedule.consolidate_missed(conn, fixed, last, now)

# Also fold in any overdue *scheduled* rows (one-off follow-ups set via
# `wake --at`) so we still send exactly one consolidated inject, not one
# per missed reminder.
overdue = schedule.due(conn, now)
if overdue:
    tags = ", ".join(tag for _, tag in overdue)
    overdue_msg = f"Missed while offline: {tags}"
    msg = f"{msg}. {overdue_msg}" if msg else overdue_msg
    schedule.mark_delivered(conn, [id_ for id_, _ in overdue])

if msg:
    wake.inject(msg)
    db.log_event(conn, "wake", "wake", msg)
EOF
