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
