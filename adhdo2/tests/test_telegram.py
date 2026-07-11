import json, time
import pytest
from adhdolib import db
from adhdolib import telegram as tg
from adhdolib.binload import load_bin_module
from adhdolib.envelope import ToolError
from adhdolib.sanitize import redact


class FakeAPI:
    def __init__(self):
        self.sent = []
        self.updates = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return {"message_id": len(self.sent)}

    def get_updates(self, offset, timeout=50):
        due = [u for u in self.updates if u["update_id"] >= offset]
        self.updates = []
        return due


def make_bridge(conn, allowlist=(42,), rate=6):
    cfg = {"telegram": {"chat_id_allowlist": list(allowlist),
                        "rate_limit_per_minute": rate}}
    api = FakeAPI()
    injected = []
    bridge = tg.Bridge(cfg, conn, lambda text: injected.append(text) or "sent", api)
    return bridge, api, injected


def msg(chat_id, text=None, update_id=1, **extra):
    m = {"chat": {"id": chat_id}}
    if text is not None:
        m["text"] = text
    m.update(extra)
    return {"update_id": update_id, "message": m}


# --- crisis screen -----------------------------------------------------

@pytest.mark.parametrize("text", [
    "I want to kill myself",
    "thinking about suicide again",
    "I might hurt myself tonight",
    "there's no point living",
    "I can't go on",
])
def test_crisis_screen_matches(text):
    assert tg.crisis_screen(text)


@pytest.mark.parametrize("text", [
    "help me focus on this task",
    "I give up on this bug",
    "this deadline is a crisis",
    "kill the server process",
])
def test_crisis_screen_ignores_normal_adhd_talk(text):
    assert not tg.crisis_screen(text)


# --- bridge ------------------------------------------------------------

def test_disallowed_chat_denied_and_journaled(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn)
    out = bridge.handle_update(msg(999, "hi"))
    assert out["action"] == "denied"
    assert injected == [] and api.sent == []
    row = conn.execute("SELECT type, payload_json FROM events").fetchone()
    assert row[0] == "error" and "chat_not_allowed" in row[1]


def test_allowed_text_forwarded_quoted_and_journaled(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn)
    out = bridge.handle_update(msg(42, "please play focus music"))
    assert out == {"action": "forwarded", "chat_id": 42,
                   "crisis_advisory": False, "delivery": "sent"}
    assert injected == ['[telegram chat:42] User says: "please play focus music"']
    row = conn.execute("SELECT source, type, payload_json FROM events").fetchone()
    assert row[0] == "telegram" and row[1] == "wake"
    payload = json.loads(row[2])
    assert payload == {"chat_id": 42, "text": "please play focus music",
                       "crisis_advisory": False}


def test_crisis_advisory_flag_never_blocks(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn)
    out = bridge.handle_update(msg(42, "I want to kill myself"))
    assert out["action"] == "forwarded" and out["crisis_advisory"] is True
    assert injected and "[crisis_advisory]" in injected[0]
    payload = json.loads(conn.execute(
        "SELECT payload_json FROM events WHERE type='wake'").fetchone()[0])
    assert payload["crisis_advisory"] is True


def test_media_refused_with_reply(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn)
    out = bridge.handle_update(msg(42, photo=[{"file_id": "x"}]))
    assert out["action"] == "refused_media"
    assert injected == []
    assert api.sent and api.sent[0][0] == 42
    row = conn.execute("SELECT type, payload_json FROM events").fetchone()
    assert row[0] == "error" and "non_text_refused" in row[1]


def test_rate_limit_per_chat_per_minute(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn, rate=2)
    for i in range(2):
        assert bridge.handle_update(msg(42, f"m{i}"))["action"] == "forwarded"
    out = bridge.handle_update(msg(42, "m3"))
    assert out["action"] == "rate_limited"
    assert len(injected) == 2
    assert any("rate limit" in t.lower() for _, t in api.sent)
    assert conn.execute("SELECT COUNT(*) FROM events WHERE type='error'").fetchone()[0] == 1


def test_rate_limit_window_expires(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn, rate=1)
    assert bridge.handle_update(msg(42, "a"))["action"] == "forwarded"
    # age the recorded timestamp past the 60s window
    bridge._recent[42][0] = time.time() - 61
    assert bridge.handle_update(msg(42, "b"))["action"] == "forwarded"


def test_non_message_update_ignored(adhdo_home):
    conn = db.connect()
    bridge, api, injected = make_bridge(conn)
    assert bridge.handle_update({"update_id": 1})["action"] == "ignored"
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


# --- token handling ----------------------------------------------------

def test_get_token_env_overrides_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
    assert tg.get_token({"telegram": {"bot_token": "cfg-token"}}) == "env-token"
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    assert tg.get_token({"telegram": {"bot_token": "cfg-token"}}) == "cfg-token"


def test_get_token_missing_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ToolError) as e:
        tg.get_token({"telegram": {"bot_token": None}})
    assert e.value.code == "no_token"


def test_redact_scrubs_token():
    assert redact("https://api.telegram.org/bot123:ABC/getUpdates", "123:ABC") \
        == "https://api.telegram.org/botREDACTED/getUpdates"
    assert redact("no secret here", None) == "no secret here"


def test_api_error_detail_is_scrubbed(monkeypatch):
    import urllib.error
    api = tg.TelegramAPI("123:SECRET")

    def boom(url, data=None, timeout=None):
        raise urllib.error.URLError(f"cannot reach {url}")

    monkeypatch.setattr(tg.urllib.request, "urlopen", boom)
    with pytest.raises(ToolError) as e:
        api.send_message(1, "hi")
    assert "123:SECRET" not in e.value.detail
    assert "REDACTED" in e.value.detail


def test_api_not_ok_raises_scrubbed(monkeypatch):
    import io

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    body = json.dumps({"ok": False, "description": "Unauthorized bot123:SECRET"}).encode()
    monkeypatch.setattr(tg.urllib.request, "urlopen",
                        lambda url, data=None, timeout=None: FakeResp(body))
    api = tg.TelegramAPI("123:SECRET")
    with pytest.raises(ToolError) as e:
        api.get_updates(0)
    assert e.value.code == "telegram_api" and "123:SECRET" not in e.value.detail


def test_api_ok_returns_result(monkeypatch):
    import io

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    captured = {}

    def fake_urlopen(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResp(json.dumps({"ok": True, "result": [{"update_id": 7}]}).encode())

    monkeypatch.setattr(tg.urllib.request, "urlopen", fake_urlopen)
    api = tg.TelegramAPI("tok")
    assert api.get_updates(5) == [{"update_id": 7}]
    assert "/bottok/getUpdates" in captured["url"]
    assert b"offset=5" in captured["data"]


# --- CLI ---------------------------------------------------------------

def load_cli():
    return load_bin_module("adhdo-telegram")


def test_cli_send(adhdo_home, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    cli = load_cli()
    fake = FakeAPI()
    monkeypatch.setattr(tg, "TelegramAPI", lambda token: fake)
    conn = db.connect()
    out = cli.run(["send", "42", "hello there"], _test_conn=conn)
    assert out == {"sent": True, "chat_id": 42}
    assert fake.sent == [(42, "hello there")]
    row = conn.execute("SELECT tool, ok, detail FROM audit").fetchone()
    assert row == ("adhdo-telegram", 1, "sent")


def test_cli_usage_error(adhdo_home, monkeypatch):
    cli = load_cli()
    with pytest.raises(ToolError) as e:
        cli.run([])
    assert e.value.code == "usage"


def test_cli_no_token(adhdo_home, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    cli = load_cli()
    conn = db.connect()
    with pytest.raises(ToolError) as e:
        cli.run(["send", "42", "hi"], _test_conn=conn)
    assert e.value.code == "no_token"


def test_daemon_once_processes_and_advances_offset(adhdo_home, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    cli = load_cli()
    fake = FakeAPI()
    fake.updates = [msg(42, "hello", update_id=10),
                    msg(42, "world", update_id=11)]
    monkeypatch.setattr(tg, "TelegramAPI", lambda token: fake)
    # config allowlist: write a config.yaml in ADHDO_HOME
    (adhdo_home / "config.yaml").write_text("telegram: {chat_id_allowlist: [42]}\n")
    injected = []
    wake = load_bin_module("wake")
    monkeypatch.setattr(wake, "run_tmux", lambda args: injected.append(args))
    monkeypatch.setattr(cli, "load_bin_module", lambda name: wake)
    conn = db.connect()
    out = cli.run(["run", "--once"], _test_conn=conn)
    assert out == {"polled": True, "handled": 2}
    assert (adhdo_home / "data" / "telegram.offset").read_text() == "12"
    # two messages -> two literal send-keys + two Enter presses
    literal = [a for a in injected if "-l" in a]
    assert len(literal) == 2 and 'User says: "hello"' in literal[0][-1]
    assert conn.execute("SELECT COUNT(*) FROM events WHERE type='wake'").fetchone()[0] == 2


def test_daemon_once_poll_error_journaled(adhdo_home, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    cli = load_cli()

    class ErrAPI(FakeAPI):
        def get_updates(self, offset, timeout=50):
            raise ToolError("telegram_api", "boom")

    monkeypatch.setattr(tg, "TelegramAPI", lambda token: ErrAPI())
    conn = db.connect()
    out = cli.run(["run", "--once"], _test_conn=conn)
    assert out == {"polled": True, "handled": 0}
    row = conn.execute("SELECT type, payload_json FROM events").fetchone()
    assert row[0] == "error" and "telegram_api" in row[1]


def test_config_defaults_include_telegram_fields(adhdo_home):
    from adhdolib.config import load_config
    cfg = load_config()
    assert cfg["telegram"]["chat_id_allowlist"] == []
    assert cfg["telegram"]["bot_token"] is None
    assert cfg["telegram"]["rate_limit_per_minute"] == 6
