# ADHDo 2

A resident Claude Code session in tmux uses a small Python toolbelt to inspect
local state, keep a journal, schedule follow-ups and play music or spoken nudges.
The deployment target is `pi@pi5-hailo`, under `~/adhdo2`.

## Source setup and tests

Python 3.11 or later is required. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ./adhdo2 pytest
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  -c adhdo2/pyproject.toml --confcutdir=adhdo2/tests adhdo2/tests -q
```

Tests use temporary data and simulated external services. They do not send live
Telegram messages, run the resident agent or establish audible Cast behaviour.
The older root package is retired; its metadata is archived. Root
`python -m pytest` selects this same supported suite.

## Configuration

Copy `config.example.yaml` to `config.yaml` in the installation directory and
set `ADHDO_HOME` to that directory when running tools elsewhere. The default is
`~/adhdo2`. Private configuration and journal data do not belong in Git.

- Set `devices` (logical alias to exact Cast friendly name) and `default_device`.
- Set `lan_ip` to an address the speakers can reach. The default `127.0.0.1`
  works locally but cannot serve audio to another device.
- Configure Jellyfin URL, API key and playlist IDs, or use the configured stream
  fallback. Jellyfin moods choose a single track, not a continuously advancing playlist.
- Configure Telegram's bot token and numeric chat allowlist before enabling it.
  An empty allowlist accepts nobody. `TELEGRAM_BOT_TOKEN` overrides the config token.
- Nudge quiet hours and hourly quotas are enforced by the tool. Only configured
  high-urgency events can bypass quiet hours; they still consume the hourly quota.

Runtime dependencies include `tmux` and Claude Code for the resident session;
`piper` or `espeak-ng`, plus `ffmpeg`, for spoken nudges; and LAN/mDNS access for Cast.
The deployment script installs Python dependencies and `piper-tts`, but does not
provision the OS packages, Claude login, speaker network or Jellyfin library.

## Tools

Run tools with `venv/bin/python bin/<tool>` from the installation directory.
Commands return JSON; errors return nonzero status with an error envelope.

| Tool | Purpose |
| --- | --- |
| `state` | Device status, recent event ages, reminders and disk usage |
| `cast play <mood\|url> [--device D]` | Play recorded content on a speaker |
| `cast stop [--device D]`, `cast status`, `cast volume 0.4` | Playback controls |
| `nudge "text" [--device D] [--urgency low\|med\|high] [--event TAG]` | Speak within configured limits |
| `wake "prompt"`, `wake --event TAG` | Deliver or queue a resident-session wake |
| `wake --at HH:MM --tag TAG` | Schedule a follow-up; clock times mean the next occurrence |
| `journal log med "morning dose"` | Record an observation |
| `journal outcome nudge worked "took a break"` | Record structured feedback |
| `journal recent 20`, `journal patterns`, `journal rollup` | Inspect or aggregate the journal |
| `adhdo-dispatch`, `adhdo-catchup` | Consume pending or overdue reminders |
| `adhdo-telegram run`, `adhdo-dashboard` | Telegram bridge and read-only LAN dashboard |

Nudges restore only recorded content actively playing on the target device
before interruption, after the nudge finishes. Buffered Jellyfin playback seeks
to the polled position; live streams restart from live. Stale records, another
device, a timeout, unknown status or another sender taking over do not trigger
restoration. Actual device behaviour still needs the audible checks.

`journal patterns` reports recorded outcomes. The legacy fields named
`nudge_response_rate_by_hour` and `nudge_response_rate_by_type` are **counts of
nudges**, not measured response rates; `event_streaks` counts distinct recorded
days, not consecutive-day streaks. A lack of response alone is not evidence that
an intervention failed or was unwelcome.

## Deployment and live acceptance

From a machine with SSH access to the Pi, run `adhdo2/scripts/deploy.sh` from the
checkout. It copies source and unit definitions, installs Python dependencies and
reloads systemd definitions. It preserves runtime/private paths and an existing
Jellyfin Compose image pin. It does not restart running services or install cron.

The tmux service, watchdog and nightly recycle explicitly pass
`--settings ~/adhdo2/session/settings.json` to Claude Code (systemd uses `%h`).
That file contains the busy-marker hooks; a bare `session/settings.json` is not
an automatically discovered project settings path. See the upstream
[settings](https://code.claude.com/docs/en/settings) and
[CLI reference](https://code.claude.com/docs/en/cli-reference).

Complete [E2E_CHECKLIST.md](E2E_CHECKLIST.md) on the host before treating the
installation as ready. Restart an already-running Telegram bridge to load new
Python code. Launch changes take effect when the resident process restarts;
finish its current work and preserve the handoff first. `scripts/install-cron.sh`
installs scheduled household activity and enables the heartbeat timer, so run it
only once the target setup is ready.

The dashboard exposes journal content to its configured LAN bind address. Keep it
on a trusted network. An implementation being read-only does not make the journal
public information.
