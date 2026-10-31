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

Read `.github/workflows/adhdo2.yml` for the product CI command. Root legacy
CI is separate and has known failures in #119. Report failures accurately;
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

`src/`, root launchers and the root package describe the older application.
Consult `docs/maintenance/2026-10-31.md` before reviving those paths. The previous
repository instructions are retained at `docs/archive/CLAUDE-legacy.md` as history;
they are not current operational guidance.
