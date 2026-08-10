import pytest
from pydantic import BaseModel

from app.safety.permissions import PermissionChecker, PermissionDeniedError
from app.tools.base import Tool


class NoArgs(BaseModel):
    pass


class ReadOnlyTool(Tool):
    name = "read_tool"
    description = "reads something"
    args_schema = NoArgs
    permissions = ["read:web"]

    def run(self, args: NoArgs) -> str:
        return "read result"


class EmailTool(Tool):
    name = "send_email"
    description = "sends an email"
    args_schema = NoArgs
    permissions = ["write:email"]

    def run(self, args: NoArgs) -> str:
        return "sent"


def test_call_succeeds_when_permission_granted():
    checker = PermissionChecker(granted_permissions={"read:web"})

    result = checker.call(ReadOnlyTool(), {})

    assert result == "read result"


def test_call_denied_when_permission_missing():
    checker = PermissionChecker(granted_permissions={"read:web"})

    with pytest.raises(PermissionDeniedError):
        checker.call(EmailTool(), {})


def test_check_does_not_raise_when_permission_present():
    checker = PermissionChecker(granted_permissions={"read:web", "write:email"})

    checker.check(ReadOnlyTool())  # should not raise


def test_tool_with_no_permissions_always_allowed():
    class OpenTool(Tool):
        name = "open"
        description = "no permission required"
        args_schema = NoArgs
        permissions = []

        def run(self, args):
            return "ok"

    checker = PermissionChecker(granted_permissions=set())

    assert checker.call(OpenTool(), {}) == "ok"
