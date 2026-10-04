"""A real, importable (not inline-script-local) Tool that sleeps, for
testing SandboxedToolExecutor's real timeout-kill path. multiprocessing's
"spawn" context needs the tool class to be importable by the fresh child
interpreter -- a locally-defined class in a script/test function isn't
picklable across spawn, which is itself a real, honest finding about how
this sandbox needs tools to be structured (confirmed while building and
testing this module)."""

import time

from pydantic import BaseModel

from app.tools.base import Tool


class SlowArgs(BaseModel):
    seconds: float = 30.0


class SlowTool(Tool):
    name = "slow_tool"
    description = "Sleeps for the given number of seconds -- used only to test sandbox timeouts."
    args_schema = SlowArgs
    permissions = []
    retry_safe = False

    def run(self, args: SlowArgs) -> str:
        time.sleep(args.seconds)
        return "done"
