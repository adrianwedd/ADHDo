# Working on ADHDo

The current product is `adhdo2/`: a resident Claude Code session on a Pi plus
Python tools. Start with `README.md`, `adhdo2/README.md` and the relevant source.
The resident companion's own instructions are `adhdo2/session/CLAUDE.md`;
this file is repository development guidance.

## Validation

From the repository root, install `./adhdo2` and `pytest`, then run:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  -c adhdo2/pyproject.toml --confcutdir=adhdo2/tests adhdo2/tests -q
```

Read `.github/workflows/adhdo2.yml` for the product CI command. Root
`python -m pytest` also selects ADHDo 2. The legacy application and its CI are
retired by the owner decision in `docs/maintenance/2026-10-31-retirement.md`. Report failures accurately;
do not turn an exception, skipped check or mocked interface into a live pass.
For bug fixes, reproduce the failing behaviour before changing it and test the
relevant boundary, not just a helper that mirrors the implementation.

## Boundaries

- Keep Telegram screening advisory; retain allowlisting and ordinary quotas.
- Preserve private config, credentials, journal, NOTES and media during deployment.
- Only resume content that a nudge actually interrupted on the target device.
- Reminder delivery is at least once. Do not promise exactly once across crashes.
- Source merge, Pi installation, running-service activation and audible acceptance
  are distinct outcomes. Verify and name what was actually completed.
- Do not infer benefit or intent from a lack of response. Outcome statistics
  describe recorded feedback, not a validated model of the person.

`src/`, `tests/`, root launchers and the archived root package describe the
unsupported older application. They are reference material, not current work
targets. Keep supported development and acceptance focused on `adhdo2/`. The previous
repository instructions are retained at `docs/archive/CLAUDE-legacy.md` as history;
they are not current operational guidance.
