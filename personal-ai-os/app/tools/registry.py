from app.tools.base import Tool, ToolError


class UnknownToolError(ToolError):
    pass


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise UnknownToolError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def descriptions(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema.model_json_schema(),
            }
            for tool in self._tools.values()
        ]
