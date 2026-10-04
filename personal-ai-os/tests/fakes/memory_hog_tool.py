"""A real, importable Tool that deliberately allocates far more memory
than any sane sandbox limit -- for testing SandboxedToolExecutor's real
OS-enforced memory ceiling (resource.RLIMIT_AS)."""

from pydantic import BaseModel

from app.tools.base import Tool


class MemoryHogArgs(BaseModel):
    pass


class MemoryHogTool(Tool):
    name = "memory_hog_tool"
    description = "Allocates a large amount of memory -- used only to test sandbox memory limits."
    args_schema = MemoryHogArgs
    permissions = []
    retry_safe = False

    def run(self, args: MemoryHogArgs) -> str:
        # Deliberately allocate well past any real sandbox limit this
        # project uses (largest default is 256MB) -- a real allocation,
        # not a simulated one, so the OS itself has to kill this.
        data = bytearray(2 * 1024 * 1024 * 1024)  # 2GB
        return str(len(data))
