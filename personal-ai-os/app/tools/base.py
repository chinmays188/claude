from abc import ABC, abstractmethod

from pydantic import BaseModel


class ToolError(Exception):
    pass


class ArgumentValidationError(ToolError):
    pass


class UndoNotSupportedError(ToolError):
    pass


class Tool(ABC):
    name: str
    description: str
    args_schema: type[BaseModel]
    permissions: list[str] = []
    retry_safe: bool = False
    # Found missing while investigating "Human-in-the-Loop AI" (criterion:
    # "understand undo/recovery"): no tool anywhere declared whether its
    # effect could be reversed. Honest default is False -- a tool must
    # explicitly opt in by overriding both this flag AND undo(), not get
    # undo "for free" just because the method exists on the base class.
    undoable: bool = False

    def validate_args(self, raw_args: dict) -> BaseModel:
        try:
            return self.args_schema.model_validate(raw_args)
        except Exception as exc:
            raise ArgumentValidationError(
                f"Invalid arguments for tool '{self.name}': {exc}"
            ) from exc

    @abstractmethod
    def run(self, args: BaseModel) -> str:
        """Execute the tool and return a text result."""

    def call(self, raw_args: dict) -> str:
        args = self.validate_args(raw_args)
        return self.run(args)

    def undo(self, args: BaseModel, result: str) -> str:
        """Reverse this tool's real effect from a previous run() call.
        args/result are exactly what run() was called with and returned.
        Only meaningful when undoable is True -- the base implementation
        always raises, so a tool that doesn't override this can never be
        undone by mistake."""
        raise UndoNotSupportedError(f"Tool '{self.name}' does not support undo.")

    def verify(self, args: BaseModel, result: str) -> tuple[bool, str] | None:
        """Real, tool-specific post-execution check -- found missing while
        investigating 'Human-in-the-Loop AI': PolicyEngine._verify() was a
        bare non-empty-result stub for every tool, with no way for a tool
        to check its OWN real effect (e.g. "did the goal actually get
        written"). Returns None when a tool has no specific check to add
        -- PolicyEngine falls back to its own generic non-empty check in
        that case, so every existing tool keeps working unchanged. Returns
        (verified, note) when a tool DOES have a real check."""
        return None
