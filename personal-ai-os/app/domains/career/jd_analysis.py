from app.domains.career.models import JdAnalysisResult, JdRequirements
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

PARSE_JD_PROMPT = """Extract structured requirements from this job description.

Job description:
{jd_text}

Respond with ONLY a JSON object:
{{
  "role_title": "<title>",
  "required_skills": ["..."],
  "preferred_skills": ["..."],
  "responsibilities": ["..."],
  "seniority_signal": "<e.g. senior, lead, individual contributor>"
}}
"""

GAP_ANALYSIS_PROMPT = """You are analyzing how well a candidate fits a job, based
ONLY on the requirements below and the candidate's own resume/achievement
excerpts retrieved from their real documents. Do not invent experience, skills,
or achievements that are not present in the retrieved excerpts.

Job requirements:
{requirements}

Candidate's retrieved resume/achievement excerpts:
{candidate_context}

Respond with ONLY a JSON object matching this schema:
{{
  "overall_fit": <float 0.0-1.0>,
  "technical_fit": <float 0.0-1.0>,
  "ai_fit": <float 0.0-1.0>,
  "pm_fit": <float 0.0-1.0>,
  "domain_fit": <float 0.0-1.0>,
  "leadership_fit": <float 0.0-1.0>,
  "major_gaps": ["<gap grounded in a missing requirement>"],
  "recommended_resume_changes": ["<change grounded in the candidate's real excerpts>"],
  "interview_risks": ["<risk grounded in a gap between requirements and excerpts>"]
}}
"""


def parse_jd(llm: LLMProvider, jd_text: str) -> JdRequirements:
    """Section 9: JD Parser -> Requirements extraction -> Skill mapping."""
    if not jd_text or not jd_text.strip():
        raise ValueError("Job description text must not be empty.")
    generator = RepairableGenerator(llm, JdRequirements)
    return generator.generate(PARSE_JD_PROMPT.format(jd_text=jd_text))


def analyze_jd(
    llm: LLMProvider,
    jd_text: str,
    secure_retriever: SecureRetriever,
    requester_id: str,
    requester_tenant_id: str,
    top_k: int = 8,
) -> JdAnalysisResult:
    """Section 9's full pipeline: JD -> parse -> resume/achievement retrieval
    (via SecureRetriever, same access-control guarantee as any other personal
    document) -> gap analysis -> Section 9's exact output fields."""
    requirements = parse_jd(llm, jd_text)

    query = f"{requirements.role_title} " + " ".join(requirements.required_skills)
    retrieved = secure_retriever.search(
        query, requester_id=requester_id, requester_tenant_id=requester_tenant_id, top_k=top_k
    )
    candidate_context = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in retrieved)
    if not candidate_context:
        candidate_context = "(no resume or achievement documents found for this candidate)"

    generator = RepairableGenerator(llm, JdAnalysisResult)
    prompt = GAP_ANALYSIS_PROMPT.format(
        requirements=requirements.model_dump_json(), candidate_context=candidate_context
    )
    return generator.generate(prompt)
