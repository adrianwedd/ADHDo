"""Telegram bridge core: allowlist, per-chat rate limit, advisory crisis
screen, journaling, and a stdlib-only (urllib) Telegram Bot API client.

Free text from Telegram is forwarded into the resident session through
bin/wake's inject() (literal tmux send-keys) — it can never become tmux
commands. The crisis screen is ADVISORY only: matched messages are flagged
in the journal and the forwarded payload, never blocked."""
import json, os, re, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict, deque

from . import db
from .envelope import ToolError
from .sanitize import redact

# Ported from the legacy src/mcp_server/llm_client.py SafetyMonitor
# crisis_patterns, tightened per the spec: the security_middleware.py
# patterns (crisis|emergency|help me) false-positive heavily on normal
# ADHD talk ("help me focus") and are deliberately NOT included.
CRISIS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r"\b(want to die|kill myself|end it all|suicide|suicidal)\b",
    r"\b(harm myself|hurt myself|self[- ]harm)\b",
    r"\b(no point (in )?living|life isn'?t worth|rather be dead)\b",
    r"\b(can'?t go on|want to disappear|end the pain)\b",
)]


def crisis_screen(text: str) -> bool:
    return any(p.search(text) for p in CRISIS_PATTERNS)


def get_token(cfg: dict) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg["telegram"].get("bot_token")
    if not token:
        raise ToolError("no_token",
                        "set telegram.bot_token in config.yaml or TELEGRAM_BOT_TOKEN")
    return token


class TelegramAPI:
    """Minimal Telegram Bot API client on urllib only."""

    def __init__(self, token: str, base: str = "https://api.telegram.org"):
        self.token = token
        self.base = base

    def _call(self, method: str, params: dict, timeout: float = 70):
        url = f"{self.base}/bot{self.token}/{method}"
        data = urllib.parse.urlencode(params).encode()
        try:
            with urllib.request.urlopen(url, data=data, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = redact(f"{method}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}",
                            self.token)
            raise ToolError("telegram_api", detail)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise ToolError("telegram_api", redact(f"{method}: {type(e).__name__}: {e}", self.token))
        if not body.get("ok"):
            raise ToolError("telegram_api",
                            redact(f"{method}: {body.get('description', 'not ok')}", self.token))
        return body["result"]

    def get_updates(self, offset: int, timeout: int = 50):
        return self._call("getUpdates",
                          {"offset": offset, "timeout": timeout,
                           "allowed_updates": '["message"]'},
                          timeout=timeout + 20)

    def send_message(self, chat_id, text: str):
        return self._call("sendMessage", {"chat_id": chat_id, "text": text}, timeout=30)


class Bridge:
    """Handles inbound updates: allowlist -> text-only -> rate limit ->
    crisis screen (advisory) -> journal -> inject into the session."""

    def __init__(self, cfg: dict, conn, injector, api: TelegramAPI):
        tcfg = cfg["telegram"]
        self.allowlist = {int(c) for c in tcfg["chat_id_allowlist"]}
        self.rate_limit = int(tcfg.get("rate_limit_per_minute", 6))
        self.conn = conn
        self.injector = injector  # wake.inject: returns "sent" or "queued"
        self.api = api
        self._recent = defaultdict(deque)  # chat_id -> timestamps of forwarded msgs

    def _rate_limited(self, chat_id, now: float) -> bool:
        q = self._recent[chat_id]
        while q and q[0] <= now - 60:
            q.popleft()
        if len(q) >= self.rate_limit:
            return True
        q.append(now)
        return False

    def handle_update(self, update: dict) -> dict:
        msg = update.get("message")
        if not msg or "chat" not in msg:
            return {"action": "ignored"}
        chat_id = msg["chat"]["id"]
        if chat_id not in self.allowlist:
            db.log_event(self.conn, "telegram", "error",
                         json.dumps({"reason": "chat_not_allowed", "chat_id": chat_id}))
            return {"action": "denied", "chat_id": chat_id}
        text = msg.get("text")
        if not text:
            db.log_event(self.conn, "telegram", "error",
                         json.dumps({"reason": "non_text_refused", "chat_id": chat_id}))
            self.api.send_message(chat_id, "Text messages only, sorry — media is ignored.")
            return {"action": "refused_media", "chat_id": chat_id}
        if self._rate_limited(chat_id, time.time()):
            db.log_event(self.conn, "telegram", "error",
                         json.dumps({"reason": "rate_limited", "chat_id": chat_id}))
            self.api.send_message(chat_id, "Slow down a moment — rate limit hit, try again shortly.")
            return {"action": "rate_limited", "chat_id": chat_id}
        crisis = crisis_screen(text)
        db.log_event(self.conn, "telegram", "wake", json.dumps(
            {"chat_id": chat_id, "text": text, "crisis_advisory": crisis}))
        flag = " [crisis_advisory]" if crisis else ""
        payload = f'[telegram chat:{chat_id}]{flag} User says: "{text}"'
        delivery = self.injector(payload)
        return {"action": "forwarded", "chat_id": chat_id,
                "crisis_advisory": crisis, "delivery": delivery}
