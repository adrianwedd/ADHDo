# ADHDo

An executive-function companion that can notice the time, remember follow-ups,
and offer a brief nudge through household speakers or Telegram.

The current implementation is **ADHDo 2**, under [`adhdo2/`](adhdo2/README.md):
a resident Claude Code session in tmux on a Raspberry Pi, with a small Python
toolbelt, a SQLite journal, Cast playback, scheduled wakes, an allowlisted
Telegram bridge and a read-only LAN dashboard. Python 3.11 or later is required.

This is a personal system under development. Automated tests demonstrate source
behaviour with simulated external interfaces; they do not establish household
readiness, therapeutic benefit or a guaranteed response time. Device setup,
Claude login, connectors and audible acceptance remain installation tasks.
Current acceptance work is tracked in [#113](https://github.com/adrianwedd/ADHDo/issues/113),
[#114](https://github.com/adrianwedd/ADHDo/issues/114) and
[#115](https://github.com/adrianwedd/ADHDo/issues/115).

## Start here

- [Setup, toolbelt and deployment](adhdo2/README.md)
- [Hardware and live-service acceptance checklist](adhdo2/E2E_CHECKLIST.md)
- [Design and intended behaviour](docs/superpowers/specs/2026-07-10-adhdo2-design.md)
- [Boot catch-up and reminder delivery](adhdo2/docs/catchup-vs-schedule.md)
- [Maintenance findings, 31 October 2026](docs/maintenance/2026-10-31.md)
- [Documentation index](docs/README.md)

To test from the repository root, without a Pi or live credentials:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ./adhdo2 pytest
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  -c adhdo2/pyproject.toml --confcutdir=adhdo2/tests adhdo2/tests -q
```

The Telegram screen flags a narrow set of phrases as advisory context. Matching
messages are forwarded, including over the ordinary rate limit. This is not a
clinical assessment or a guarantee that every expression of distress is detected.
Nudges enforce quiet hours and ordinary hourly limits in code.

## Earlier implementations

**ADHDo 2 is the sole supported application.** The earlier FastAPI/browser
server under `src/`, its `tests/`, Docker files and top-level launchers are
retired reference material. Their active workflows and root packaging metadata
are [archived](docs/archive/legacy-workflows/README.md); their failing tests have
not been declared passing.

Root `python -m pytest` now selects `adhdo2/tests`. Install the current package
with `pip install ./adhdo2`. See the [support decision and evidence](docs/maintenance/2026-10-31-retirement.md).

The [previous README](docs/archive/README-legacy.md) is preserved as historical
material. Its claims of immediate readiness, sub-three-second responses and
complete integrations are not current verification results.
