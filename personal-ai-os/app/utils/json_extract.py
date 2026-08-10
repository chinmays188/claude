import json


def extract_json(raw: str) -> str:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return raw
    return raw[start : end + 1]


def loads_lenient(raw: str) -> dict:
    """json.loads with a fallback that escapes literal control characters (raw
    newlines, tabs, etc.) found inside string literals. LLMs frequently emit
    unescaped '\\n' inside JSON string values when writing multi-paragraph prose,
    which is invalid per the JSON spec but a common, recoverable failure mode."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_escape_control_chars_in_strings(raw))


def _escape_control_chars_in_strings(raw: str) -> str:
    result = []
    in_string = False
    escaped = False
    for ch in raw:
        if in_string:
            if escaped:
                result.append(ch)
                escaped = False
            elif ch == "\\":
                result.append(ch)
                escaped = True
            elif ch == '"':
                result.append(ch)
                in_string = False
            elif ch == "\n":
                result.append("\\n")
            elif ch == "\t":
                result.append("\\t")
            elif ch == "\r":
                result.append("\\r")
            else:
                result.append(ch)
        else:
            result.append(ch)
            if ch == '"':
                in_string = True
    return "".join(result)
