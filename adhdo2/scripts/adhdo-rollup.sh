#!/usr/bin/env bash
# Nightly 03:15: aggregate daily journal outcomes into rollup rows, prune
# raw rows older than 90 days, and keep a backup copy of journal.db.
set -u
ADHDO_HOME=${ADHDO_HOME:-$HOME/adhdo2}
export ADHDO_HOME
"$ADHDO_HOME"/venv/bin/python "$ADHDO_HOME"/bin/journal rollup || \
  "$ADHDO_HOME"/venv/bin/python "$ADHDO_HOME"/bin/journal log error "nightly rollup failed" || true
# Python is already required by the journal. Its backup API includes WAL data
# without requiring the sqlite3 CLI, and preserves the previous backup on error.
cd "$ADHDO_HOME"
"$ADHDO_HOME"/venv/bin/python -m adhdolib.db
