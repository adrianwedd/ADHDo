# Supported application decision — 31 October 2026

**Owner decision: ADHDo 2 only.** The older FastAPI/browser-automation stack is
retired from active support and CI. It is not being rehabilitated into a second
supported application.

## What changed

- The old CI/CD, accessibility and security-hardening workflow definitions were
  moved out of `.github/workflows` into `docs/archive/legacy-workflows`.
- The old issue groomer was archived because its feature detector inspects the
  retired `src/` implementation. It should not recommend issue dispositions for
  the current application based on obsolete code.
- The legacy root package manifest and pytest config were preserved as
  `docs/archive/legacy-pyproject.toml` and `docs/archive/legacy-pytest.ini`.
- Root `python -m pytest` now explicitly selects `adhdo2/tests`. The supported
  package remains `adhdo2/pyproject.toml`; install it using `pip install ./adhdo2`.
- The existing ADHDo 2 CI job now runs on every PR/main push and uses that root
  test command. It installs only the current application's dependencies.
- Legacy source, tests, Docker files and launchers remain in history and the
  checkout as reference. Their presence does not imply support or readiness.

## Evidence and limits

The current toolbelt is independent of `src/`: the match found in its source is
a comment identifying the historical origin of Telegram phrase patterns, not a
runtime import. Retiring the old application does not change the Pi toolbelt.

The supported suite passes **211 tests**, both through root discovery and the
existing isolated ADHDo 2 command. The archived legacy suite's failures are
retired obligations, not passing results. Historical red Actions runs are not
deleted or relabelled as successful.

The exploratory legacy repair is preserved in
[PR #127](https://github.com/adrianwedd/ADHDo/pull/127), branch
`repair/legacy-ci-119`, at `08532bbc9c0be916153f6070aec834c7838e54ed`.
It reached clean installation/source compilation and 13 focused boundary tests,
but still exposed incompatible test contracts and broader behaviour failures.
It is not merged into the supported product. #119 is superseded by this support
scope decision, not closed as a successful legacy rehabilitation.

Pi installation/activation remains separate. This retirement does not stop or
change any process on a host; no live host or audible acceptance is claimed.
