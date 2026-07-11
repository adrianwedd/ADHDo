#!/usr/bin/env bash
# Idempotent: replaces the ADHDO block in the pi user's crontab and
# (re)installs the heartbeat systemd user timer.
#
# The heartbeat deliberately does NOT live in cron: a step value of 25 in
# cron only divides the minute field within each hour (:00, :25, :50, then
# :00 again),
# which leaves a 10-minute gap at every hour boundary instead of a true
# 25-minute cadence. A systemd user timer with OnUnitActiveSec=25min fires
# 25 minutes after the previous activation regardless of wall-clock hour,
# and the project already manages user units (adhdo-httpd, adhdo-tmux), so
# it fits the existing deployment design. See systemd/adhdo-heartbeat.timer.
set -eu
PY=~/adhdo2/venv/bin/python
TMP=$(mktemp)
crontab -l 2>/dev/null | sed '/# ADHDO-BEGIN/,/# ADHDO-END/d' > "$TMP" || true
cat >> "$TMP" <<CRON
# ADHDO-BEGIN
0 8 * * *   ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event meds >/dev/null 2>&1
30 22 * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event bedtime >/dev/null 2>&1
*/5 * * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/adhdo-dispatch >/dev/null 2>&1
*/5 * * * * \$HOME/adhdo2/scripts/adhdo-watchdog.sh >/dev/null 2>&1
15 3 * * *  \$HOME/adhdo2/scripts/adhdo-rollup.sh >/dev/null 2>&1
30 3 * * *  \$HOME/adhdo2/scripts/adhdo-recycle.sh >/dev/null 2>&1
@reboot     \$HOME/adhdo2/scripts/adhdo-catchup.sh >/dev/null 2>&1
# ADHDO-END
CRON
crontab "$TMP"
rm "$TMP"

# Heartbeat: true 25-minute cadence via systemd user timer (see header).
mkdir -p ~/.config/systemd/user
cp ~/adhdo2/systemd/adhdo-heartbeat.service ~/adhdo2/systemd/adhdo-heartbeat.timer \
   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now adhdo-heartbeat.timer
echo "cron installed; heartbeat timer enabled"
