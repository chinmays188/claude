"""These tests exercise the generator's own pure logic (schema extraction,
example shape) without a live Gemini key -- the generator's live run
(scripts/generate_tool_examples.py) is verified manually/in CI separately
since it makes real LLM calls for email_summary/analyze_feedback/analyze_jd/
draft_prd."""

from app.tools.calculator import CalculatorTool
from scripts.generate_tool_examples import _example


def test_example_extracts_real_json_schema():
    calc = CalculatorTool()

    result = _example(calc, {"expression": "1+1"}, "2", "test reason")

    assert result["args_schema"]["required"] == ["expression"]
    assert result["name"] == "calculator"
    assert result["example_request"] == {"expression": "1+1"}
    assert result["example_response"] == "2"
    assert result["when_to_call"] == "test reason"


def test_example_includes_permissions():
    calc = CalculatorTool()

    result = _example(calc, {"expression": "1+1"}, "2", "test reason")

    assert result["permissions"] == calc.permissions
