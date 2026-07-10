# ADHDo 2.0 Design — Resident Claude Cognitive Companion

**Date:** 2026-07-10 (rev 3, after two QA rounds by hermes/codex/agy)
**Status:** Approved approach (Option A: fresh toolbelt, Claude Code as the brain)
**Target host:** pi5-hailo (Raspberry Pi 5, Debian, aarch64)

## Goal

Restore and surpass the original ADHDo vision: a personal executive-function
support system that proactively nudges, wrangles music and smart-speaker
devices, and maintains situational awareness (calendar, Gmail, time-of-day,
activity patterns) — without the fragile browser-automation auth and
overgrown FastAPI orchestration of the original codebase.

## Core Decision

**The brain is a persistent Claude Code session** running in tmux on
pi5-hailo (clawdcraft-style), not a Python cognitive loop. Claude Code
natively provides reasoning, tool use, memory, and — inside the session —
connector/MCP access to Gmail and Google Calendar. The Python codebase
shrinks to a small toolbelt of CLIs the session invokes via Bash.

**Responsibility split (explicit):** Google data (calendar, Gmail) is read
*only* by the resident session via its connectors; the toolbelt never talks
to Google. The toolbelt owns local facts: devices, playback, nudges,
schedule, journal. When the session observes a connector failure or re-auth
need, it journals it (`type: error`) and nudges Adrian to re-auth — the
`state` tool does not (and cannot) probe connector health. Connector
provisioning is a one-time interactive login on the Pi over SSH (P2 task).

The original ADHDo repo stays on the Mac as **reference only** — mood
playlists, nudge phrasing, crisis regex patterns (`llm_client.py`,
`security_middleware.py`), quiet-hours defaults, and pychromecast know-how
get cherry-picked, not imported.

## Verified Environment (2026-07-10 inventory)

- Claude Code 2.1.74, Node, Python 3, Docker installed on pi5-hailo.
- Docker stack running: sonarr, radarr, qbittorrent (via gluetun), prowlarr,
  frigate, dashy. Ollama on :11434. Mosquitto MQTT on :1883.
- **Chromecast discovery works** via avahi: Nest Hub Max, Nest Mini,
  Google Home Mini, Chromecast Audio, Shield TV all visible.
- Missing: tmux, Jellyfin, pychromecast, Piper, the ADHDo code itself.
- Disk: 92% full (~160 GB free) — see Media §.
- **Prerequisites (P1 setup):** DHCP reservation / static IP for the Pi;
  **verify Piper TTS aarch64 binary runs** (fallback: espeak-ng, already
  packaged for Debian arm64 — lower quality but guaranteed).

## Architecture

```
┌──────────────────────── pi5-hailo ────────────────────────┐
│  systemd user units (linger enabled):                     │
│    adhdo-tmux.service   → tmux server + session "adhdo"   │
│    adhdo-httpd.service  → python http.server, serves ONLY │
│                           ~/adhdo2/tts-cache, LAN-IP:8765,│
│                           no auth (LAN-only by binding)   │
│  cron (user crontab):                                     │
│    */25 heartbeat · fixed events (meds, bedtime)          │
│    */5  dispatcher (due scheduled wakes, pending queue)   │
│    */5  watchdog (claude alive in pane? restart pane)     │
│    03:30 session recycle                                  │
│    @reboot catch-up                                       │
│                                                           │
│  ~/adhdo2/bin   cast | nudge | state | journal | wake     │
│  ~/adhdo2/config.yaml   (schema below)                    │
│  ~/adhdo2/data/journal.db  SQLite, WAL                    │
│  ~/adhdo2/NOTES.md      session working memory            │
│                                                           │
│  Docker: jellyfin (LAN-IP bound; music-only, no transcode)│
└───────────────────────────────────────────────────────────┘
```

### Wake-up & serialization (concrete contract)

`wake` is the only writer to the session. Contract:

- **The flock is the gate.** `wake` holds `~/adhdo2/data/wake.lock` for the
  whole injection. A busy marker (`data/busy`) is maintained by Claude Code
  hooks — `UserPromptSubmit` creates it, `Stop` removes it (both are
  supported hook events in Claude Code 2.x); it is **advisory**: if present,
  `wake` defers. Stale markers (>15 min) are ignored and cleaned. If
  deferred, the payload is appended to `data/pending.txt`; the 5-min
  dispatcher retries delivery.
- **Injection escaping:** payloads are sanitized (control chars stripped,
  newlines collapsed to `\n` literals), sent with `tmux send-keys -l`
  (literal mode, no key-name interpretation), then `Enter` sent separately.
  This is also the P3 Telegram path — free text can never become tmux
  commands.
- **`wake --at <time> [--tag T]`** writes a row to the `schedule` table in
  journal.db (`due_ts, tag, delivered`). The 5-min dispatcher delivers due
  rows (marking delivered; dedup by tag+due). Survives reboot by
  construction; precision is ±5 min, which is fine for nudges.
- **Fixed events** are cron entries calling `wake --event meds` etc.
- **Missed events:** on boot, `@reboot` catch-up compares last-delivered
  events against the fixed schedule and `schedule` table, and delivers at
  most **one** consolidated "you missed X and Y" wake — no nudge storm.
- **Watchdog:** systemd only keeps the tmux server alive. A 5-min cron
  checks that a `claude` process is a child of the "adhdo" pane
  (`tmux list-panes -F '#{pane_pid}'` + pgrep); if not, it respawns the
  pane command and journals the restart.
- **Nightly recycle (03:30, no fixed events within ±1 h):** takes the wake
  lock, injects a handoff prompt ("write state to NOTES.md"), polls for the
  busy marker to clear (max 5 min), then restarts the pane. `pending.txt`
  and the `schedule` table are untouched — the dispatcher delivers them to
  the new session. On start the session reads CLAUDE.md, NOTES.md, and
  `journal recent`; in-flight reasoning at crash time is accepted as lost.

### The cognitive loop

On each wake-up the session:
1. Runs `state`; consults calendar/Gmail connectors when relevant.
2. Reasons — time of day, upcoming events, elapsed time since last
   break/meds/meal (computed by `state` from journal rows), what's playing,
   what `journal patterns` says worked before.
3. Acts: `nudge`, `cast`, `wake --at` for follow-ups, or deliberately
   does nothing.

### Toolbelt contracts

Standalone CLIs; JSON to stdout on success, JSON error envelope
(`{"error": <code>, "detail": ...}`) + nonzero exit on failure; a top-level
wrapper converts any Python crash into that envelope. **Tools write their
own audit rows** (see journal) — the record does not depend on model
compliance.

- **`cast`** — `cast play <mood|url> [--device D]`, `cast stop`,
  `cast volume <0-1>`, `cast status`. Mood resolution: `config.yaml`
  `moods.<name>.jellyfin_playlist` (playlist ID, played via direct-stream
  URLs on the Default Media Receiver) → `moods.<name>.streams` list.
  Spotify is out of scope (deferred). `cast` records what it started
  (content URL, device, position polling) in `data/now_playing.json` —
  this is what makes resume possible. All devices offline →
  `{"error":"no_devices"}`; session policy is log-and-skip.
- **`nudge`** — `nudge "<text>" [--device D] [--urgency low|med|high]`.
  Piper TTS → MP3 in `tts-cache/` (pruned >24 h) → adhdo-httpd URL →
  Default Media Receiver. **Resume contract:** only content that `cast`
  itself started (per `now_playing.json`) is resumed, at last polled
  position for Jellyfin items, from-live for streams. Third-party casts
  (Spotify app, external senders) are *not* resumed — the interruption is
  journaled instead. Hard limits from config, enforced in-tool: max
  nudges/hour (default 4), quiet hours (default 22:00–07:00);
  `--urgency high` (only for config-enumerated events: medication, safety,
  user-requested) bypasses quiet hours, never the hourly cap. Rate-limit
  rejection = distinct error code; session must not retry this cycle.
- **`state`** — one JSON doc, fixed schema:
  `{ts, day_part, devices:[{name, online, now_playing}],
  last:{med, meal, break, nudge}, scheduled:[...],
  disk:{pct, warn}}`. Elapsed times computed from journal
  event rows; device scan cached 60 s. `disk.warn` trips at
  `disk_warn_pct` (default 94); CLAUDE.md policy: warn Adrian once/day,
  and prefer stream URLs over Jellyfin above 97%.
- **`journal`** — SQLite (WAL, busy-timeout) at `data/journal.db`. Tables:
  - `events(id, ts, source, type, payload_json)` — **semantic** rows,
    `type ∈ {nudge, cast, med, meal, break, decision, outcome, feedback,
    wake, error}`; written by `journal log <type> <text>` (session) and by
    tools for their domain events.
  - `audit(id, ts, tool, argv, ok, detail)` — tool invocations, written
    automatically by every tool *except* `journal` itself (no
    double-writing; a failed journal write reports only via its error
    envelope).
  - `schedule(id, due_ts, tag, delivered)` — future wakes.
  - `rollups(day, metric, value_json)` — nightly SQL aggregation.
  `journal recent [n]`; `journal patterns` returns fixed-schema JSON:
  `{window_days, nudge_response_rate_by_hour, nudge_response_rate_by_type,
  mood_by_daypart, event_streaks}` — plain SQL over events+rollups, no
  model calls. Retention: raw rows 90 days, rollups kept. Nightly backup
  copy to a second directory.

## Media

Jellyfin in Docker, bound to the Pi's static LAN IP (Chromecasts cannot
reach localhost). **Music-only configuration:** transcoding disabled
(audio direct-plays on cast devices), chapter/thumbnail extraction off,
metadata cache capped, transcode dir on a **512 MB tmpfs** as a safety net —
if anything ever does transcode and fills it, playback errors and `cast`
falls back to stream URLs. If Jellyfin still proves too heavy for the
92%-full disk, mood→stream-URLs is the standing fallback and Jellyfin moves
to a storage-cleanup follow-up.

## config.yaml (sketch — load-bearing fields)

```yaml
lan_ip: 192.168.x.x          # static; used by httpd + cast URLs
httpd_port: 8765
devices:                      # friendly-name → cast device
  office: "Nest Hub Max"
  kitchen: "Nest Mini"
default_device: office
moods:
  focus:  {jellyfin_playlist: "<id>", streams: ["https://..."]}
  calm:   {jellyfin_playlist: "<id>", streams: ["https://..."]}
jellyfin: {url: "http://<lan_ip>:8096", api_key: "..."}
nudge:
  max_per_hour: 4
  quiet_hours: ["22:00", "07:00"]
  high_urgency_events: [medication, safety, user_requested]
disk_warn_pct: 94
crisis:
  contacts: ["Lifeline Australia 13 11 14"]
telegram: {chat_id_allowlist: []}      # P3
```

## Interfaces (phased)

- **P1 — Foundation:** static IP, tmux, systemd units, toolbelt + wake
  machinery, Jellyfin, heartbeat loop, Piper verification. Interact via
  tmux/SSH.
- **P2 — Situational awareness:** connector login on the Pi; calendar/Gmail
  in the wake-up routine; proactive nudges (meds, breaks, bedtime,
  hyperfocus interruption); personalization = session consults
  `journal patterns` before choosing intervention type/timing and logs
  `outcome`/`feedback` rows after.
- **P3 — Remote interfaces:** Telegram bot bridging messages into the
  session via the same `wake` escaping contract. Security: chat-ID
  allowlist, inbound messages journaled, bridged as quoted user text only,
  per-minute rate limit. Thin read-only dashboard (state + journal) on the
  LAN (separate service from adhdo-httpd).
- **P4 — Voice via Nest:** investigation phase; Hailo NPU (local
  whisper/TTS) considered then.

## Safety

- **Crisis handling is layered:** (1) the Telegram bridge (P3) runs a
  deterministic regex screen before text reaches the model and prepends an
  **advisory** machine flag when matched — advisory because the original
  patterns (`crisis`, `help me`, `give up`) false-positive heavily on
  normal ADHD talk ("help me focus"); patterns get tightened when ported.
  (2) CLAUDE.md contains the fixed response — contacts from
  `config.yaml crisis.contacts` (Lifeline Australia 13 11 14), never
  improvised. In P1–P2 the only input is Adrian at a terminal.
- **Nudge rate limits and quiet hours live in the `nudge` tool.** Urgency
  overrides are config-enumerated, not model-invented.
- Privacy: journal and state stay local. Calendar/Gmail content read via
  connectors does transit Anthropic's API as session context — accepted
  trade-off. Connectors are read-only; no autonomous email sending.

## Error handling

- Uniform JSON error envelope from every tool, including on crashes.
- Claude process death → watchdog respawns pane; tmux death → systemd.
- Missed fixed events → consolidated catch-up wake on boot.
- Connector failure → session journals it and proceeds on local state.
- Jellyfin down/full → `cast` falls back to stream URLs.

## Testing

- **Contract tests (pytest, no hardware):** tool output schemas, error
  envelope on induced crashes, rate-limit/quiet-hours/urgency logic,
  config parsing + defaults, journal schemas + `patterns` output shape,
  schedule dedup, catch-up consolidation, `wake` sanitization (control
  chars, tmux metacharacters).
- **Hardware E2E (scripted manual checklist):** `cast play focus` audible;
  `nudge "test"` speaks and music resumes; wake injection lands during and
  outside a busy turn; full heartbeat cycle acts on real state; recycle
  preserves continuity; watchdog revives a killed claude process.
- No test-suite theater beyond that until the core loop demonstrably works.

## Non-goals

- Reviving `minimal_main.py`, the V2 engine, frame builder, or trace memory.
- Browser-automation auth of any kind.
- Spotify integration; resuming third-party casts.
- New media acquisition (disk at 92%).
- Voice input and Hailo NPU usage (deferred to P4 investigation).
