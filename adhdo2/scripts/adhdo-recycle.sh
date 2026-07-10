#!/usr/bin/env bash
# Nightly 03:30: graceful handoff then fresh session. Holds the wake lock.
set -u
exec 9>~/adhdo2/data/wake.lock
flock 9
tmux send-keys -t adhdo -l 'Nightly recycle: write a concise handoff of current state, pending follow-ups, and observations to NOTES.md, then say DONE.'
tmux send-keys -t adhdo Enter
for i in $(seq 60); do  # wait up to 5 min for busy marker to clear
  sleep 5
  [ ! -e ~/adhdo2/data/busy ] && break
done
tmux respawn-pane -k -t adhdo \
  "cd ~/adhdo2/session && ADHDO_HOME=~/adhdo2 claude --dangerously-skip-permissions"
~/adhdo2/venv/bin/python ~/adhdo2/bin/journal log decision "nightly session recycle" || true
