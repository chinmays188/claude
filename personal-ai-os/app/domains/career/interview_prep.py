from app.domains.career.models import InterviewStory
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

STORY_PROMPT = """Build a STAR-format interview answer for this request, using
ONLY the candidate's real, retrieved experience excerpts below. You must NEVER
invent a situation, action, or result — every detail must come from the
excerpts. If no excerpt is genuinely relevant, respond with each field
explaining that no matching experience was found rather than fabricating one.

Interview question / request: {request}

Candidate's retrieved experience excerpts (id -> text):
{excerpts}

Respond with ONLY a JSON object:
{{
  "situation": "<grounded in an excerpt>",
  "task": "<grounded in an excerpt>",
  "action": "<grounded in an excerpt>",
  "result": "<grounded in an excerpt>",
  "source_achievement_id": "<the excerpt id this story is built from>"
}}
"""


class NoRelevantExperienceError(Exception):
    pass


def build_interview_story(
    llm: LLMProvider,
    request: str,
    secure_retriever: SecureRetriever,
    requester_id: str,
    requester_tenant_id: str,
    top_k: int = 5,
) -> InterviewStory:
    """Section 11: retrieve relevant experiences -> candidate stories -> best
    story selection -> STAR structure. Raises rather than fabricating a story
    when no real experience was retrieved at all."""
    if not request or not request.strip():
        raise ValueError("Interview request must not be empty.")

    retrieved = secure_retriever.search(
        request, requester_id=requester_id, requester_tenant_id=requester_tenant_id, top_k=top_k
    )
    if not retrieved:
        raise NoRelevantExperienceError(
            "No relevant experience found in the candidate's documents for this request."
        )

    excerpts = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in retrieved)
    generator = RepairableGenerator(llm, InterviewStory)
    prompt = STORY_PROMPT.format(request=request, excerpts=excerpts)
    story = generator.generate(prompt)

    valid_ids = {r.chunk.id for r in retrieved}
    if story.source_achievement_id not in valid_ids:
        raise NoRelevantExperienceError(
            f"Generated story cited source_achievement_id '{story.source_achievement_id}', "
            f"which was not among the retrieved excerpts {sorted(valid_ids)} — likely fabricated."
        )

    return story
