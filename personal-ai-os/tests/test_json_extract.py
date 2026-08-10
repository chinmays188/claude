import json

import pytest

from app.utils.json_extract import extract_json, loads_lenient


def test_extract_json_strips_surrounding_text():
    raw = "Sure, here you go:\n{\"a\": 1}\nHope that helps."

    assert extract_json(raw) == '{"a": 1}'


def test_extract_json_returns_raw_if_no_braces_found():
    assert extract_json("no json here") == "no json here"


def test_loads_lenient_parses_valid_json_directly():
    result = loads_lenient('{"a": 1}')

    assert result == {"a": 1}


def test_loads_lenient_fixes_literal_newline_in_string_value():
    raw = '{"answer": "line one\nline two"}'

    result = loads_lenient(raw)

    assert result["answer"] == "line one\nline two"


def test_loads_lenient_fixes_literal_tab_and_carriage_return():
    raw = '{"answer": "a\tb\rc"}'

    result = loads_lenient(raw)

    assert result["answer"] == "a\tb\rc"


def test_loads_lenient_preserves_already_escaped_sequences():
    raw = json.dumps({"answer": "already\nescaped"})

    result = loads_lenient(raw)

    assert result["answer"] == "already\nescaped"


def test_loads_lenient_raises_on_truly_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        loads_lenient("not json at all")
