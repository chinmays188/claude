from pydantic import BaseModel

from app.providers.base import LLMProvider


class AgentResponse(BaseModel):
    input: str
    output: str
    model: str
    agent: str
    tool_calls: list[str] = []
    stop_reason: str = "task_completed"
    # Set only when stop_reason == "approval_pending" (ToolAgent + a real
    # PolicyEngine wired in -- app/actions/policy_engine.py's
    # ApprovalPending). The real action_id a human must approve/reject via
    # PolicyEngine.resume_after_approval() to let this request continue.
    pending_action_id: str | None = None


class Agent:
    name: str = "agent"
    system_prompt: str = ""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def run(self, text: str) -> AgentResponse:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        prompt = f"{self.system_prompt}\n\n{text}" if self.system_prompt else text
        output = self._llm.generate(prompt)
        return AgentResponse(
            input=text,
            output=output,
            model=self._llm.model_name,
            agent=self.name,
        )
