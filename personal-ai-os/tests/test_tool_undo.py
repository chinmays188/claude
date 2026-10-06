import pytest
from pydantic import BaseModel

from app.tools.base import Tool, UndoNotSupportedError


class _Args(BaseModel):
    x: int


class _PlainTool(Tool):
    name = "plain"
    description = "does nothing undoable"
    args_schema = _Args

    def run(self, args: _Args) -> str:
        return str(args.x)


def test_tool_defaults_to_not_undoable():
    assert _PlainTool.undoable is False


def test_undo_raises_by_default():
    tool = _PlainTool()

    with pytest.raises(UndoNotSupportedError):
        tool.undo(_Args(x=1), "1")
