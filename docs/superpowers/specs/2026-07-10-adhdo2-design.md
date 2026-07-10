# ADHDo 2.0 Design — Resident Claude Cognitive Companion

**Date:** 2026-07-10 (rev 2, after QA review by hermes/codex/agy)
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
natively provides reasoning, tool use, memory, and connector access (Gmail,
Google Calendar). The Python codebase shrinks to a small toolbelt of CLIs
the session invokes via Bash.

The original ADHDo repo stays on the Mac as **reference only** — mood
playlists, nudge phrasing, crisis regex patterns (`llm_client.py`,
`security_middleware.py`), quiet-hours defaults (`user_profile.py`,
`config.py`), and pychromecast know-how get cherry-picked, not imported.

## Verified Environment (2026-07-10 inventory)

- Claude Code 2.1.74, Node, Python 3, Docker installed on pi5-hailo.
- Docker stack running: sonarr, radarr, qbittorrent (via gluetun), prowlarr,
  frigate, dashy. Ollama on :11434. Mosquitto MQTT on :1883.
- **Chromecast discovery works** via avahi: Nest Hub Max, Nest Mini,
  Google Home Mini, Chromecast Audio, Shield TV all visible.
- Missing: tmux, Jellyfin, pychromecast, the ADHDo code itself.
- Disk: 92% full (~160 GB free) — see Media §.
- **Prerequisite (P1 setup):** give the Pi a DHCP reservation / static IP —
  Jellyfin and the TTS server are addressed by LAN IP from cast devices.

## Architecture

```
┌──────────────────────── pi5-hailo ────────────────────────┐
│  systemd user units (linger enabled):                     │
│    adhdo-session.service → tmux session "adhdo"           │
│       └─ Claude Code (resident session)                   │
│    adhdo-httpd.service   → static file server (TTS cache, │
│                            LAN-IP bound, fixed port)      │
│  cron (user crontab):                                     │
│    heartbeat every 25 min + fixed events (meds, bedtime)  │
│    nightly session recycle (03:30)                        │
│                                                           │
│  ~/adhdo2/bin  (toolbelt CLIs, self-logging)              │
│    cast | nudge | state | journal                         │
│  ~/adhdo2/config.yaml   hard limits, quiet hours, devices │
│  ~/adhdo2/data/journal.db  SQLite (WAL mode)              │
│  ~/adhdo2/NOTES.md      session working memory            │
│                                                           │
│  Docker: jellyfin (LAN-IP bound; cache/transcode capped)  │
└───────────────────────────────────────────────────────────┘
```

### Heartbeat & wake-up mechanism (defined, not hand-waved)

A cron-driven `wake` script injects a prompt into the tmux session via
`tmux send-keys`. Rules:

- **Serialization:** `wake` takes a lock file (`flock`). If the session is
  mid-turn (detected via a busy-marker file the session's hooks maintain, or
  lock still held), the wake-up is queued to `~/adhdo2/data/pending.txt`
  and delivered on the next attempt. Only one injection in flight, ever.
- **Fixed events** (medication, bedtime) are separate cron entries calling
  `wake --event meds` etc. — they carry an event tag so the session knows
  why it woke.
- **Missed events:** cron does not fire while the Pi is off. On boot, a
  `@reboot` catch-up script compares the last journal heartbeat against the
  fixed-event schedule and delivers at most **one** consolidated "you missed
  X and Y" wake-up — no nudge storm.
- **Context lifetime:** the session is recycled nightly (03:30 cron:
  graceful prompt to write a handoff into `NOTES.md`, then restart the tmux
  pane). On start, the session reads CLAUDE.md, `NOTES.md`, and
  `journal recent` — that is the continuity story; in-flight reasoning at
  crash time is accepted as lost.

### The cognitive loop

On each wake-up the session:
1. Runs `state`; consults calendar/Gmail connectors when relevant.
2. Reasons about the situation — time of day, upcoming events, elapsed time
   since last break/meds/meal (computed by `state` from journal event rows),
   what's playing, what the journal says worked before.
3. Acts: `nudge`, `cast`, schedules a follow-up (`wake --at`), or
   deliberately does nothing.

Tools self-log (below), so the record does not depend on model compliance.

### Toolbelt contracts

Standalone CLIs; JSON to stdout on success, JSON error object + nonzero exit
on failure. A top-level wrapper catches Python exceptions and emits
`{"error": ..., "trace_tail": ...}` so the session never sees a raw
traceback. **Every tool appends its own invocation + outcome to the journal**
— logging is not delegated to the model.

- **`cast`** — `cast play <mood|url> [--device D]`, `cast stop`,
  `cast volume <0-1>`, `cast status`. Mood resolution order: Jellyfin
  playlist (API key in config) → curated stream URLs in `config.yaml`.
  *(Spotify is explicitly out of scope for P1–P3; it requires OAuth +
  Spotify Connect design and is deferred to a later investigation.)*
  All-devices-offline → error JSON `{"error":"no_devices"}`; the session's
  policy (in CLAUDE.md) is log-and-skip, retry next heartbeat.
- **`nudge`** — `nudge "<text>" [--device D] [--urgency low|med|high]`.
  Pipeline: Piper TTS (aarch64 binary) → MP3 in `~/adhdo2/tts-cache/`
  (pruned >24 h) → served by adhdo-httpd → cast via pychromecast media
  controller. Saves the device's playback state first and **resumes
  interrupted music after the nudge** when resumable (Jellyfin/stream URLs;
  best-effort otherwise).
  **Hard limits from `config.yaml`, enforced in the tool:** default max
  4 nudges/hour, quiet hours 22:00–07:00. `--urgency high` (reserved for
  medication/safety/user-requested events, listed in config) bypasses quiet
  hours but never the hourly cap. Rate-limit rejections return a distinct
  error code; CLAUDE.md instructs the session not to retry them this cycle.
- **`state`** — no args; one JSON doc with a fixed schema:
  `{ts, day_part, devices:[{name, online, now_playing}], last:{med, meal,
  break, nudge}, pending_events, connector_status}`. Elapsed-time fields
  are computed from journal event rows. Device scan is cached (60 s TTL) to
  keep it cheap. Connector fields report `"stale"`/`"unavailable"` rather
  than failing the whole snapshot (degraded mode is normal on Starlink).
- **`journal`** — SQLite (WAL) at `~/adhdo2/data/journal.db`.
  Schema: `events(id, ts, source, type, payload_json)` where `source` is
  the tool or `session`, `type ∈ {nudge, cast, med, meal, break, decision,
  outcome, feedback, wake, error}`. Commands: `journal log <type> <text>`,
  `journal recent [n]`, `journal patterns` = **plain SQL rollups** (nudge
  response rate by hour/type, music moods by day-part, streaks) — no
  embeddings, no model calls. Retention: raw rows pruned after 90 days,
  daily rollup rows kept. Backup: nightly copy to a second directory.
  WAL + short busy-timeout handles the few concurrent writers.

## Media

Jellyfin in Docker, bound to the Pi's static LAN IP (Chromecasts cannot
reach localhost — the original system's key lesson). Library pointed at
existing media dirs. **Disk mitigation:** Jellyfin cache and transcode dirs
capped and mounted on tmpfs; chapter-image/thumbnail extraction disabled;
disk usage checked in `state`. If Jellyfin proves too heavy for the 92%-full
disk, the mood→stream-URL path is the fallback and Jellyfin moves to a
storage-cleanup follow-up.

## Interfaces (phased)

- **P1 — Foundation:** static IP, tmux, systemd units, toolbelt, Jellyfin,
  heartbeat loop. Interact via tmux/SSH.
- **P2 — Situational awareness:** calendar/Gmail connectors in the wake-up
  routine; proactive nudges (meds, breaks, bedtime, hyperfocus
  interruption); personalization = CLAUDE.md instructs the session to
  consult `journal patterns` before choosing intervention type/timing, and
  to log `outcome`/`feedback` rows afterward. Connector auth is set up
  interactively once; if a connector needs re-auth, `state` surfaces it and
  the session nudges *the user* to re-auth rather than failing silently.
- **P3 — Remote interfaces:** Telegram bot bridging messages into the
  session. **Security:** bot accepts messages only from Adrian's chat ID
  (allowlist in config), all inbound messages logged to journal, bridged as
  quoted user text (never executed as commands), simple per-minute rate
  limit. Thin read-only dashboard (state + journal) on the LAN.
- **P4 — Voice via Nest:** investigation phase; not designed here. (The
  Hailo NPU is likewise unused until P4 — candidate for local
  whisper/TTS acceleration then.)

## Safety

- **Crisis handling is layered:** (1) the Telegram bridge and any future
  input path run a deterministic regex screen (ported from the original
  `security_middleware.py` patterns) *before* text reaches the model, and
  prepend a machine flag when matched; (2) CLAUDE.md contains the fixed
  response — Lifeline Australia 13 11 14 and local crisis contacts
  (locale-configurable in config.yaml), never improvised. In P1–P2 the
  only input is Adrian at a terminal; the regex layer ships with the
  Telegram bridge in P3.
- **Nudge rate limits and quiet hours live in the `nudge` tool.** Urgency
  overrides are config-enumerated, not model-invented.
- Privacy: journal and state stay local. Calendar/Gmail content read via
  connectors does transit Anthropic's API as session context — accepted
  trade-off, noted explicitly. Connectors are read-only; no autonomous
  email sending.

## Error handling

- Uniform JSON error envelope from every tool (see toolbelt contracts).
- Session death → systemd restarts tmux + session; continuity from
  CLAUDE.md + NOTES.md + journal.
- Missed fixed events → consolidated catch-up wake on boot (see heartbeat §).
- Connector/network failure → degraded `state`, loop continues on local data.

## Testing

- **Contract tests (pytest, cheap, no hardware):** JSON schema of each
  tool's output, rate-limit and quiet-hours enforcement, config parsing,
  error envelope, journal schema/rollups, catch-up consolidation logic.
- **Hardware E2E (manual, scripted checklist):** `cast play focus` →
  audible music; `nudge "test"` → Nest speaks and music resumes; full
  heartbeat cycle observed acting on real state; session recycle preserves
  continuity.
- No test-suite theater beyond that until the core loop demonstrably works.

## Non-goals

- Reviving `minimal_main.py`, the V2 engine, frame builder, or trace memory.
- Browser-automation auth of any kind.
- Spotify integration (deferred; stream URLs are the fallback).
- New media acquisition (disk at 92%).
- Voice input and Hailo NPU usage (deferred to P4 investigation).
