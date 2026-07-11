# ADHDo 2.0 P1 Hardware E2E (pi5-hailo)

> How boot catch-up interacts with the dispatcher and fixed-event schedule
> (and why they never double-fire) is documented in
> [docs/catchup-vs-schedule.md](docs/catchup-vs-schedule.md).
>
> Note (P2 quality pass): the heartbeat is no longer a `*/25` cron line —
> `install-cron.sh` now installs the `adhdo-heartbeat.timer` systemd user
> timer (true 25-min cadence). On-device step: re-run
> `~/adhdo2/scripts/install-cron.sh` after the next deploy so the old cron
> heartbeat line is replaced and the timer is enabled.

## P3 Telegram bridge — on-device setup (human steps)

1. Create a bot with @BotFather on Telegram; copy the bot token.
2. On the Pi, put the token in `~/adhdo2/config.yaml` under
   `telegram.bot_token` (or export `TELEGRAM_BOT_TOKEN` in the service
   environment — env overrides config).
3. Message the bot once from your own Telegram account, then find your
   numeric chat ID (e.g. via `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"`
   → `message.chat.id`) and add it to `telegram.chat_id_allowlist` in
   `~/adhdo2/config.yaml`.
4. `cp ~/adhdo2/systemd/adhdo-telegram.service ~/.config/systemd/user/ &&
   systemctl --user daemon-reload && systemctl --user enable --now adhdo-telegram`
5. Verify:
   - [ ] Text the bot "hello" → appears in the adhdo tmux pane as
         `[telegram chat:<id>] User says: "hello"` and Claude responds.
   - [ ] `bin/adhdo-telegram send <chat_id> "test reply"` → arrives in Telegram.
   - [ ] Message from a non-allowlisted chat → ignored, `error` row in journal.
   - [ ] Send a photo → bot replies "Text messages only"; nothing injected.
   - [ ] 7 rapid messages in a minute → later ones get a rate-limit reply.

Run 2026-07-10, automated portion only (no audible verification performed —
that requires a human physically listening at the Pi's location).

- [x] `bin/state` returns full schema; devices list shows real Nest devices online
      Result: schema OK after fixing a bug (see below). `devices` returned `[]`
      in this run — pychromecast discovery window (5s) did not resolve any of
      the 5 discovered `_googlecast._tcp` mDNS devices (Shack Speakers, SHIELD,
      Nest Hub Max, Nest Mini, Office Mini — confirmed via `avahi-browse`).
      Bug found & fixed: `bin/state`'s `scan_devices()` used
      `importlib.util.spec_from_file_location("cast_cli", .../bin/cast)` with no
      loader, so `spec.loader` was `None` on an extensionless file → crashed
      with `AttributeError: 'NoneType' object has no attribute 'loader'`.
      Fixed by passing an explicit `importlib.machinery.SourceFileLoader`.
      NOT independently re-verified that pychromecast now actually resolves
      device names against `config.yaml`'s `devices` map — needs human/audible
      follow-up if `bin/cast play <mood>` doesn't find the device by friendly
      name.
      Output: `{"ts": ..., "day_part": "afternoon", "devices": [], "last":
      {"med": null, "meal": null, "break": null, "nudge": null}, "scheduled":
      [], "disk": {"pct": 86.4, "warn": false}}`

- [ ] `bin/cast play focus` → music audibly plays on default device (source: jellyfin)
      SKIPPED — audible verification, human step.

- [ ] Stop Jellyfin container → `cast play focus` falls back to stream (source: stream)
      SKIPPED — audible verification, human step.

- [ ] `bin/nudge "test nudge"` → device speaks; interrupted music resumes after
      SKIPPED — audible verification, human step. The resume-wait polish
      (poll media_controller.status until idle, max 30s in `_resume_previous`)
      called out in the brief as "now observable on hardware" was NOT
      implemented in this automated pass — it requires audibly observing
      actual resume timing, which is a human step. `_resume_previous()`
      exists in `bin/nudge` (line 45) but its current polling behavior needs
      human review with real hardware before refining.

- [x] 5 rapid nudges → 5th returns {"error":"rate_limited"}
      Verified equivalent behavior non-audibly: temporarily set
      `nudge.max_per_hour: 0` in config.yaml (restored after) and ran
      `bin/nudge "test nudge"` once → immediately got:
      `{"error": "rate_limited", "detail": "nudge blocked; do not retry this cycle"}`
      exit code 1. This confirms the rate-limit gate fires before any TTS/cast
      call (no sound), which is the logic under test. Did not run 5 literal
      calls against a real device (audible).

- [x] `bin/nudge "x"` during configured quiet hours → {"error":"quiet_hours"};
      `--urgency high --event medication` → speaks
      Verified the quiet_hours branch non-audibly: temporarily set
      `nudge.quiet_hours: ["00:00", "23:59"]` in config.yaml (restored after)
      and ran `bin/nudge "test nudge"` → immediately got:
      `{"error": "quiet_hours", "detail": "nudge blocked; do not retry this cycle"}`
      exit code 1. Did NOT test the high-urgency override path (`--urgency high
      --event medication` should still speak during quiet hours) — that
      requires an audible check that it does speak. SKIPPED that half.
      config.yaml confirmed restored to original values afterward
      (`max_per_hour: 4`, `quiet_hours: ["22:00", "07:00"]`).

- [ ] `bin/wake "hello from wake"` → text appears in the adhdo tmux pane and Claude responds
      SKIPPED — the adhdo tmux Claude session is not logged in yet (see below);
      Claude cannot respond until a human runs `/login` interactively in the
      pane. Not attempted to avoid interfering with the auth flow.

- [ ] `bin/wake "test"` while Claude is mid-response → "queued"; adhdo-dispatch delivers it after
      SKIPPED — depends on a logged-in, responsive Claude session (see above).

- [ ] `bin/wake --at <2 min from now> --tag t1` → dispatcher injects within 5 min
      SKIPPED — depends on a logged-in Claude session; also install-cron.sh
      was intentionally NOT run (see Step 4 notes), so the dispatcher isn't
      scheduled yet.

- [ ] Kill claude in the pane (`pkill -f claude`) → watchdog respawns within 5 min; journal has error row
      SKIPPED — deferred until after human completes `/login`; didn't want to
      kill/respawn an unauthenticated session repeatedly.

- [ ] `scripts/adhdo-recycle.sh` → handoff written to NOTES.md, fresh session, continuity on greet
      SKIPPED — depends on a working, logged-in Claude session.

- [ ] Reboot Pi with a meds event in the past → single consolidated catch-up wake, no storm
      SKIPPED — explicitly instructed not to reboot the Pi during this
      automated pass.

- [ ] Nightly rollup: after re-running `install-cron.sh` (adds a 03:15
      `adhdo-rollup.sh` entry), verify next morning that `journal rollup`
      wrote rows (`sqlite3 ~/adhdo2/data/journal.db "SELECT * FROM rollups"`)
      and `~/adhdo2/data/backup/journal.db` exists. Depends on cron being
      enabled (human-gated switch below).

- [ ] Full heartbeat observed: cron fires, session runs state, journals a decision
      SKIPPED — install-cron.sh intentionally NOT run yet (final human-gated
      switch, see Step 4 notes). No heartbeat cron installed, so nothing to
      observe.

## Step 1: Pi prerequisites — DONE (automated)
`sudo -n apt-get update && sudo -n apt-get install -y tmux espeak-ng ffmpeg && sudo -n loginctl enable-linger pi`
ran successfully with passwordless sudo (no human needed). `tmux` and
`espeak-ng` newly installed; `ffmpeg` already present. `loginctl show-user pi`
confirms `Linger=yes`.

## Step 2: Piper — PIPER_OK
`pipx` is not installed on the Pi (`command not found: pipx`), so fell back to
the documented alternative: `~/adhdo2/venv/bin/pip install piper-tts`, which
succeeded (`piper-tts-1.4.2`, plus `onnxruntime`, `numpy`, etc). Confirmed
working: `echo test | ~/adhdo2/venv/bin/piper --help` exits 0 and prints usage.
Result: **PIPER_OK** (not falling back to espeak-ng, though espeak-ng is also
installed as a safety net per Step 1).

## Step 3: Static IP / devices — partially human
- Pi's current LAN IP: `192.168.0.115` (eth0, confirmed via `ip route get 1.1.1.1`).
- DID NOT set a DHCP reservation in the router — **human step**, noted.
- Cast devices discovered via `avahi-browse -t -r _googlecast._tcp`:
  - `Shack Speakers` (Chromecast Audio)
  - `SHIELD` (SHIELD Android TV)
  - `Nest Hub Max` (Google Nest Hub Max)
  - `Nest Mini` (Google Nest Mini)
  - `Office Mini` (Google Home Mini)
- Wrote `~/adhdo2/config.yaml` on the Pi with:
  - `lan_ip: 192.168.0.115`
  - `devices: {office: "Nest Hub Max", kitchen: "Nest Mini", shack: "Shack Speakers", officemini: "Office Mini"}`
  - `default_device: office` (Nest Hub Max)
  - `moods.calm.streams: ["https://ice1.somafm.com/groovesalad-256-mp3"]`
  - `moods.focus.streams: ["https://ice1.somafm.com/dronezone-256-mp3"]`
  - `jellyfin.url: "http://192.168.0.115:8096"` (api_key still placeholder,
    pending Jellyfin setup wizard — human step)
  - `moods.*.jellyfin_playlist` left as `"<id>"` placeholders — human step,
    depends on Jellyfin Music library + playlists being created.

## Step 4: Deploy + services
- `adhdo2/scripts/deploy.sh` run from the worktree: rsync + venv + pip installs
  succeeded. Fixed a review-noted gap: deploy.sh now also
  `mkdir -p jellyfin/config` (previously only `data tts-cache`), needed by the
  Jellyfin compose volume mount. (Committed below.)
- Also discovered adhdolib isn't pip-installable as-is (`pyproject.toml` has
  no package/module discovery config, so `pip install -e .` fails with a
  multi-package-discovery error). Worked around by invoking scripts with
  `PYTHONPATH=/home/pi/adhdo2` — this is what `bin/state` needed to find
  `adhdolib`. Not fixed in pyproject.toml since scope of this task was
  provisioning, not a packaging refactor; flagging for a future task.
- `systemctl --user enable --now adhdo-httpd` → **active (running)**, PID
  confirmed, serving `python3 -m http.server 8765`.
- `systemctl --user enable --now adhdo-tmux` → **active (running)**.
  `tmux capture-pane -t adhdo -p` showed:
  1. A one-time "trust this folder" dialog (answered "1. Yes" — this is not
     an auth step, just Claude Code's folder-trust prompt, safe to confirm).
  2. A "try the new fullscreen renderer?" UI prompt (answered "2. Not now" —
     cosmetic, not auth-related).
  3. Final state: Claude Code v2.1.202 is running but the status bar reads
     **"Not logged in · Run /login"**.
  **HUMAN STEP REQUIRED**: an interactive `claude /login` (OAuth flow) must be
  completed in the `adhdo` tmux pane over SSH before wake/nudge-to-Claude
  interactions will work. Did not attempt to run `/login` myself since it
  requires opening a browser-based OAuth URL and pasting a code back — an
  interactive human action, exactly as anticipated in the task brief.
- `install-cron.sh` was **NOT run**, as instructed — this is the final
  human-gated switch (starts heartbeats/catch-up before the human verifies the
  Claude session works). **Human step**: run
  `ssh pi@pi5-hailo '~/adhdo2/scripts/install-cron.sh'` only after confirming
  `/login` succeeded and a basic `bin/wake` round-trip works.

## Step 5: Jellyfin
- `docker compose -f jellyfin-compose.yml up -d` pulled the image and started
  the container successfully (`docker ps` shows `jellyfin` container `Up ...
  (healthy)`).
- Verified port 8096 responds: `curl -s -o /dev/null -w '%{http_code}'
  http://localhost:8096/` → `302` (redirect to setup wizard — expected for a
  fresh instance). `/health` → `503` (also expected pre-setup-wizard).
- **HUMAN STEP REQUIRED**: browse to `http://192.168.0.115:8096`, complete the
  setup wizard, disable transcoding + chapter images, add a Music library,
  create `focus`/`calm` playlists, generate an API key, and put the playlist
  IDs + API key into `~/adhdo2/config.yaml` on the Pi (currently placeholders).

## Bugs found & fixed during this pass
1. `bin/state`'s `scan_devices()` crashed (`AttributeError: 'NoneType' object
   has no attribute 'loader'`) loading `bin/cast` via
   `importlib.util.spec_from_file_location` without an explicit loader (the
   file has no `.py` extension so the loader couldn't be inferred). Fixed by
   using `importlib.machinery.SourceFileLoader` explicitly. Committed.
2. `deploy.sh` didn't create `~/adhdo2/jellyfin/config` (needed by the
   Jellyfin docker-compose volume mount) — added `mkdir -p ... jellyfin/config`
   alongside the existing `data tts-cache`. Committed.

## Summary of human-gated remaining work
1. Router DHCP reservation for `192.168.0.115` (Pi's current IP).
2. Interactive `claude /login` inside the `adhdo` tmux pane over SSH.
3. Jellyfin setup wizard (`http://192.168.0.115:8096`): admin account, disable
   transcoding + chapter images, add Music library, create `focus`/`calm`
   playlists, generate API key; then fill in `jellyfin.api_key` and
   `moods.*.jellyfin_playlist` in `~/adhdo2/config.yaml`.
4. All audible verification items in this checklist (cast playback, nudge TTS,
   resume-after-nudge timing, rate-limit-with-real-device, quiet-hours
   high-urgency override, wake→Claude round-trip, dispatcher delivery,
   watchdog respawn, recycle handoff, reboot catch-up, full heartbeat) — all
   require either a logged-in Claude session, a completed Jellyfin setup, or a
   human physically listening at the Pi.
5. Run `~/adhdo2/scripts/install-cron.sh` only after (2) is confirmed working
   via a manual `bin/wake` test — this starts the heartbeat/catch-up cron and
   was intentionally left un-run by this automated pass.
6. Consider fixing `pyproject.toml` package discovery so `pip install -e .`
   works without needing `PYTHONPATH` workarounds (not done in this pass —
   out of scope for provisioning, noted for a future cleanup task).
7. The `_resume_previous()` polling refinement mentioned in the brief (poll
   `media_controller.status` until idle, max 30s) was NOT implemented — it
   requires audible hardware observation to tune correctly, which is a human
   step.
8. P3 dashboard (`bin/adhdo-dashboard`, port 8766): on-device verification —
   `systemctl --user enable --now adhdo-dashboard` (unit in
   `systemd/adhdo-dashboard.service`), then open
   `http://<lan_ip>:8766/` from another LAN machine and confirm the page
   shows live state (devices, disk, last-event ages) and recent journal rows,
   auto-refreshing every 30s. Confirm `curl -X POST http://<lan_ip>:8766/`
   returns 405 (read-only) and that the service is NOT reachable from outside
   the LAN (binds to `dashboard.bind`, defaulting to `lan_ip`). Contract
   tests (routing, JSON schemas, secret scrubbing, method rejection) are
   covered in `tests/test_dashboard.py`.
