from app.tools.mcp_tool import _extract_text, _json_schema_to_pydantic


class FakeTextContent:
    def __init__(self, text):
        self.text = text


class FakeImageContent:
    """No .text attribute -- simulates a non-text MCP content block."""


def test_json_schema_to_pydantic_builds_required_and_optional_fields():
    schema = {
        "properties": {
            "repo": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["repo"],
    }
    model_cls = _json_schema_to_pydantic("search_repos", schema)

    instance = model_cls(repo="owner/repo")
    assert instance.repo == "owner/repo"
    assert instance.limit is None


def test_json_schema_to_pydantic_rejects_missing_required_field():
    import pytest
    from pydantic import ValidationError

    schema = {"properties": {"repo": {"type": "string"}}, "required": ["repo"]}
    model_cls = _json_schema_to_pydantic("search_repos", schema)

    with pytest.raises(ValidationError):
        model_cls()


def test_json_schema_to_pydantic_defaults_unknown_type_to_str():
    schema = {"properties": {"payload": {"type": "some_unknown_type"}}, "required": []}
    model_cls = _json_schema_to_pydantic("weird_tool", schema)

    instance = model_cls(payload="anything")
    assert instance.payload == "anything"


def test_extract_text_joins_multiple_text_blocks():
    result = _extract_text([FakeTextContent("first"), FakeTextContent("second")])
    assert result == "first\nsecond"


def test_extract_text_names_non_text_blocks_rather_than_dropping():
    result = _extract_text([FakeTextContent("real text"), FakeImageContent()])
    assert "real text" in result
    assert "FakeImageContent" in result


def test_extract_text_handles_empty_content():
    assert _extract_text([]) == "(empty result)"
