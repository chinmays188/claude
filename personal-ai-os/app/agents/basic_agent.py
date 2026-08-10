from pydantic import BaseModel

from app.providers.base import LLMProvider


class AgentResponse(BaseModel):
    input: str
    output: str
    model: str


class BasicAgent:
    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def run(self, text: str) -> AgentResponse:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        output = self._llm.generate(text)
        return AgentResponse(
            input=text,
            output=output,
            model=self._llm.model_name,
        )
