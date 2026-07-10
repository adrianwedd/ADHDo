# ADHDo 2.0 — P1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy the ADHDo 2.0 P1 foundation — a toolbelt of self-logging CLIs (`journal`, `state`, `cast`, `nudge`, `wake`), the wake/dispatch/watchdog machinery, and the resident Claude Code session config — onto pi5-hailo.

**Architecture:** Code lives in this repo under `adhdo2/`, developed and unit-tested on the Mac, deployed to `pi@pi5-hailo:~/adhdo2` via an rsync deploy script. A shared `adhdolib` package provides config loading, the JSON error envelope, and SQLite access; each CLI is a thin executable in `adhdo2/bin/`. Hardware-dependent behavior (pychromecast, tmux, TTS) is isolated behind small functions so contract tests run without hardware.

**Tech Stack:** Python 3.11+, pychromecast, PyYAML, pytest, SQLite (stdlib), Piper TTS (espeak-ng fallback), tmux, systemd user units, cron, Jellyfin (Docker).

**Spec:** `docs/superpowers/specs/2026-07-10-adhdo2-design.md` (rev 3). The spec's contracts are normative; this plan implements them.

## Global Constraints

- All tools: JSON to stdout on success; `{"error": "<code>", "detail": "..."}` + exit 1 on any failure, including uncaught crashes.
- Every tool except `journal` writes an `audit` row per invocation.
- `ADHDO_HOME` env var overrides the data root (default `~/adhdo2`); all paths derive from it — this is how tests isolate.
- Nudge hard limits are enforced in-tool: `max_per_hour` (default 4), quiet hours (default 22:00–07:00); `--urgency high` bypasses quiet hours only, and only for config-enumerated events.
- `wake` sanitization: strip control chars, collapse newlines, `tmux send-keys -l`, Enter sent separately.
- Python on the Pi is system `python3` + venv at `~/adhdo2/venv`.
- Target user/host for deployment: `pi@pi5-hailo` (passwordless SSH from the Mac).

## File Structure

```
adhdo2/
  pyproject.toml              # package metadata + pytest config
  adhdolib/
    __init__.py
    config.py                 # load_config() with defaults
    envelope.py               # cli_main() wrapper, ToolError
    db.py                     # connect(), schema, audit(), log_event()
    nudgelimits.py            # rate-limit + quiet-hours logic (pure)
    sanitize.py               # wake payload sanitization (pure)
    schedule.py               # schedule table ops + catch-up consolidation
  bin/
    journal  state  cast  nudge  wake  adhdo-dispatch   # executables
  scripts/
    adhdo-watchdog.sh  adhdo-recycle.sh  adhdo-catchup.sh
    install-cron.sh    deploy.sh
  systemd/
    adhdo-tmux.service  adhdo-httpd.service
  session/
    CLAUDE.md                 # resident session role/policies
    settings.json             # hooks: busy marker
  config.example.yaml
  docker/jellyfin-compose.yml
  E2E_CHECKLIST.md
tests/adhdo2/
  conftest.py  test_config.py  test_envelope.py  test_db.py
  test_journal.py  test_state.py  test_nudgelimits.py  test_nudge.py
  test_sanitize.py  test_wake.py  test_schedule.py  test_cast.py
```

---

### Task 1: Package scaffold, config loader

**Files:**
- Create: `adhdo2/pyproject.toml`, `adhdo2/adhdolib/__init__.py`, `adhdo2/adhdolib/config.py`, `adhdo2/config.example.yaml`
- Test: `tests/adhdo2/conftest.py`, `tests/adhdo2/test_config.py`

**Interfaces:**
- Produces: `adhdolib.config.load_config() -> dict` — merged defaults + `$ADHDO_HOME/config.yaml`; `adhdolib.config.home() -> Path` (respects `ADHDO_HOME`).

- [ ] **Step 1: Scaffold package**

`adhdo2/pyproject.toml`:
```toml
[project]
name = "adhdo2"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6", "pychromecast>=14"]

[tool.pytest.ini_options]
testpaths = ["../tests/adhdo2"]
```

`adhdo2/adhdolib/__init__.py`: empty file.

- [ ] **Step 2: Write failing tests**

`tests/adhdo2/conftest.py`:
```python
import os, pathlib, sys, pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "adhdo2"))

@pytest.fixture
def adhdo_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ADHDO_HOME", str(tmp_path))
    (tmp_path / "data").mkdir()
    return tmp_path
```

`tests/adhdo2/test_config.py`:
```python
from adhdolib.config import load_config, home

def test_defaults_without_file(adhdo_home):
    cfg = load_config()
    assert cfg["nudge"]["max_per_hour"] == 4
    assert cfg["nudge"]["quiet_hours"] == ["22:00", "07:00"]
    assert cfg["disk_warn_pct"] == 94

def test_file_overrides_merge(adhdo_home):
    (adhdo_home / "config.yaml").write_text("nudge:\n  max_per_hour: 2\n")
    cfg = load_config()
    assert cfg["nudge"]["max_per_hour"] == 2
    assert cfg["nudge"]["quiet_hours"] == ["22:00", "07:00"]  # default kept

def test_home_respects_env(adhdo_home):
    assert home() == adhdo_home
```

- [ ] **Step 3: Run tests, verify failure**

Run: `cd adhdo2 && python -m pytest ../tests/adhdo2/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`/`ImportError`.

- [ ] **Step 4: Implement**

`adhdo2/adhdolib/config.py`:
```python
import os, copy
from pathlib import Path
import yaml

DEFAULTS = {
    "lan_ip": "127.0.0.1",
    "httpd_port": 8765,
    "devices": {},
    "default_device": None,
    "moods": {},
    "jellyfin": {"url": None, "api_key": None},
    "nudge": {
        "max_per_hour": 4,
        "quiet_hours": ["22:00", "07:00"],
        "high_urgency_events": ["medication", "safety", "user_requested"],
    },
    "disk_warn_pct": 94,
    "crisis": {"contacts": ["Lifeline Australia 13 11 14"]},
    "telegram": {"chat_id_allowlist": []},
}

def home() -> Path:
    return Path(os.environ.get("ADHDO_HOME", str(Path.home() / "adhdo2")))

def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config() -> dict:
    path = home() / "config.yaml"
    if path.exists():
        return _merge(DEFAULTS, yaml.safe_load(path.read_text()) or {})
    return copy.deepcopy(DEFAULTS)
```

`adhdo2/config.example.yaml`: copy the sketch from the spec's "config.yaml" section verbatim.

- [ ] **Step 5: Run tests, verify pass**

Run: `cd adhdo2 && python -m pytest ../tests/adhdo2/test_config.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add adhdo2 tests/adhdo2
git commit -m "feat(adhdo2): package scaffold and config loader"
```

---

### Task 2: Error envelope + CLI wrapper

**Files:**
- Create: `adhdo2/adhdolib/envelope.py`
- Test: `tests/adhdo2/test_envelope.py`

**Interfaces:**
- Produces: `ToolError(code, detail)` exception; `cli_main(fn)` — runs `fn() -> dict`, prints JSON, exits 0; on `ToolError` prints `{"error": code, "detail": detail}` exits 1; on any other exception prints `{"error": "crash", "detail": "<Type>: <msg>", "trace_tail": "<last 3 frames>"}` exits 1.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_envelope.py`:
```python
import json, pytest
from adhdolib.envelope import ToolError, cli_main

def run(fn, capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(fn)
    return e.value.code, json.loads(capsys.readouterr().out)

def test_success(capsys):
    code, out = run(lambda: {"ok": True}, capsys)
    assert code == 0 and out == {"ok": True}

def test_tool_error(capsys):
    def f(): raise ToolError("no_devices", "none online")
    code, out = run(f, capsys)
    assert code == 1 and out == {"error": "no_devices", "detail": "none online"}

def test_crash_is_enveloped(capsys):
    def f(): raise ValueError("boom")
    code, out = run(f, capsys)
    assert code == 1 and out["error"] == "crash"
    assert "ValueError: boom" in out["detail"]
    assert "trace_tail" in out
```

- [ ] **Step 2: Run, verify FAIL** — `python -m pytest ../tests/adhdo2/test_envelope.py -v`

- [ ] **Step 3: Implement**

`adhdo2/adhdolib/envelope.py`:
```python
import json, sys, traceback

class ToolError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail)
        self.code, self.detail = code, detail

def cli_main(fn):
    try:
        out = fn()
        print(json.dumps(out, default=str))
        sys.exit(0)
    except ToolError as e:
        print(json.dumps({"error": e.code, "detail": e.detail}))
        sys.exit(1)
    except SystemExit:
        raise
    except BaseException as e:
        tail = "".join(traceback.format_tb(e.__traceback__)[-3:])
        print(json.dumps({"error": "crash",
                          "detail": f"{type(e).__name__}: {e}",
                          "trace_tail": tail}))
        sys.exit(1)
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): JSON error envelope for all CLIs"`

---

### Task 3: Database layer (events, audit, schedule, rollups)

**Files:**
- Create: `adhdo2/adhdolib/db.py`
- Test: `tests/adhdo2/test_db.py`

**Interfaces:**
- Produces: `connect() -> sqlite3.Connection` (WAL, busy_timeout 3000 ms, creates tables at `$ADHDO_HOME/data/journal.db`); `log_event(conn, source, type, payload: str)`; `audit(conn, tool, argv: list, ok: bool, detail: str)`; `EVENT_TYPES` frozenset = `{nudge, cast, med, meal, break, decision, outcome, feedback, wake, error}`.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_db.py`:
```python
from adhdolib import db

def test_schema_created(adhdo_home):
    conn = db.connect()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "audit", "schedule", "rollups"} <= names

def test_log_event_and_audit(adhdo_home):
    conn = db.connect()
    db.log_event(conn, "session", "decision", "played focus music")
    db.audit(conn, "cast", ["play", "focus"], True, "ok")
    assert conn.execute("SELECT type FROM events").fetchone()[0] == "decision"
    assert conn.execute("SELECT tool, ok FROM audit").fetchone() == ("cast", 1)

def test_invalid_event_type_rejected(adhdo_home):
    import pytest
    conn = db.connect()
    with pytest.raises(ValueError):
        db.log_event(conn, "session", "bogus", "x")
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/adhdolib/db.py`:
```python
import json, sqlite3, time
from .config import home

EVENT_TYPES = frozenset({"nudge", "cast", "med", "meal", "break",
                         "decision", "outcome", "feedback", "wake", "error"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, ts REAL NOT NULL,
  source TEXT NOT NULL, type TEXT NOT NULL, payload_json TEXT);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, ts REAL NOT NULL,
  tool TEXT NOT NULL, argv TEXT, ok INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS schedule(
  id INTEGER PRIMARY KEY, due_ts REAL NOT NULL,
  tag TEXT, delivered INTEGER DEFAULT 0,
  UNIQUE(due_ts, tag));
CREATE TABLE IF NOT EXISTS rollups(
  day TEXT NOT NULL, metric TEXT NOT NULL, value_json TEXT,
  PRIMARY KEY(day, metric));
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, ts);
"""

def connect() -> sqlite3.Connection:
    path = home() / "data" / "journal.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=3.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.executescript(SCHEMA)
    return conn

def log_event(conn, source: str, type: str, payload: str):
    if type not in EVENT_TYPES:
        raise ValueError(f"unknown event type: {type}")
    conn.execute("INSERT INTO events(ts, source, type, payload_json) VALUES(?,?,?,?)",
                 (time.time(), source, type, json.dumps(payload)))
    conn.commit()

def audit(conn, tool: str, argv: list, ok: bool, detail: str = ""):
    conn.execute("INSERT INTO audit(ts, tool, argv, ok, detail) VALUES(?,?,?,?,?)",
                 (time.time(), tool, json.dumps(argv), int(ok), detail))
    conn.commit()
```

- [ ] **Step 4: Run, verify PASS**  — all of `test_db.py`.

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): sqlite layer with events/audit/schedule/rollups"`

---

### Task 4: `journal` CLI (log, recent, patterns)

**Files:**
- Create: `adhdo2/bin/journal` (executable Python, shebang `#!/usr/bin/env python3`)
- Test: `tests/adhdo2/test_journal.py`

**Interfaces:**
- Consumes: `db.connect/log_event`, `envelope.cli_main`.
- Produces: CLI — `journal log <type> <text>` → `{"logged": type}`; `journal recent [n]` → `{"events": [{ts, source, type, payload}]}` (newest first, default n=20); `journal patterns` → `{"window_days": 30, "nudge_response_rate_by_hour": {..}, "nudge_response_rate_by_type": {..}, "mood_by_daypart": {..}, "event_streaks": {..}}`. Also importable: `adhdo2/bin/journal` keeps logic in functions `cmd_log/cmd_recent/cmd_patterns(conn, args)` so tests import it via `importlib`.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_journal.py`:
```python
import importlib.util, json, pathlib, subprocess, sys, os

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "journal"

def run_cli(adhdo_home, *args):
    env = dict(os.environ, ADHDO_HOME=str(adhdo_home),
               PYTHONPATH=str(BIN.parents[1]))
    p = subprocess.run([sys.executable, str(BIN), *args],
                       capture_output=True, text=True, env=env)
    return p.returncode, json.loads(p.stdout)

def test_log_and_recent(adhdo_home):
    code, out = run_cli(adhdo_home, "log", "med", "morning dose")
    assert code == 0 and out == {"logged": "med"}
    code, out = run_cli(adhdo_home, "recent", "5")
    assert code == 0
    assert out["events"][0]["type"] == "med"

def test_bad_type_is_enveloped(adhdo_home):
    code, out = run_cli(adhdo_home, "log", "bogus", "x")
    assert code == 1 and out["error"] in ("bad_type", "crash")

def test_patterns_shape(adhdo_home):
    run_cli(adhdo_home, "log", "nudge", json.dumps({"urgency": "low"}))
    code, out = run_cli(adhdo_home, "patterns")
    assert code == 0
    for key in ("window_days", "nudge_response_rate_by_hour",
                "nudge_response_rate_by_type", "mood_by_daypart",
                "event_streaks"):
        assert key in out
```

- [ ] **Step 2: Run, verify FAIL** (file not found / non-JSON output).

- [ ] **Step 3: Implement**

`adhdo2/bin/journal`:
```python
#!/usr/bin/env python3
import json, sys, time
from adhdolib import db
from adhdolib.envelope import ToolError, cli_main

def cmd_log(conn, args):
    if len(args) < 2:
        raise ToolError("usage", "journal log <type> <text>")
    type_, text = args[0], " ".join(args[1:])
    if type_ not in db.EVENT_TYPES:
        raise ToolError("bad_type", f"type must be one of {sorted(db.EVENT_TYPES)}")
    db.log_event(conn, "session", type_, text)
    return {"logged": type_}

def cmd_recent(conn, args):
    n = int(args[0]) if args else 20
    rows = conn.execute(
        "SELECT ts, source, type, payload_json FROM events "
        "ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
    return {"events": [
        {"ts": r[0], "source": r[1], "type": r[2],
         "payload": json.loads(r[3]) if r[3] else None} for r in rows]}

def cmd_patterns(conn, args):
    cutoff = time.time() - 30 * 86400
    by_hour, by_type, moods, streaks = {}, {}, {}, {}
    for (h, n) in conn.execute(
        "SELECT strftime('%H', ts, 'unixepoch', 'localtime'), COUNT(*) "
        "FROM events WHERE type='nudge' AND ts>? GROUP BY 1", (cutoff,)):
        by_hour[h] = n
    for (t, n) in conn.execute(
        "SELECT COALESCE(json_extract(payload_json,'$.urgency'),'unknown'), COUNT(*) "
        "FROM events WHERE type='nudge' AND ts>? GROUP BY 1", (cutoff,)):
        by_type[t] = n
    for (dp, n) in conn.execute(
        "SELECT COALESCE(json_extract(payload_json,'$.mood'),'unknown'), COUNT(*) "
        "FROM events WHERE type='cast' AND ts>? GROUP BY 1", (cutoff,)):
        moods[dp] = n
    for (t, n) in conn.execute(
        "SELECT type, COUNT(DISTINCT date(ts,'unixepoch','localtime')) "
        "FROM events WHERE type IN ('med','meal','break') AND ts>? GROUP BY 1",
        (cutoff,)):
        streaks[t] = n
    return {"window_days": 30, "nudge_response_rate_by_hour": by_hour,
            "nudge_response_rate_by_type": by_type,
            "mood_by_daypart": moods, "event_streaks": streaks}

def main():
    if len(sys.argv) < 2:
        raise ToolError("usage", "journal <log|recent|patterns> ...")
    conn = db.connect()
    cmd = {"log": cmd_log, "recent": cmd_recent, "patterns": cmd_patterns}.get(sys.argv[1])
    if not cmd:
        raise ToolError("usage", f"unknown subcommand {sys.argv[1]}")
    return cmd(conn, sys.argv[2:])

if __name__ == "__main__":
    cli_main(main)
```

`chmod +x adhdo2/bin/journal`

- [ ] **Step 4: Run, verify PASS** — `python -m pytest ../tests/adhdo2/test_journal.py -v`

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): journal CLI with log/recent/patterns"`

---

### Task 5: Nudge limits (pure logic)

**Files:**
- Create: `adhdo2/adhdolib/nudgelimits.py`
- Test: `tests/adhdo2/test_nudgelimits.py`

**Interfaces:**
- Produces: `check_allowed(now: datetime, urgency: str, event: str|None, nudges_last_hour: int, cfg: dict) -> tuple[bool, str]` — returns `(True, "ok")` or `(False, code)` with codes `rate_limited` / `quiet_hours` / `bad_override`.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_nudgelimits.py`:
```python
from datetime import datetime
from adhdolib.config import DEFAULTS
from adhdolib.nudgelimits import check_allowed

DAY = datetime(2026, 7, 10, 14, 0)      # 2pm
NIGHT = datetime(2026, 7, 10, 23, 30)   # 11:30pm
EARLY = datetime(2026, 7, 10, 6, 30)    # 6:30am (still quiet)

def test_normal_daytime_ok():
    assert check_allowed(DAY, "low", None, 0, DEFAULTS) == (True, "ok")

def test_hourly_cap():
    assert check_allowed(DAY, "low", None, 4, DEFAULTS) == (False, "rate_limited")

def test_quiet_hours_block_low():
    assert check_allowed(NIGHT, "low", None, 0, DEFAULTS) == (False, "quiet_hours")
    assert check_allowed(EARLY, "low", None, 0, DEFAULTS) == (False, "quiet_hours")

def test_high_urgency_bypasses_quiet_hours_only():
    assert check_allowed(NIGHT, "high", "medication", 0, DEFAULTS) == (True, "ok")
    assert check_allowed(NIGHT, "high", "medication", 4, DEFAULTS) == (False, "rate_limited")

def test_high_urgency_requires_enumerated_event():
    assert check_allowed(NIGHT, "high", "party", 0, DEFAULTS) == (False, "bad_override")
    assert check_allowed(NIGHT, "high", None, 0, DEFAULTS) == (False, "bad_override")
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/adhdolib/nudgelimits.py`:
```python
from datetime import datetime, time as dtime

def _in_quiet_hours(now: datetime, quiet: list[str]) -> bool:
    start = dtime(*map(int, quiet[0].split(":")))
    end = dtime(*map(int, quiet[1].split(":")))
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # wraps midnight

def check_allowed(now, urgency, event, nudges_last_hour, cfg):
    ncfg = cfg["nudge"]
    if nudges_last_hour >= ncfg["max_per_hour"]:
        return (False, "rate_limited")
    if _in_quiet_hours(now, ncfg["quiet_hours"]):
        if urgency != "high":
            return (False, "quiet_hours")
        if event not in ncfg["high_urgency_events"]:
            return (False, "bad_override")
    return (True, "ok")
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): nudge rate-limit and quiet-hours logic"`

---

### Task 6: `nudge` CLI (TTS pipeline + limits + resume hook)

**Files:**
- Create: `adhdo2/bin/nudge`
- Test: `tests/adhdo2/test_nudge.py`

**Interfaces:**
- Consumes: `nudgelimits.check_allowed`, `db`, `envelope`, `config`.
- Produces: CLI `nudge "<text>" [--device D] [--urgency low|med|high] [--event E]` → `{"nudged": true, "device": ..., "resumed": bool}`. Internals split for testability: `synthesize(text, cache_dir) -> Path` (Piper via subprocess, fallback `espeak-ng`, raises `ToolError("tts_failed")`), `play_url_on_device(url, device_name, cfg)` (pychromecast; monkeypatched in tests), `save_and_resume(device)` context manager reading/honoring `$ADHDO_HOME/data/now_playing.json`.

- [ ] **Step 1: Write failing tests** (mock hardware; test the orchestration + limits + audit)

`tests/adhdo2/test_nudge.py`:
```python
import importlib.util, json, pathlib, time
import pytest
from adhdolib import db
from adhdolib.envelope import ToolError

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "nudge"

def load_nudge():
    spec = importlib.util.spec_from_file_location("nudge_cli", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_rate_limited_returns_distinct_code(adhdo_home, monkeypatch):
    nudge = load_nudge()
    conn = db.connect()
    for _ in range(4):
        db.log_event(conn, "nudge", "nudge", json.dumps({"urgency": "low"}))
    with pytest.raises(ToolError) as e:
        nudge.run(["hello"], _test_conn=conn)
    assert e.value.code == "rate_limited"

def test_successful_nudge_audits_and_journals(adhdo_home, monkeypatch):
    nudge = load_nudge()
    monkeypatch.setattr(nudge, "synthesize", lambda text, d: d / "x.mp3")
    monkeypatch.setattr(nudge, "play_url_on_device", lambda url, dev, cfg: None)
    conn = db.connect()
    out = nudge.run(["step away", "--urgency", "med"], _test_conn=conn)
    assert out["nudged"] is True
    assert conn.execute("SELECT COUNT(*) FROM events WHERE type='nudge'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM audit WHERE tool='nudge'").fetchone()[0] == 1

def test_tts_failure_enveloped(adhdo_home, monkeypatch):
    nudge = load_nudge()
    def boom(text, d): raise ToolError("tts_failed", "no engine")
    monkeypatch.setattr(nudge, "synthesize", boom)
    conn = db.connect()
    with pytest.raises(ToolError) as e:
        nudge.run(["hi"], _test_conn=conn)
    assert e.value.code == "tts_failed"
    assert conn.execute("SELECT ok FROM audit WHERE tool='nudge'").fetchone()[0] == 0
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/bin/nudge`:
```python
#!/usr/bin/env python3
import argparse, hashlib, json, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from adhdolib import db
from adhdolib.config import load_config, home
from adhdolib.envelope import ToolError, cli_main
from adhdolib.nudgelimits import check_allowed

def synthesize(text: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / (hashlib.sha1(text.encode()).hexdigest()[:16] + ".mp3")
    wav = out.with_suffix(".wav")
    if out.exists():
        return out
    if shutil.which("piper"):
        subprocess.run(["piper", "--output_file", str(wav)],
                       input=text.encode(), check=True, timeout=60)
    elif shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", "-w", str(wav), text], check=True, timeout=60)
    else:
        raise ToolError("tts_failed", "neither piper nor espeak-ng found")
    if not shutil.which("ffmpeg"):
        raise ToolError("tts_failed", "ffmpeg not found for mp3 encode")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), str(out)],
                   check=True, timeout=60)
    wav.unlink(missing_ok=True)
    # prune cache >24h
    cutoff = time.time() - 86400
    for f in cache_dir.glob("*.mp3"):
        if f.stat().st_mtime < cutoff and f != out:
            f.unlink()
    return out

def play_url_on_device(url: str, device_name: str, cfg: dict):
    import pychromecast
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[device_name])
    if not casts:
        raise ToolError("no_devices", f"{device_name} not found")
    cc = casts[0]; cc.wait()
    cc.media_controller.play_media(url, "audio/mpeg")
    cc.media_controller.block_until_active(timeout=15)
    browser.stop_discovery()

def _resume_previous(cfg) -> bool:
    np = home() / "data" / "now_playing.json"
    if not np.exists():
        return False
    info = json.loads(np.read_text())
    if not info.get("url"):
        return False
    try:
        play_url_on_device(info["url"], info["device"], cfg)
        return True
    except ToolError:
        return False

def run(argv, _test_conn=None):
    ap = argparse.ArgumentParser(prog="nudge")
    ap.add_argument("text")
    ap.add_argument("--device")
    ap.add_argument("--urgency", choices=["low", "med", "high"], default="low")
    ap.add_argument("--event")
    args = ap.parse_args(argv)
    cfg = load_config()
    conn = _test_conn or db.connect()
    try:
        hour_ago = time.time() - 3600
        n = conn.execute("SELECT COUNT(*) FROM events WHERE type='nudge' AND ts>?",
                         (hour_ago,)).fetchone()[0]
        ok, code = check_allowed(datetime.now(), args.urgency, args.event, n, cfg)
        if not ok:
            raise ToolError(code, "nudge blocked; do not retry this cycle")
        device = args.device or cfg["default_device"]
        if not device:
            raise ToolError("no_device_configured", "set default_device in config")
        real_name = cfg["devices"].get(device, device)
        mp3 = synthesize(args.text, home() / "tts-cache")
        url = f"http://{cfg['lan_ip']}:{cfg['httpd_port']}/{mp3.name}"
        play_url_on_device(url, real_name, cfg)
        time.sleep(1)
        resumed = _resume_previous(cfg)
        db.log_event(conn, "nudge", "nudge", json.dumps(
            {"text": args.text, "urgency": args.urgency, "device": device}))
        db.audit(conn, "nudge", argv, True, "")
        return {"nudged": True, "device": device, "resumed": resumed}
    except ToolError as e:
        db.audit(conn, "nudge", argv, False, e.code)
        raise

if __name__ == "__main__":
    cli_main(lambda: run(sys.argv[1:]))
```

`chmod +x adhdo2/bin/nudge`

Note: `_resume_previous` waits only 1 s here; TTS playback-finish detection is refined during hardware E2E (poll `media_controller.status` until idle, max 30 s) — implement that then, on the Pi, where behavior is observable.

- [ ] **Step 4: Run, verify PASS** — `python -m pytest ../tests/adhdo2/test_nudge.py -v`

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): nudge CLI with TTS pipeline, limits, resume"`

---

### Task 7: `cast` CLI

**Files:**
- Create: `adhdo2/bin/cast`
- Test: `tests/adhdo2/test_cast.py`

**Interfaces:**
- Consumes: `db`, `config`, `envelope`.
- Produces: CLI `cast play <mood|url> [--device D]` → `{"playing": <url>, "device": ..., "source": "jellyfin"|"stream"|"url"}`; `cast stop`; `cast volume <0-1>`; `cast status` → `{"devices": [{name, online, now_playing}]}`. Writes `$ADHDO_HOME/data/now_playing.json` (`{url, device, mood, started_ts}`) on play, clears on stop. Internals: `resolve_mood(mood, cfg) -> tuple[str, str]` returns `(url, source)` — Jellyfin playlist → first item's direct-stream URL (`{jellyfin.url}/Audio/{item_id}/universal?api_key=...`), else random choice from `streams`, raises `ToolError("unknown_mood")`; `get_cast(device_name)` wraps pychromecast (patched in tests).

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_cast.py`:
```python
import importlib.util, json, pathlib
import pytest
from adhdolib.envelope import ToolError

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "cast"

def load_cast():
    spec = importlib.util.spec_from_file_location("cast_cli", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

CFG = {"moods": {"focus": {"jellyfin_playlist": None,
                           "streams": ["http://stream.example/focus"]}},
       "jellyfin": {"url": None, "api_key": None}}

def test_resolve_mood_stream_fallback():
    cast = load_cast()
    url, source = cast.resolve_mood("focus", CFG)
    assert url == "http://stream.example/focus" and source == "stream"

def test_resolve_unknown_mood():
    cast = load_cast()
    with pytest.raises(ToolError) as e:
        cast.resolve_mood("rave", CFG)
    assert e.value.code == "unknown_mood"

def test_raw_url_passthrough():
    cast = load_cast()
    url, source = cast.resolve_mood("http://x/y.mp3", CFG)
    assert source == "url"

def test_play_writes_now_playing(adhdo_home, monkeypatch):
    cast = load_cast()
    monkeypatch.setattr(cast, "play_on_device", lambda url, dev: None)
    from adhdolib import db
    out = cast.run(["play", "http://x/y.mp3", "--device", "office"],
                   _test_conn=db.connect(),
                   _test_cfg={**CFG, "devices": {"office": "Nest Hub Max"},
                              "default_device": "office"})
    np = json.loads((adhdo_home / "data" / "now_playing.json").read_text())
    assert np["url"] == "http://x/y.mp3" and np["device"] == "Nest Hub Max"
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/bin/cast`:
```python
#!/usr/bin/env python3
import argparse, json, random, sys, time
from pathlib import Path
from adhdolib import db
from adhdolib.config import load_config, home
from adhdolib.envelope import ToolError, cli_main

def resolve_mood(mood_or_url: str, cfg: dict):
    if mood_or_url.startswith(("http://", "https://")):
        return mood_or_url, "url"
    mood = cfg["moods"].get(mood_or_url)
    if not mood:
        raise ToolError("unknown_mood", f"no mood '{mood_or_url}' in config")
    jf = cfg.get("jellyfin", {})
    if mood.get("jellyfin_playlist") and jf.get("url") and jf.get("api_key"):
        try:
            import urllib.request
            u = (f"{jf['url']}/Playlists/{mood['jellyfin_playlist']}/Items"
                 f"?api_key={jf['api_key']}")
            items = json.loads(urllib.request.urlopen(u, timeout=5).read())["Items"]
            if items:
                item = random.choice(items)
                return (f"{jf['url']}/Audio/{item['Id']}/universal"
                        f"?api_key={jf['api_key']}&Container=mp3", "jellyfin")
        except Exception:
            pass  # fall through to streams
    streams = mood.get("streams") or []
    if streams:
        return random.choice(streams), "stream"
    raise ToolError("unknown_mood", f"mood '{mood_or_url}' has no playable source")

def play_on_device(url: str, device_name: str):
    import pychromecast
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[device_name])
    if not casts:
        raise ToolError("no_devices", f"{device_name} not found")
    cc = casts[0]; cc.wait()
    cc.media_controller.play_media(url, "audio/mpeg")
    cc.media_controller.block_until_active(timeout=15)
    browser.stop_discovery()

def device_status(cfg):
    import pychromecast
    names = list(cfg["devices"].values())
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=names)
    online = {}
    for cc in casts:
        cc.wait(timeout=5)
        s = cc.media_controller.status
        online[cc.name] = s.title if s and s.player_is_playing else None
    browser.stop_discovery()
    return [{"name": n, "online": n in online, "now_playing": online.get(n)}
            for n in names]

def run(argv, _test_conn=None, _test_cfg=None):
    ap = argparse.ArgumentParser(prog="cast")
    ap.add_argument("cmd", choices=["play", "stop", "volume", "status"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--device")
    args = ap.parse_args(argv)
    cfg = _test_cfg or load_config()
    conn = _test_conn or db.connect()
    np_path = home() / "data" / "now_playing.json"
    try:
        if args.cmd == "play":
            if not args.arg:
                raise ToolError("usage", "cast play <mood|url>")
            url, source = resolve_mood(args.arg, cfg)
            device = args.device or cfg["default_device"]
            real = cfg["devices"].get(device, device)
            play_on_device(url, real)
            np_path.parent.mkdir(parents=True, exist_ok=True)
            np_path.write_text(json.dumps(
                {"url": url, "device": real, "mood": args.arg,
                 "started_ts": time.time()}))
            db.log_event(conn, "cast", "cast",
                         json.dumps({"mood": args.arg, "device": device}))
            out = {"playing": url, "device": device, "source": source}
        elif args.cmd == "stop":
            device = args.device or cfg["default_device"]
            real = cfg["devices"].get(device, device)
            import pychromecast
            casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[real])
            if casts:
                casts[0].wait(); casts[0].media_controller.stop()
                browser.stop_discovery()
            np_path.unlink(missing_ok=True)
            out = {"stopped": True}
        elif args.cmd == "volume":
            level = float(args.arg)
            if not 0 <= level <= 1:
                raise ToolError("usage", "volume must be 0..1")
            device = args.device or cfg["default_device"]
            real = cfg["devices"].get(device, device)
            import pychromecast
            casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[real])
            if not casts:
                raise ToolError("no_devices", f"{real} not found")
            casts[0].wait(); casts[0].set_volume(level)
            browser.stop_discovery()
            out = {"volume": level}
        else:
            out = {"devices": device_status(cfg)}
        db.audit(conn, "cast", argv, True, "")
        return out
    except ToolError as e:
        db.audit(conn, "cast", argv, False, e.code)
        raise

if __name__ == "__main__":
    cli_main(lambda: run(sys.argv[1:]))
```

`chmod +x adhdo2/bin/cast`

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): cast CLI with mood resolution and now_playing tracking"`

---

### Task 8: `state` CLI

**Files:**
- Create: `adhdo2/bin/state`
- Test: `tests/adhdo2/test_state.py`

**Interfaces:**
- Consumes: `db`, `config`; `cast.device_status` semantics (device scan is invoked via a patched function and cached).
- Produces: CLI `state` → `{ts, day_part, devices, last: {med, meal, break, nudge}, scheduled, disk: {pct, warn}}`. `last.*` values are seconds-since (`null` if never). Device scan cached in `$ADHDO_HOME/data/devices_cache.json` for 60 s. `day_part ∈ {morning, afternoon, evening, night}`.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_state.py`:
```python
import importlib.util, json, pathlib, time
from adhdolib import db

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "state"

def load_state():
    spec = importlib.util.spec_from_file_location("state_cli", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_schema_and_last_events(adhdo_home, monkeypatch):
    st = load_state()
    monkeypatch.setattr(st, "scan_devices", lambda cfg: [])
    conn = db.connect()
    db.log_event(conn, "session", "med", "dose")
    out = st.run([], _test_conn=conn)
    for k in ("ts", "day_part", "devices", "last", "scheduled", "disk"):
        assert k in out
    assert out["last"]["med"] is not None and out["last"]["med"] < 5
    assert out["last"]["meal"] is None
    assert isinstance(out["disk"]["pct"], (int, float))

def test_device_cache_used(adhdo_home, monkeypatch):
    st = load_state()
    calls = []
    monkeypatch.setattr(st, "scan_devices", lambda cfg: calls.append(1) or [])
    conn = db.connect()
    st.run([], _test_conn=conn)
    st.run([], _test_conn=conn)
    assert len(calls) == 1  # second call served from 60s cache
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/bin/state`:
```python
#!/usr/bin/env python3
import json, shutil, sys, time
from datetime import datetime
from adhdolib import db
from adhdolib.config import load_config, home
from adhdolib.envelope import cli_main

def scan_devices(cfg):
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "cast_cli", pathlib.Path(__file__).parent / "cast")
    cast = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cast)
    return cast.device_status(cfg)

def _devices(cfg):
    cache = home() / "data" / "devices_cache.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 60:
        return json.loads(cache.read_text())
    devs = scan_devices(cfg)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(devs))
    return devs

def _day_part(h):
    return ("night" if h < 6 else "morning" if h < 12
            else "afternoon" if h < 18 else "evening" if h < 22 else "night")

def run(argv, _test_conn=None):
    cfg = load_config()
    conn = _test_conn or db.connect()
    now = time.time()
    last = {}
    for t in ("med", "meal", "break", "nudge"):
        row = conn.execute("SELECT MAX(ts) FROM events WHERE type=?", (t,)).fetchone()
        last[t] = round(now - row[0], 1) if row[0] else None
    sched = [{"due_ts": r[0], "tag": r[1]} for r in conn.execute(
        "SELECT due_ts, tag FROM schedule WHERE delivered=0 ORDER BY due_ts LIMIT 10")]
    du = shutil.disk_usage("/")
    pct = round(du.used / du.total * 100, 1)
    out = {"ts": now, "day_part": _day_part(datetime.now().hour),
           "devices": _devices(cfg), "last": last, "scheduled": sched,
           "disk": {"pct": pct, "warn": pct >= cfg["disk_warn_pct"]}}
    db.audit(conn, "state", argv, True, "")
    return out

if __name__ == "__main__":
    cli_main(lambda: run(sys.argv[1:]))
```

`chmod +x adhdo2/bin/state`

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): state CLI snapshot"`

---

### Task 9: Sanitization + `wake` CLI + schedule ops

**Files:**
- Create: `adhdo2/adhdolib/sanitize.py`, `adhdo2/adhdolib/schedule.py`, `adhdo2/bin/wake`
- Test: `tests/adhdo2/test_sanitize.py`, `tests/adhdo2/test_schedule.py`, `tests/adhdo2/test_wake.py`

**Interfaces:**
- Produces:
  - `sanitize.clean(text) -> str` — strips control chars (keeps none), collapses newlines to literal `\n`, caps length 4000.
  - `schedule.add(conn, due_ts, tag) -> bool` (False if duplicate tag+due); `schedule.due(conn, now) -> list[(id, tag)]`; `schedule.mark_delivered(conn, ids)`; `schedule.consolidate_missed(conn, fixed_events: list[dict], last_wake_ts, now) -> str|None` — one summary line ("Missed while offline: meds (08:00), bedtime (22:30)") or None.
  - `wake` CLI: `wake "<prompt>"` (inject now), `wake --event <tag>` (inject "[event:<tag>] ..." per config), `wake --at "<HH:MM|ISO>" --tag T` (schedule row). Injection: flock on `data/wake.lock`; defers to `data/pending.txt` if `data/busy` exists and is <15 min old; `tmux send-keys -t adhdo -l "<clean text>"` then `tmux send-keys -t adhdo Enter`. Internals: `inject(text) -> "sent"|"queued"` with `run_tmux(args)` patched in tests.

- [ ] **Step 1: Write failing tests**

`tests/adhdo2/test_sanitize.py`:
```python
from adhdolib.sanitize import clean

def test_control_chars_stripped():
    assert clean("hi\x1b[31m;`rm`\x07") == "hi[31m;`rm`"

def test_newlines_collapsed():
    assert clean("a\nb\r\nc") == "a\\nb\\nc"

def test_length_capped():
    assert len(clean("x" * 9000)) == 4000
```

`tests/adhdo2/test_schedule.py`:
```python
import time
from adhdolib import db, schedule

def test_add_dedup_and_due(adhdo_home):
    conn = db.connect()
    now = time.time()
    assert schedule.add(conn, now - 10, "meds") is True
    assert schedule.add(conn, now - 10, "meds") is False
    due = schedule.due(conn, now)
    assert [t for _, t in due] == ["meds"]
    schedule.mark_delivered(conn, [i for i, _ in due])
    assert schedule.due(conn, now) == []

def test_consolidate_missed(adhdo_home):
    conn = db.connect()
    now = time.time()
    fixed = [{"tag": "meds", "time": "08:00"}, {"tag": "bedtime", "time": "22:30"}]
    msg = schedule.consolidate_missed(conn, fixed, last_wake_ts=now - 86400, now=now)
    assert msg is not None and "meds" in msg and "bedtime" in msg

def test_consolidate_none_when_recent(adhdo_home):
    conn = db.connect()
    now = time.time()
    msg = schedule.consolidate_missed(conn, [{"tag": "meds", "time": "08:00"}],
                                      last_wake_ts=now - 60, now=now)
    assert msg is None
```

`tests/adhdo2/test_wake.py`:
```python
import importlib.util, pathlib, time
from adhdolib import db

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "wake"

def load_wake():
    spec = importlib.util.spec_from_file_location("wake_cli", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_inject_sends_literal_then_enter(adhdo_home, monkeypatch):
    wake = load_wake()
    sent = []
    monkeypatch.setattr(wake, "run_tmux", lambda args: sent.append(args))
    assert wake.inject("hello; `x`\nworld") == "sent"
    assert sent[0][:4] == ["send-keys", "-t", "adhdo", "-l"]
    assert sent[0][4] == "hello; `x`\\nworld"
    assert sent[1] == ["send-keys", "-t", "adhdo", "Enter"]

def test_busy_marker_queues(adhdo_home, monkeypatch):
    wake = load_wake()
    monkeypatch.setattr(wake, "run_tmux", lambda args: None)
    busy = adhdo_home / "data" / "busy"
    busy.write_text("")
    assert wake.inject("later") == "queued"
    assert "later" in (adhdo_home / "data" / "pending.txt").read_text()

def test_stale_busy_marker_ignored(adhdo_home, monkeypatch):
    import os
    wake = load_wake()
    sent = []
    monkeypatch.setattr(wake, "run_tmux", lambda args: sent.append(args))
    busy = adhdo_home / "data" / "busy"
    busy.write_text("")
    old = time.time() - 16 * 60
    os.utime(busy, (old, old))
    assert wake.inject("now") == "sent"
    assert not busy.exists()

def test_at_writes_schedule_row(adhdo_home, monkeypatch):
    wake = load_wake()
    conn = db.connect()
    out = wake.run(["--at", "23:59", "--tag", "checkin"], _test_conn=conn)
    assert out["scheduled"] == "checkin"
    assert conn.execute("SELECT COUNT(*) FROM schedule").fetchone()[0] == 1
```

- [ ] **Step 2: Run, verify FAIL** (all three files)

- [ ] **Step 3: Implement**

`adhdo2/adhdolib/sanitize.py`:
```python
def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "\\n")
    text = "".join(ch for ch in text if ch >= " " or ch == "\t")
    return text[:4000]
```

`adhdo2/adhdolib/schedule.py`:
```python
import sqlite3
from datetime import datetime, timedelta

def add(conn, due_ts: float, tag: str) -> bool:
    try:
        conn.execute("INSERT INTO schedule(due_ts, tag) VALUES(?,?)", (due_ts, tag))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def due(conn, now: float):
    return conn.execute(
        "SELECT id, tag FROM schedule WHERE delivered=0 AND due_ts<=?",
        (now,)).fetchall()

def mark_delivered(conn, ids):
    conn.executemany("UPDATE schedule SET delivered=1 WHERE id=?",
                     [(i,) for i in ids])
    conn.commit()

def consolidate_missed(conn, fixed_events, last_wake_ts: float, now: float):
    missed = []
    start = datetime.fromtimestamp(last_wake_ts)
    end = datetime.fromtimestamp(now)
    for ev in fixed_events:
        h, m = map(int, ev["time"].split(":"))
        day = start.replace(hour=h, minute=m, second=0, microsecond=0)
        while day <= end:
            if start < day <= end:
                missed.append(f"{ev['tag']} ({ev['time']})")
                break
            day += timedelta(days=1)
    if not missed:
        return None
    return "Missed while offline: " + ", ".join(missed)
```

`adhdo2/bin/wake`:
```python
#!/usr/bin/env python3
import argparse, fcntl, subprocess, sys, time
from datetime import datetime
from adhdolib import db, schedule
from adhdolib.config import home
from adhdolib.envelope import ToolError, cli_main
from adhdolib.sanitize import clean

BUSY_STALE_S = 15 * 60

def run_tmux(args):
    subprocess.run(["tmux", *args], check=True, timeout=10)

def inject(text: str) -> str:
    data = home() / "data"
    data.mkdir(parents=True, exist_ok=True)
    text = clean(text)
    with open(data / "wake.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        busy = data / "busy"
        if busy.exists():
            if time.time() - busy.stat().st_mtime < BUSY_STALE_S:
                with open(data / "pending.txt", "a") as f:
                    f.write(text + "\n")
                return "queued"
            busy.unlink()  # stale
        run_tmux(["send-keys", "-t", "adhdo", "-l", text])
        run_tmux(["send-keys", "-t", "adhdo", "Enter"])
        return "sent"

def _parse_at(s: str) -> float:
    if ":" in s and len(s) <= 5:
        h, m = map(int, s.split(":"))
        due = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if due.timestamp() <= time.time():
            due = due.replace(day=due.day) + __import__("datetime").timedelta(days=1)
        return due.timestamp()
    return datetime.fromisoformat(s).timestamp()

def run(argv, _test_conn=None):
    ap = argparse.ArgumentParser(prog="wake")
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--event")
    ap.add_argument("--at")
    ap.add_argument("--tag", default="followup")
    args = ap.parse_args(argv)
    conn = _test_conn or db.connect()
    if args.at:
        ok = schedule.add(conn, _parse_at(args.at), args.tag)
        db.audit(conn, "wake", argv, True, "scheduled" if ok else "duplicate")
        return {"scheduled": args.tag, "duplicate": not ok}
    if args.event:
        text = f"[event:{args.event}] Scheduled event fired. Check state and act."
    elif args.prompt:
        text = args.prompt
    else:
        raise ToolError("usage", "wake <prompt> | --event TAG | --at TIME --tag T")
    result = inject(text)
    db.log_event(conn, "wake", "wake", text[:200])
    db.audit(conn, "wake", argv, True, result)
    return {"wake": result}

if __name__ == "__main__":
    cli_main(lambda: run(sys.argv[1:]))
```

`chmod +x adhdo2/bin/wake`

- [ ] **Step 4: Run, verify PASS** — `python -m pytest ../tests/adhdo2/ -v` (full suite; catch regressions)

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): wake CLI, sanitization, schedule ops with catch-up consolidation"`

---

### Task 10: Dispatcher + shell scripts (watchdog, recycle, catch-up, cron install)

**Files:**
- Create: `adhdo2/bin/adhdo-dispatch`, `adhdo2/scripts/adhdo-watchdog.sh`, `adhdo2/scripts/adhdo-recycle.sh`, `adhdo2/scripts/adhdo-catchup.sh`, `adhdo2/scripts/install-cron.sh`
- Test: `tests/adhdo2/test_dispatch.py`

**Interfaces:**
- Consumes: `wake.inject`, `schedule.due/mark_delivered/consolidate_missed`.
- Produces: `adhdo-dispatch` (run by cron */5): delivers pending.txt lines then due schedule rows, each via `wake`'s inject; only marks delivered/removes on `"sent"`. Shell scripts are exercised on the Pi (Task 12 E2E), not unit-tested.

- [ ] **Step 1: Write failing test**

`tests/adhdo2/test_dispatch.py`:
```python
import importlib.util, pathlib, time
from adhdolib import db, schedule

BIN = pathlib.Path(__file__).resolve().parents[2] / "adhdo2" / "bin" / "adhdo-dispatch"

def load_dispatch():
    spec = importlib.util.spec_from_file_location("dispatch_cli", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_delivers_pending_and_due(adhdo_home, monkeypatch):
    d = load_dispatch()
    sent = []
    monkeypatch.setattr(d, "inject", lambda t: sent.append(t) or "sent")
    (adhdo_home / "data" / "pending.txt").write_text("queued msg\n")
    conn = db.connect()
    schedule.add(conn, time.time() - 5, "checkin")
    out = d.run(_test_conn=conn)
    assert out == {"delivered": 2}
    assert not (adhdo_home / "data" / "pending.txt").exists()
    assert schedule.due(conn, time.time()) == []

def test_requeues_when_busy(adhdo_home, monkeypatch):
    d = load_dispatch()
    monkeypatch.setattr(d, "inject", lambda t: "queued")
    (adhdo_home / "data" / "pending.txt").write_text("msg\n")
    conn = db.connect()
    out = d.run(_test_conn=conn)
    assert out == {"delivered": 0}
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement**

`adhdo2/bin/adhdo-dispatch`:
```python
#!/usr/bin/env python3
import importlib.util, pathlib, sys, time
from adhdolib import db, schedule
from adhdolib.config import home
from adhdolib.envelope import cli_main

def _wake():
    spec = importlib.util.spec_from_file_location(
        "wake_cli", pathlib.Path(__file__).parent / "wake")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def inject(text):
    return _wake().inject(text)

def run(_test_conn=None):
    conn = _test_conn or db.connect()
    delivered = 0
    pending = home() / "data" / "pending.txt"
    if pending.exists():
        lines = [l for l in pending.read_text().splitlines() if l.strip()]
        remaining = []
        for line in lines:
            # inject() re-queues internally when busy; avoid double-append
            # by removing the file first and re-adding leftovers below.
            remaining.append(line)
        pending.unlink()
        for line in remaining:
            if inject(line) == "sent":
                delivered += 1
        # anything inject() re-queued is back in pending.txt now
    now = time.time()
    done = []
    for id_, tag in schedule.due(conn, now):
        if inject(f"[scheduled:{tag}] Follow-up you set is due.") == "sent":
            done.append(id_)
            delivered += 1
    schedule.mark_delivered(conn, done)
    return {"delivered": delivered}

if __name__ == "__main__":
    cli_main(run)
```

`chmod +x adhdo2/bin/adhdo-dispatch`

`adhdo2/scripts/adhdo-watchdog.sh`:
```bash
#!/usr/bin/env bash
# Respawn claude inside the adhdo tmux pane if it died.
set -u
PANE_PID=$(tmux list-panes -t adhdo -F '#{pane_pid}' 2>/dev/null | head -1) || exit 0
[ -z "${PANE_PID:-}" ] && exit 0
if ! pgrep -P "$PANE_PID" -f claude >/dev/null; then
  ~/adhdo2/venv/bin/python ~/adhdo2/bin/journal log error "watchdog: claude dead, respawning" || true
  tmux respawn-pane -k -t adhdo \
    "cd ~/adhdo2/session && ADHDO_HOME=~/adhdo2 claude --dangerously-skip-permissions"
fi
```

`adhdo2/scripts/adhdo-recycle.sh`:
```bash
#!/usr/bin/env bash
# Nightly 03:30: graceful handoff then fresh session. Holds the wake lock.
set -u
exec 9>~/adhdo2/data/wake.lock
flock 9
tmux send-keys -t adhdo -l 'Nightly recycle: write a concise handoff of current state, pending follow-ups, and observations to NOTES.md, then say DONE.'
tmux send-keys -t adhdo Enter
for i in $(seq 60); do  # wait up to 5 min for busy marker to clear
  sleep 5
  [ ! -e ~/adhdo2/data/busy ] && break
done
tmux respawn-pane -k -t adhdo \
  "cd ~/adhdo2/session && ADHDO_HOME=~/adhdo2 claude --dangerously-skip-permissions"
~/adhdo2/venv/bin/python ~/adhdo2/bin/journal log decision "nightly session recycle" || true
```

`adhdo2/scripts/adhdo-catchup.sh`:
```bash
#!/usr/bin/env bash
# @reboot: deliver one consolidated missed-events wake after the session is up.
sleep 120
~/adhdo2/venv/bin/python - <<'EOF'
import time
from adhdolib import db, schedule
from adhdolib.config import load_config
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("wake_cli", pathlib.Path.home() / "adhdo2/bin/wake")
wake = importlib.util.module_from_spec(spec); spec.loader.exec_module(wake)
conn = db.connect()
row = conn.execute("SELECT MAX(ts) FROM events WHERE type='wake'").fetchone()
last = row[0] or (time.time() - 86400)
fixed = [{"tag": "meds", "time": "08:00"}, {"tag": "bedtime", "time": "22:30"}]
msg = schedule.consolidate_missed(conn, fixed, last, time.time())
if msg:
    wake.inject(msg)
    db.log_event(conn, "wake", "wake", msg)
EOF
```

`adhdo2/scripts/install-cron.sh`:
```bash
#!/usr/bin/env bash
# Idempotent: replaces the ADHDO block in the pi user's crontab.
set -eu
PY=~/adhdo2/venv/bin/python
TMP=$(mktemp)
crontab -l 2>/dev/null | sed '/# ADHDO-BEGIN/,/# ADHDO-END/d' > "$TMP" || true
cat >> "$TMP" <<CRON
# ADHDO-BEGIN
*/25 * * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake "[heartbeat] Run state, reason, act or do nothing." >/dev/null 2>&1
0 8 * * *   ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event meds >/dev/null 2>&1
30 22 * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/wake --event bedtime >/dev/null 2>&1
*/5 * * * * ADHDO_HOME=\$HOME/adhdo2 $PY \$HOME/adhdo2/bin/adhdo-dispatch >/dev/null 2>&1
*/5 * * * * \$HOME/adhdo2/scripts/adhdo-watchdog.sh >/dev/null 2>&1
30 3 * * *  \$HOME/adhdo2/scripts/adhdo-recycle.sh >/dev/null 2>&1
@reboot     \$HOME/adhdo2/scripts/adhdo-catchup.sh >/dev/null 2>&1
# ADHDO-END
CRON
crontab "$TMP"
rm "$TMP"
echo "cron installed"
```

`chmod +x adhdo2/scripts/*.sh`

- [ ] **Step 4: Run full suite, verify PASS** — `python -m pytest ../tests/adhdo2/ -v`

- [ ] **Step 5: Commit** — `git commit -m "feat(adhdo2): dispatcher, watchdog, recycle, catch-up, cron install"`

---

### Task 11: systemd units, session CLAUDE.md + hooks, Jellyfin compose, deploy script

**Files:**
- Create: `adhdo2/systemd/adhdo-tmux.service`, `adhdo2/systemd/adhdo-httpd.service`, `adhdo2/session/CLAUDE.md`, `adhdo2/session/settings.json`, `adhdo2/docker/jellyfin-compose.yml`, `adhdo2/scripts/deploy.sh`

**Interfaces:**
- Consumes: everything above (paths as deployed on the Pi).
- Produces: deployable infrastructure. No unit tests — verified on-Pi in Task 12.

- [ ] **Step 1: systemd units**

`adhdo2/systemd/adhdo-tmux.service`:
```ini
[Unit]
Description=ADHDo tmux server with resident Claude session
After=network-online.target

[Service]
Type=forking
Environment=ADHDO_HOME=%h/adhdo2
ExecStart=/usr/bin/tmux new-session -d -s adhdo -c %h/adhdo2/session \
  "ADHDO_HOME=%h/adhdo2 claude --dangerously-skip-permissions"
ExecStop=/usr/bin/tmux kill-session -t adhdo
Restart=on-failure

[Install]
WantedBy=default.target
```

`adhdo2/systemd/adhdo-httpd.service`:
```ini
[Unit]
Description=ADHDo TTS cache static server
After=network-online.target

[Service]
WorkingDirectory=%h/adhdo2/tts-cache
ExecStart=/usr/bin/python3 -m http.server 8765 --bind 0.0.0.0
Restart=always

[Install]
WantedBy=default.target
```

(Binding 0.0.0.0 is acceptable: the Pi is LAN-only; the directory contains only generated TTS MP3s.)

- [ ] **Step 2: Session CLAUDE.md and hooks**

`adhdo2/session/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command",
      "command": "touch \"$ADHDO_HOME/data/busy\""}]}],
    "Stop": [{"hooks": [{"type": "command",
      "command": "rm -f \"$ADHDO_HOME/data/busy\""}]}]
  }
}
```

`adhdo2/session/CLAUDE.md` (complete content):
```markdown
# ADHDo — Resident Executive-Function Companion

You are the always-on cognitive companion for Adrian (ADHD). You run in a
tmux session on pi5-hailo. Messages arrive as heartbeats (`[heartbeat]`),
events (`[event:meds]`, `[event:bedtime]`), scheduled follow-ups
(`[scheduled:tag]`), or direct text from Adrian.

## Your toolbelt (run via Bash; all print JSON; nonzero exit = JSON error)
- `~/adhdo2/venv/bin/python ~/adhdo2/bin/state` — situation snapshot. Run this FIRST on every wake-up.
- `... bin/cast play <mood|url> [--device D]` / `cast stop` / `cast volume 0.4` / `cast status`
- `... bin/nudge "text" [--device D] [--urgency low|med|high] [--event medication|safety|user_requested]`
- `... bin/journal log <type> "<text>"` — types: med, meal, break, decision, outcome, feedback, error
- `... bin/journal recent 20` · `... bin/journal patterns`
- `... bin/wake --at "HH:MM" --tag <tag>` — schedule your own follow-up

## Wake-up routine
1. Run `state`. 2. Check calendar/Gmail connectors if the situation warrants.
3. Consult `journal patterns` before choosing intervention type/timing.
4. Act — or deliberately do nothing (often correct). 5. `journal log decision`
with one line of reasoning, and later `journal log outcome` when observable.

## Policies (non-negotiable)
- If a tool returns `rate_limited` or `quiet_hours`, do NOT retry this cycle.
- Never work around the nudge tool (no direct pychromecast, no other TTS path).
- Nudges are brief, kind, concrete: "Time to step away — 3h of screen time" not lectures.
- If `state.disk.warn` is true, mention it to Adrian at most once per day.
- If a connector fails or needs re-auth: `journal log error`, tell Adrian, move on with local state.
- On start: read NOTES.md and `journal recent 30` to restore continuity.
- Nightly recycle prompt: write handoff to NOTES.md exactly as asked, then say DONE.

## Crisis (fixed response — never improvise)
If Adrian's words indicate self-harm risk or acute crisis, respond with
exactly: support, plus "Lifeline Australia: 13 11 14 (24/7). If in immediate
danger call 000." Do not use tools. Do not analyze. Stay with him.
```

- [ ] **Step 3: Jellyfin compose**

`adhdo2/docker/jellyfin-compose.yml`:
```yaml
services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    network_mode: host          # simplest path to LAN-IP reachability + DLNA
    volumes:
      - /home/pi/adhdo2/jellyfin/config:/config
      - /home/pi/Music:/media/music:ro
      - jellyfin-transcode:/config/transcodes
    restart: unless-stopped
volumes:
  jellyfin-transcode:
    driver_opts: {type: tmpfs, device: tmpfs, o: "size=512m"}
```

Post-install config (manual, in Jellyfin admin UI, part of Task 12): disable transcoding, disable chapter-image extraction, create mood playlists, generate API key.

- [ ] **Step 4: Deploy script**

`adhdo2/scripts/deploy.sh`:
```bash
#!/usr/bin/env bash
# Deploy adhdo2 from the repo to pi@pi5-hailo:~/adhdo2
set -eu
SRC="$(cd "$(dirname "$0")/.." && pwd)"
rsync -av --exclude venv --exclude data --exclude tts-cache --exclude jellyfin \
  "$SRC/" pi@pi5-hailo:~/adhdo2/
ssh pi@pi5-hailo '
  set -eu
  cd ~/adhdo2
  [ -d venv ] || python3 -m venv venv
  venv/bin/pip -q install PyYAML pychromecast pytest
  mkdir -p data tts-cache
  [ -f config.yaml ] || cp config.example.yaml config.yaml
  mkdir -p ~/.config/systemd/user
  cp systemd/*.service ~/.config/systemd/user/
  systemctl --user daemon-reload
  echo "deployed; run scripts/install-cron.sh and enable units when ready"
'
```

`chmod +x adhdo2/scripts/deploy.sh`

- [ ] **Step 5: Run full test suite one more time** — `python -m pytest ../tests/adhdo2/ -v` → all PASS.

- [ ] **Step 6: Commit** — `git commit -m "feat(adhdo2): systemd units, resident session config, jellyfin compose, deploy script"`

---

### Task 12: Provision pi5-hailo + hardware E2E

**Files:**
- Create: `adhdo2/E2E_CHECKLIST.md`
- On-Pi actions (via SSH from the Mac).

**Interfaces:**
- Consumes: everything. This task turns the code into a running system.

- [ ] **Step 1: Pi prerequisites**

```bash
ssh pi@pi5-hailo 'sudo apt-get update && sudo apt-get install -y tmux espeak-ng ffmpeg && sudo loginctl enable-linger pi'
```
Expected: installs succeed; `loginctl show-user pi | grep Linger` → `Linger=yes`.

- [ ] **Step 2: Verify/install Piper (spec prerequisite; espeak-ng is the working fallback)**

```bash
ssh pi@pi5-hailo 'pipx install piper-tts 2>/dev/null || ~/adhdo2/venv/bin/pip install piper-tts; echo test | piper --help >/dev/null 2>&1 && echo PIPER_OK || echo PIPER_MISSING_USING_ESPEAK'
```
Either outcome is acceptable; record which in E2E_CHECKLIST.md.

- [ ] **Step 3: Static IP** — reserve the Pi's current IP in the router's DHCP (manual, note the IP), set it as `lan_ip` in `~/adhdo2/config.yaml` on the Pi along with real device names from `avahi-browse -t _googlecast._tcp`.

- [ ] **Step 4: Deploy + services**

```bash
adhdo2/scripts/deploy.sh
ssh pi@pi5-hailo 'systemctl --user enable --now adhdo-httpd adhdo-tmux && ~/adhdo2/scripts/install-cron.sh'
```
Expected: `systemctl --user status adhdo-tmux` active; `tmux -L default has-session -t adhdo` (via ssh) exits 0; Claude Code greets inside the pane (needs one interactive `claude login` first if not authenticated — do that in the pane over SSH).

- [ ] **Step 5: Jellyfin**

```bash
ssh pi@pi5-hailo 'cd ~/adhdo2/docker && docker compose -f jellyfin-compose.yml up -d'
```
Then browse to `http://<lan_ip>:8096`, complete setup wizard, disable transcoding + chapter images, add Music library, create `focus`/`calm` playlists, generate API key, put playlist IDs + key into `config.yaml`.

- [ ] **Step 6: Run the E2E checklist** — create `adhdo2/E2E_CHECKLIST.md`:

```markdown
# ADHDo 2.0 P1 Hardware E2E (run on pi5-hailo, record results inline)

- [ ] `bin/state` returns full schema; devices list shows real Nest devices online
- [ ] `bin/cast play focus` → music audibly plays on default device (source: jellyfin)
- [ ] Stop Jellyfin container → `cast play focus` falls back to stream (source: stream)
- [ ] `bin/nudge "test nudge"` → device speaks; interrupted music resumes after
      (refine resume wait: poll media_controller.status until idle, max 30 s —
      implement in nudge's `_resume_previous` now that behavior is observable)
- [ ] 5 rapid nudges → 5th returns {"error":"rate_limited"}
- [ ] `bin/nudge "x"` during configured quiet hours → {"error":"quiet_hours"};
      `--urgency high --event medication` → speaks
- [ ] `bin/wake "hello from wake"` → text appears in the adhdo tmux pane and Claude responds
- [ ] `bin/wake "test"` while Claude is mid-response → "queued"; adhdo-dispatch delivers it after
- [ ] `bin/wake --at <2 min from now> --tag t1` → dispatcher injects within 5 min
- [ ] Kill claude in the pane (`pkill -f claude`) → watchdog respawns within 5 min; journal has error row
- [ ] `scripts/adhdo-recycle.sh` → handoff written to NOTES.md, fresh session, continuity on greet
- [ ] Reboot Pi with a meds event in the past → single consolidated catch-up wake, no storm
- [ ] Full heartbeat observed: cron fires, session runs state, journals a decision
```

Work through it over SSH; fix what fails; record outcomes.

- [ ] **Step 7: Commit** (checklist results + the resume-wait refinement in `nudge`)

```bash
git add adhdo2
git commit -m "feat(adhdo2): P1 provisioned on pi5-hailo, hardware E2E complete"
```

---

## Self-Review Notes

- **Spec coverage:** config loader (T1), envelope (T2), journal schema incl. audit/schedule/rollups (T3–T4), nudge limits + TTS + resume contract (T5–T6), cast + mood resolution + now_playing (T7), state schema + disk warn + device cache (T8), wake contract: flock/busy/sanitize/--at/pending (T9), dispatcher/watchdog/recycle/catch-up/cron (T10), systemd/hooks/CLAUDE.md/crisis/Jellyfin-tmpfs/deploy (T11), prerequisites (static IP, Piper verify, linger) + E2E (T12). Rollup *generation* (nightly aggregation job) and 90-day retention pruning are deliberately deferred to P2 — `patterns` computes live over events until data volume warrants rollups; the table exists so the schema doesn't migrate.
- **Placeholders:** the one intentional deferral is nudge's resume-wait polish, explicitly assigned to Task 12 Step 6 where the hardware makes it observable.
- **Type consistency:** `run(argv, _test_conn=...)` convention across all CLIs; `inject() -> "sent"|"queued"`; envelope codes used in tests match implementations (`rate_limited`, `quiet_hours`, `bad_override`, `unknown_mood`, `no_devices`, `tts_failed`, `crash`).
```
