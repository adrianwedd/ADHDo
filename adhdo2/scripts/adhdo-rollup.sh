#!/usr/bin/env bash
# Nightly 03:15: aggregate daily journal outcomes into rollup rows, prune
# raw rows older than 90 days, and keep a backup copy of journal.db.
set -u
ADHDO_HOME=${ADHDO_HOME:-$HOME/adhdo2}
export ADHDO_HOME
"$ADHDO_HOME"/venv/bin/python "$ADHDO_HOME"/bin/journal rollup || \
  "$ADHDO_HOME"/venv/bin/python "$ADHDO_HOME"/bin/journal log error "nightly rollup failed" || true
mkdir -p "$ADHDO_HOME"/data/backup
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$ADHDO_HOME"/data/journal.db \
    ".backup '$ADHDO_HOME/data/backup/journal.db'" || true
else
  cp "$ADHDO_HOME"/data/journal.db "$ADHDO_HOME"/data/backup/journal.db || true
fi
