import json, subprocess, sys, pathlib
import pytest
from adhdolib.envelope import ToolArgumentParser, ToolError, cli_main, write_atomic

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

def test_tool_argument_parser_raises_tool_error(capsys):
    ap = ToolArgumentParser(prog="x")
    ap.add_argument("cmd", choices=["a", "b"])
    def f():
        args = ap.parse_args(["bogus"])
        return {"unreachable": True}
    code, out = run(f, capsys)
    assert code == 1
    assert out["error"] == "usage"

def test_cast_bogus_subcommand_returns_json_usage_error():
    bin_path = pathlib.Path(__file__).resolve().parents[1] / "bin" / "cast"
    proc = subprocess.run([sys.executable, str(bin_path), "bogus"],
                          capture_output=True, text=True)
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["error"] == "usage"

def test_write_atomic(tmp_path):
    target = tmp_path / "data.json"
    write_atomic(target, '{"a": 1}')
    assert target.read_text() == '{"a": 1}'
    assert not (tmp_path / "data.json.tmp").exists()
    write_atomic(target, '{"a": 2}')
    assert target.read_text() == '{"a": 2}'
