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
