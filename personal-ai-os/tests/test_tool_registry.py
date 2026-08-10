import pytest

from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry, UnknownToolError


def test_get_known_tool():
    registry = ToolRegistry([CalculatorTool()])

    tool = registry.get("calculator")

    assert tool.name == "calculator"


def test_get_unknown_tool_raises():
    registry = ToolRegistry([CalculatorTool()])

    with pytest.raises(UnknownToolError):
        registry.get("send_email")


def test_descriptions_include_schema():
    registry = ToolRegistry([CalculatorTool()])

    descriptions = registry.descriptions()

    assert descriptions[0]["name"] == "calculator"
    assert "properties" in descriptions[0]["args_schema"]
