def redact(text: str, secret) -> str:
    """Replace every occurrence of secret in text with REDACTED.
    No-op when secret is falsy (no token configured)."""
    if not secret:
        return text
    return text.replace(secret, "REDACTED")


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "\\n")
    text = "".join(ch for ch in text if (ch >= " " and ch != "\x7f") or ch == "\t")
    return text[:4000]
