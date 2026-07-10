def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "\\n")
    text = "".join(ch for ch in text if (ch >= " " and ch != "\x7f") or ch == "\t")
    return text[:4000]
