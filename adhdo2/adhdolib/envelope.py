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
