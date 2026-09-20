from pydantic import BaseModel, Field


class PersonalEvalDisplay(BaseModel):
    """Section 36: what the human evaluation interface must show. This is the
    data shape a UI would render, not the UI itself."""

    case_id: str
    user_request: str
    retrieved_memory: list[str] = Field(default_factory=list)
    retrieved_documents: list[str] = Field(default_factory=list)
    agent_response: str
    citations: list[str] = Field(default_factory=list)
    execution_trace: str = ""


class PersonalHumanRating(BaseModel):
    """Section 36's exact 5-field rating, distinct from Phase 1's HumanRating
    (Milestone 11) which uses a different 6-field set — this milestone adds
    Personalization specifically, since that's the new personal-workload
    dimension Section 35 introduces."""

    case_id: str
    correctness: int = Field(ge=1, le=5)
    personalization: int = Field(ge=1, le=5)
    trust: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    citations: int = Field(ge=1, le=5)

    @property
    def average(self) -> float:
        return (self.correctness + self.personalization + self.trust + self.usefulness + self.citations) / 5
