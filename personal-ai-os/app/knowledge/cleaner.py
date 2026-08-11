import re

_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+\n")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(raw_text: str) -> str:
    """Basic normalization before chunking: strip control characters left over
    from PDF/DOCX extraction, collapse excessive blank lines, trim trailing
    whitespace per line."""
    text = _CONTROL_CHARS.sub("", raw_text)
    text = _TRAILING_WHITESPACE.sub("\n", text)
    text = _MULTIPLE_BLANK_LINES.sub("\n\n", text)
    return text.strip()
