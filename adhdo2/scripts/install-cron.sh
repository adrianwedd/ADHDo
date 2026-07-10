#!/usr/bin/env bash
# Idempotent: replaces the ADHDO block in the pi user's crontab.
set -eu
PY=~/adhdo2/venv/bin/python
TMP=$(mktemp)
crontab -l 2>/dev/null | sed '/# ADHDO-BEGIN/,/# ADHDO-END/d' > "$TMP" || true
cat >> "$TMP" <<CRON
# ADHDO-BEGIN
*/25 * * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake "[heartbeat] Run state, reason, act or do nothing." >/dev/null 2>&1
0 8 * * *   ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event meds >/dev/null 2>&1
30 22 * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event bedtime >/dev/null 2>&1
*/5 * * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/adhdo-dispatch >/dev/null 2>&1
*/5 * * * * \$HOME/adhdo2/scripts/adhdo-watchdog.sh >/dev/null 2>&1
30 3 * * *  \$HOME/adhdo2/scripts/adhdo-recycle.sh >/dev/null 2>&1
@reboot     \$HOME/adhdo2/scripts/adhdo-catchup.sh >/dev/null 2>&1
# ADHDO-END
CRON
crontab "$TMP"
rm "$TMP"
echo "cron installed"
