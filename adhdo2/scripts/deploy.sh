#!/usr/bin/env bash
# Deploy adhdo2 from the repo to pi@pi5-hailo:~/adhdo2
set -eu
SRC="$(cd "$(dirname "$0")/.." && pwd)"
rsync -av --exclude venv --exclude data --exclude tts-cache --exclude jellyfin \
  "$SRC/" pi@pi5-hailo:~/adhdo2/
ssh pi@pi5-hailo '
  set -eu
  cd ~/adhdo2
  [ -d venv ] || python3 -m venv venv
  venv/bin/pip -q install PyYAML pychromecast pytest
  mkdir -p data tts-cache jellyfin/config
  [ -f config.yaml ] || cp config.example.yaml config.yaml
  mkdir -p ~/.config/systemd/user
  cp systemd/*.service ~/.config/systemd/user/
  systemctl --user daemon-reload
  echo "deployed; run scripts/install-cron.sh and enable units when ready"
'
