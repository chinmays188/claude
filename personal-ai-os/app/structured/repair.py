import json

from pydantic import BaseModel, ValidationError

from app.providers.base import LLMProvider
from app.utils.json_extract import extract_json, loads_lenient

REPAIR_PROMPT = """Your previous response did not match the required format.

Previous response:
{previous_response}

Validation error:
{error}

Required JSON schema:
{schema}

Respond again with ONLY a valid JSON object matching the schema. No extra text.
"""


class StructuredOutputError(Exception):
    """Raised when valid structured output could not be obtained after all repair attempts."""


class RepairableGenerator:
    """Generates a Pydantic model from an LLM, retrying with a repair prompt on validation failure."""

    def __init__(self, llm: LLMProvider, schema: type[BaseModel], max_repair_attempts: int = 2):
        self._llm = llm
        self._schema = schema
        self._max_repair_attempts = max_repair_attempts

    def generate(self, prompt: str) -> BaseModel:
        raw = self._llm.generate(prompt)

        for attempt in range(self._max_repair_attempts + 1):
            try:
                data = loads_lenient(extract_json(raw))
                return self._schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == self._max_repair_attempts:
                    break
                raw = self._llm.generate(
                    REPAIR_PROMPT.format(
                        previous_response=raw,
                        error=str(exc),
                        schema=json.dumps(self._schema.model_json_schema()),
                    )
                )

        raise StructuredOutputError(
            f"Could not obtain valid {self._schema.__name__} after "
            f"{self._max_repair_attempts} repair attempt(s). Last response: {raw!r}"
        )
