#!/usr/bin/env bash
# Respawn claude inside the adhdo tmux pane if it died.
set -u
PANE_PID=$(tmux list-panes -t adhdo -F '#{pane_pid}' 2>/dev/null | head -1) || exit 0
[ -z "${PANE_PID:-}" ] && exit 0
if ! pgrep -P "$PANE_PID" -f claude >/dev/null; then
  ~/adhdo2/venv/bin/python ~/adhdo2/bin/journal log error "watchdog: claude dead, respawning" || true
  tmux respawn-pane -k -t adhdo \
    "cd ~/adhdo2/session && ADHDO_HOME=~/adhdo2 claude --dangerously-skip-permissions"
fi
