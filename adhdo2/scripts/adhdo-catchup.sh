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
fixed = [{"tag": "meds", "time": "08:00"}, {"tag": "bedtime", "time": "22:30"}]
msg = schedule.consolidate_missed(conn, fixed, last, time.time())
if msg:
    wake.inject(msg)
    db.log_event(conn, "wake", "wake", msg)
EOF
