from abc import ABC, abstractmethod

from pydantic import BaseModel


class ToolError(Exception):
    pass


class ArgumentValidationError(ToolError):
    pass


class Tool(ABC):
    name: str
    description: str
    args_schema: type[BaseModel]
    permissions: list[str] = []
    retry_safe: bool = False

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
