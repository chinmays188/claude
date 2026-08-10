from app.tools.base import Tool, ToolError


class PermissionDeniedError(ToolError):
    pass


class PermissionChecker:
    """Enforces which permission scopes a given caller/session may use, per
    Section 54. Runtime-enforced, not just declared on the Tool — a tool listing
    `permissions=["write:email"]` does not mean every caller may invoke it."""

    def __init__(self, granted_permissions: set[str]):
        self._granted = granted_permissions

    def check(self, tool: Tool) -> None:
        missing = set(tool.permissions) - self._granted
        if missing:
            raise PermissionDeniedError(
                f"Tool '{tool.name}' requires permission(s) {sorted(missing)}, "
                f"which are not granted to this caller."
            )

    def call(self, tool: Tool, raw_args: dict) -> str:
        self.check(tool)
        return tool.call(raw_args)
