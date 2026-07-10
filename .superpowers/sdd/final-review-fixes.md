# Final whole-branch review fixes (adhdo2-p1)

Five findings from the final review, all addressed in one commit.

1. **Critical — deployed `bin/*` tools can't import `adhdolib`.** Added a
   `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))`
   bootstrap to the top of every `adhdo2/bin/*` script (`journal`, `state`,
   `cast`, `nudge`, `wake`, `adhdo-dispatch`), before any `adhdolib` import.
   Also added `[tool.setuptools]\npackages = ["adhdolib"]` to
   `adhdo2/pyproject.toml` as belt-and-braces (deploy.sh unchanged).

2. **Critical — `adhdo-catchup.sh` loader crash.** `spec_from_file_location`
   on an extensionless file with no explicit loader leaves `spec.loader`
   `None`, so `exec_module` crashes. Added `adhdo2/adhdolib/binload.py`
   exposing `load_bin_module(name)`, which builds a `SourceFileLoader`
   explicitly. Wired it into `scripts/adhdo-catchup.sh`'s inline python,
   `bin/adhdo-dispatch`'s `_wake()`, and `bin/state`'s `scan_devices()` — one
   helper, no divergence. Added `adhdo2/tests/test_binload.py` asserting
   `load_bin_module("wake")` returns a module with an `inject` attribute.

3. **Important — dispatch pending/processing race.** `bin/adhdo-dispatch`
   now takes `wake.lock` (the same lock `wake.inject()` uses) only around the
   pending.txt -> pending.processing merge/rename, then releases it before
   the inject loop (inject() re-acquires the lock itself; holding it there
   would deadlock on a "queued" result). The trailing `processing.unlink()`
   is left unlocked since only dispatch ever touches `pending.processing`.
   Comment added explaining the lock scope.

4. **Important — committed `.pyc` files.** Ran
   `git rm -r --cached adhdo2/tests/__pycache__` and appended
   `adhdo2/tests/__pycache__/` to the root `.gitignore`.

5. **One-liner — stale busy marker.** `bin/wake`: `busy.unlink()` ->
   `busy.unlink(missing_ok=True)`.

## Test output

```
cd adhdo2 && ../.venv/bin/python -m pytest tests/ -v
...
45 passed in 1.49s
```

All 44 previously-existing tests plus the new `test_binload.py` pass.
