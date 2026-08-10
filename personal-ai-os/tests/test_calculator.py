import pytest

from app.tools.base import ArgumentValidationError, ToolError
from app.tools.calculator import CalculatorTool


def test_evaluates_basic_expression():
    tool = CalculatorTool()

    result = tool.call({"expression": "47 * 12"})

    assert result == "564"


def test_supports_parentheses_and_precedence():
    tool = CalculatorTool()

    result = tool.call({"expression": "(2 + 3) * 4"})

    assert result == "20"


def test_invalid_args_raise_argument_validation_error():
    tool = CalculatorTool()

    with pytest.raises(ArgumentValidationError):
        tool.call({"expression": None})


def test_missing_args_raise_argument_validation_error():
    tool = CalculatorTool()

    with pytest.raises(ArgumentValidationError):
        tool.call({})


def test_division_by_zero_raises_tool_error():
    tool = CalculatorTool()

    with pytest.raises(ToolError):
        tool.call({"expression": "1 / 0"})


def test_unsupported_syntax_raises_tool_error():
    tool = CalculatorTool()

    with pytest.raises(ToolError):
        tool.call({"expression": "__import__('os').system('ls')"})
