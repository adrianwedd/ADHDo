# ADHDo 2.0 Design — Resident Claude Cognitive Companion

**Date:** 2026-07-10
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
natively provides reasoning, tool use, scheduling (heartbeats/cron), memory,
and connector access (Gmail, Google Calendar). The Python codebase shrinks to
a small toolbelt of CLIs the session invokes via Bash.

The original ADHDo repo stays on the Mac as **reference only** — mood
playlists, nudge phrasing, crisis patterns, and pychromecast know-how get
cherry-picked, not imported.

## Verified Environment (2026-07-10 inventory)

- Claude Code 2.1.74, Node, Python 3, Docker installed on pi5-hailo.
- Docker stack running: sonarr, radarr, qbittorrent (via gluetun), prowlarr,
  frigate, dashy. Ollama on :11434. Mosquitto MQTT on :1883.
- **Chromecast discovery works** via avahi: Nest Hub Max, Nest Mini,
  Google Home Mini, Chromecast Audio, Shield TV all visible.
- Missing: tmux, Jellyfin, pychromecast, the ADHDo code itself.
- Disk: 92% full (~160 GB free) — Jellyfin indexes existing media only;
  no new library ingestion.

## Architecture

```
┌──────────────────────── pi5-hailo ────────────────────────┐
│  systemd user unit → tmux session "adhdo"                 │
│    └─ Claude Code (resident session)                      │
│         • CLAUDE.md: role, safety rules, tool docs        │
│         • Heartbeat wake-ups (~20–30 min) + cron events   │
│         • Connectors: Gmail, Google Calendar              │
│         • Bash → toolbelt CLIs                            │
│                                                           │
│  ~/adhdo2/bin  (toolbelt)                                 │
│    cast     play/stop/volume/status on cast devices       │
│    nudge    TTS broadcast to Nest device(s), urgency tiers│
│    state    JSON snapshot: time, devices, now-playing,    │
│             timers, recent nudge/interaction history      │
│    journal  append/query SQLite interaction & pattern log │
│                                                           │
│  Docker: jellyfin (bound to LAN IP so Chromecasts reach it)│
└───────────────────────────────────────────────────────────┘
```

### The cognitive loop

On each heartbeat or cron wake-up the session:
1. Runs `state` (and consults calendar/Gmail connectors when relevant).
2. Reasons about the full situation — time of day, upcoming events,
   how long since last break/meds/meal, what music is playing, what
   the journal says worked before.
3. Acts: `nudge`, `cast`, set a follow-up wake-up — or deliberately does
   nothing. Every decision and outcome is appended via `journal`.

Fixed-time events (medication, bedtime wind-down) are cron entries, not
left to heartbeat judgment.

### Toolbelt contracts

Each tool is a standalone CLI, independently testable, JSON output:

- **`cast`** — `cast play <mood|uri> [--device D]`, `cast stop`,
  `cast volume <0-1>`, `cast status`. Moods resolve to Jellyfin
  playlists first, then Spotify/stream-URL fallback. Uses pychromecast.
- **`nudge`** — `nudge "<text>" [--device D] [--urgency low|med|high]`.
  TTS via Google Cast (local TTS-to-MP3 served over HTTP, cast to device).
  **Rate limiting enforced in the tool**: max nudges/hour and quiet hours
  are hard config, not model judgment.
- **`state`** — no args; emits one JSON document. Cheap enough to run
  every wake-up.
- **`journal`** — `journal log <type> <text>`, `journal recent [n]`,
  `journal patterns`. SQLite at `~/adhdo2/data/journal.db`. Survives
  session restarts; the session reads it on start.

## Media

Jellyfin in Docker on the existing host, port bound to the Pi's LAN IP
(Chromecasts cannot reach localhost — the original system's key lesson).
Library pointed at existing `~/Music` / torrent media dirs. Spotify or
curated stream URLs as fallback when Jellyfin lacks a mood.

## Interfaces (phased)

- **P1 — Foundation:** tmux + resident session + `cast`/`nudge`/`state`/
  `journal` + Jellyfin + heartbeat loop. Interact via tmux/SSH.
- **P2 — Situational awareness:** calendar/Gmail connectors wired into the
  wake-up routine; proactive nudges (meds, breaks, bedtime, hyperfocus
  interruption); journal-informed personalization.
- **P3 — Remote interfaces:** Telegram bot that bridges messages into the
  resident session; thin read-only dashboard (state + journal) served
  from the Pi.
- **P4 — Voice via Nest:** investigation phase; not designed here.

## Safety

- **Crisis detection is deterministic:** hard rules in CLAUDE.md with a
  fixed response (crisis hotline numbers), never improvised by the model.
- **Nudge rate limits and quiet hours live in the `nudge` tool** — the
  model cannot exceed them.
- Privacy: journal and state stay local on the Pi; connectors are
  read-mostly (calendar/Gmail read; no autonomous email sending).

## Error handling

- Toolbelt CLIs exit nonzero with a JSON error the session can read and
  reason about (device offline, Jellyfin down → fall back to stream).
- If the resident session dies, systemd restarts tmux + session; journal
  and CLAUDE.md restore continuity.
- Heartbeat missed (Pi offline) → cron events still fire independently.

## Testing

- Each tool verified end-to-end on real hardware (`cast play focus` →
  audible music; `nudge "test" --urgency low` → Nest speaks).
- Loop verified by observing one full heartbeat cycle act on real state.
- No test-suite theater before the core loop demonstrably works
  (per the original project's hard-won lesson).

## Non-goals

- Reviving `minimal_main.py`, the V2 engine, frame builder, or trace
  memory modules.
- Browser-automation auth of any kind.
- New media acquisition (disk at 92%).
- Voice input design (deferred to P4 investigation).
