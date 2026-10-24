import argparse, json, os, sys, traceback, re
from pathlib import Path

_SECRET_RE = re.compile(r"(api_key|apikey|token|password|secret)=[^&\s\"']+", re.I)

def scrub(text: str) -> str:
    """Redact sensitive data from text: replaces secret values with REDACTED."""
    return _SECRET_RE.sub(r"\1=REDACTED", text)

class ToolError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail)
        self.code, self.detail = code, detail

class ToolArgumentParser(argparse.ArgumentParser):
    """argparse.ArgumentParser variant that raises ToolError instead of
    printing usage to stderr and calling sys.exit() directly, so CLI
    argument errors still go through the JSON envelope."""
    def error(self, message):
        raise ToolError("usage", message)

def write_atomic(path, text: str) -> None:
    """Write text to path atomically: write to a temp file in the same
    directory, then os.replace() it into place."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(str(tmp), str(path))

def cli_main(fn):
    try:
        out = fn()
        print(scrub(json.dumps(out, default=str)))
        sys.exit(0)
    except ToolError as e:
        print(json.dumps({"error": e.code, "detail": scrub(e.detail)}))
        sys.exit(1)
    except Exception as e:
        # Deliberately Exception, not BaseException: KeyboardInterrupt and
        # SystemExit must propagate so Ctrl-C / exit codes behave normally.
        tail = "".join(traceback.format_tb(e.__traceback__)[-3:])
        print(json.dumps({"error": "crash",
                          "detail": scrub(f"{type(e).__name__}: {e}"),
                          "trace_tail": scrub(tail)}))
        sys.exit(1)
