import importlib.util, json, pathlib, subprocess, sys, os

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "journal"

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
