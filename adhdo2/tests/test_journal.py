import importlib.util, json, pathlib, subprocess, sys, os, time

from adhdolib import db

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

def test_patterns_nudge_response_rate_by_type_values(adhdo_home):
    run_cli(adhdo_home, "log", "nudge", json.dumps({"urgency": "high"}))
    code, out = run_cli(adhdo_home, "patterns")
    assert code == 0
    assert out["nudge_response_rate_by_type"] == {"high": 1}

def test_outcome_logs_structured_row(adhdo_home):
    code, out = run_cli(adhdo_home, "outcome", "nudge", "worked", "took", "the", "break")
    assert code == 0
    assert out == {"logged": "outcome", "intervention": "nudge", "outcome": "worked"}
    code, out = run_cli(adhdo_home, "recent", "1")
    ev = out["events"][0]
    assert ev["type"] == "outcome"
    assert ev["payload"] == {"intervention": "nudge", "outcome": "worked",
                             "feedback": "took the break"}

def test_outcome_without_feedback(adhdo_home):
    code, out = run_cli(adhdo_home, "outcome", "cast", "ignored")
    assert code == 0
    _, out = run_cli(adhdo_home, "recent", "1")
    assert out["events"][0]["payload"] == {"intervention": "cast", "outcome": "ignored"}

def test_outcome_bad_value_is_enveloped(adhdo_home):
    code, out = run_cli(adhdo_home, "outcome", "nudge", "amazing")
    assert code == 1 and out["error"] == "bad_outcome"

def test_outcome_usage_error(adhdo_home):
    code, out = run_cli(adhdo_home, "outcome", "nudge")
    assert code == 1 and out["error"] == "usage"

def test_patterns_surfaces_outcomes(adhdo_home):
    run_cli(adhdo_home, "outcome", "nudge", "worked")
    run_cli(adhdo_home, "outcome", "nudge", "ignored")
    run_cli(adhdo_home, "outcome", "cast", "partial")
    code, out = run_cli(adhdo_home, "patterns")
    assert code == 0
    assert out["outcome_by_intervention"] == {
        "nudge": {"worked": 1, "ignored": 1}, "cast": {"partial": 1}}
    assert out["success_rate_by_intervention"] == {"nudge": 0.5, "cast": 0.5}
    dayparts = out["outcome_by_daypart"]
    assert sum(n for b in dayparts.values() for n in b.values()) == 3

def test_patterns_outcome_keys_present_when_empty(adhdo_home):
    code, out = run_cli(adhdo_home, "patterns")
    assert code == 0
    assert out["outcome_by_intervention"] == {}
    assert out["outcome_by_daypart"] == {}
    assert out["success_rate_by_intervention"] == {}

def test_patterns_mood_by_daypart_nested(adhdo_home):
    run_cli(adhdo_home, "log", "cast", json.dumps({"mood": "focused"}))
    code, out = run_cli(adhdo_home, "patterns")
    assert code == 0
    moods = out["mood_by_daypart"]
    assert len(moods) >= 1
    found = any(mood_counts.get("focused") == 1
                for mood_counts in moods.values())
    assert found

def _insert_event(adhdo_home, ts, type_, payload):
    conn = db.connect()
    conn.execute("INSERT INTO events(ts, source, type, payload_json) VALUES(?,?,?,?)",
                 (ts, "test", type_, json.dumps(payload)))
    conn.commit()
    conn.close()

def test_rollup_aggregates_past_days(adhdo_home):
    yesterday = time.time() - 86400
    _insert_event(adhdo_home, yesterday, "outcome",
                  {"intervention": "nudge", "outcome": "worked"})
    _insert_event(adhdo_home, yesterday, "nudge", {"urgency": "low"})
    code, out = run_cli(adhdo_home, "rollup")
    assert code == 0
    assert len(out["rolled_up_days"]) == 1
    day = out["rolled_up_days"][0]
    conn = db.connect()
    rows = {m: json.loads(v) for (m, v) in conn.execute(
        "SELECT metric, value_json FROM rollups WHERE day=?", (day,))}
    conn.close()
    assert rows["events_by_type"] == {"outcome": 1, "nudge": 1}
    assert rows["outcomes"] == {"nudge:worked": 1}
    assert sum(rows["nudges_by_hour"].values()) == 1

def test_rollup_is_idempotent_and_skips_today(adhdo_home):
    run_cli(adhdo_home, "log", "med", "today dose")  # today: not rolled up
    _insert_event(adhdo_home, time.time() - 86400, "med", "yesterday dose")
    code, out = run_cli(adhdo_home, "rollup")
    assert code == 0 and len(out["rolled_up_days"]) == 1
    code, out = run_cli(adhdo_home, "rollup")
    assert code == 0 and out["rolled_up_days"] == []

def test_rollup_prunes_rows_older_than_90_days(adhdo_home):
    old = time.time() - 91 * 86400
    _insert_event(adhdo_home, old, "nudge", {"urgency": "low"})
    conn = db.connect()
    conn.execute("INSERT INTO audit(ts, tool, argv, ok, detail) VALUES(?,?,?,?,?)",
                 (old, "nudge", "[]", 1, ""))
    conn.commit()
    conn.close()
    run_cli(adhdo_home, "log", "med", "fresh row")
    code, out = run_cli(adhdo_home, "rollup")
    assert code == 0
    assert out["pruned_events"] == 1 and out["pruned_audit"] == 1
    conn = db.connect()
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    # the old day was still rolled up before pruning
    assert conn.execute("SELECT COUNT(*) FROM rollups").fetchone()[0] > 0
    conn.close()
