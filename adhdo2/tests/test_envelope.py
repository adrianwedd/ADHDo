import json, subprocess, sys, pathlib
import pytest
from adhdolib.envelope import ToolArgumentParser, ToolError, cli_main, write_atomic, scrub

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

def test_scrub_api_key():
    text = "GET http://x/Items?api_key=SECRET123 failed"
    scrubbed = scrub(text)
    assert "SECRET123" not in scrubbed
    assert "api_key=REDACTED" in scrubbed

def test_scrub_multiple_patterns():
    text = "api_key=SECRET1 token=SECRET2 password=SECRET3 apikey=SECRET4"
    scrubbed = scrub(text)
    assert "SECRET1" not in scrubbed
    assert "SECRET2" not in scrubbed
    assert "SECRET3" not in scrubbed
    assert "SECRET4" not in scrubbed
    assert "api_key=REDACTED" in scrubbed
    assert "token=REDACTED" in scrubbed
    assert "password=REDACTED" in scrubbed
    assert "apikey=REDACTED" in scrubbed

def test_scrub_url_with_multiple_params():
    url = "http://x?api_key=SECRET&user=alice&token=MY_TOKEN"
    scrubbed = scrub(url)
    assert "SECRET" not in scrubbed
    assert "MY_TOKEN" not in scrubbed
    assert "user=alice" in scrubbed
    assert "api_key=REDACTED" in scrubbed
    assert "token=REDACTED" in scrubbed

def test_tool_error_detail_scrubbed(capsys):
    def f(): raise ToolError("jellyfin_error", "GET http://x/Items?api_key=SECRET123 failed")
    code, out = run(f, capsys)
    assert code == 1
    assert out["error"] == "jellyfin_error"
    assert "SECRET123" not in out["detail"]
    assert "api_key=REDACTED" in out["detail"]

def test_success_with_secret_url_scrubbed(capsys):
    def f(): return {"url": "http://x?api_key=SECRET"}
    code, out = run(f, capsys)
    assert code == 0
    assert "SECRET" not in json.dumps(out)
    assert "api_key=REDACTED" in json.dumps(out)

def test_crash_detail_scrubbed(capsys):
    def f(): raise ValueError("api_key=SECRET123")
    code, out = run(f, capsys)
    assert code == 1
    assert out["error"] == "crash"
    assert "SECRET123" not in out["detail"]
    assert "api_key=REDACTED" in out["detail"]

def test_crash_trace_scrubbed(capsys):
    def inner(): raise ValueError("token=MYSECRET")
    def f(): inner()
    code, out = run(f, capsys)
    assert code == 1
    assert "MYSECRET" not in out["trace_tail"]
    assert "token=REDACTED" in out["trace_tail"]
