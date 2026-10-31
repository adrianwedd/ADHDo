#!/usr/bin/env bash
# @reboot: deliver one consolidated missed-events wake after the session is up.
set -eu
sleep 120
ADHDO_HOME=${ADHDO_HOME:-$HOME/adhdo2}
export ADHDO_HOME
exec "$ADHDO_HOME/venv/bin/python" "$ADHDO_HOME/bin/adhdo-catchup"
