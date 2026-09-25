from app.agents.orchestrator import Orchestrator
from app.evaluation.golden import GoldenCase, pass_rate, run_golden_case, run_golden_set
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_passing_case_research_agent():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        ]
    )
    orchestrator = Orchestrator(llm)
    case = GoldenCase(id="r1", input="Explain RAG.", expected_agent="research_agent")

    result = run_golden_case(orchestrator, case)

    assert result.passed
    assert result.actual_agent == "research_agent"


def test_failing_case_wrong_agent():
    llm = ScriptedProvider(['{"domains": [], "confidence": 0.9}', '{"task_type": "planning", "confidence": 0.9}', "a plan"])
    orchestrator = Orchestrator(llm)
    case = GoldenCase(id="r1", input="Explain RAG.", expected_agent="research_agent")

    result = run_golden_case(orchestrator, case)

    assert not result.passed
    assert "planner_agent" in result.reason


def test_expects_clarification_and_gets_it():
    llm = ScriptedProvider(['{"domains": [], "confidence": 0.9}', '{"task_type": "unclear", "confidence": 0.9}'])
    orchestrator = Orchestrator(llm)
    case = GoldenCase(id="amb1", input="Do something useful.", expected_agent=None)

    result = run_golden_case(orchestrator, case)

    assert result.passed


def test_expects_clarification_but_gets_an_agent():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "some answer"}',
        ]
    )
    orchestrator = Orchestrator(llm)
    case = GoldenCase(id="amb1", input="Explain RAG.", expected_agent=None)

    result = run_golden_case(orchestrator, case)

    assert not result.passed


def test_missing_expected_tool_fails():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "564"}',
        ]
    )
    orchestrator = Orchestrator(llm)
    case = GoldenCase(id="r2", input="What is 47*12?", expected_agent="research_agent", expected_tools=["calculator"])

    result = run_golden_case(orchestrator, case)

    assert not result.passed
    assert "calculator" in result.reason


def test_pass_rate_computation():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "answer"}',
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "planning", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "answer"}',
        ]
    )
    orchestrator = Orchestrator(llm)
    cases = [
        GoldenCase(id="r1", input="Explain RAG.", expected_agent="research_agent"),
        GoldenCase(id="r2", input="Explain X.", expected_agent="research_agent"),  # will get planner -> fail
    ]

    results = run_golden_set(orchestrator, cases)

    assert pass_rate(results) == 0.5


def test_pass_rate_empty_results():
    assert pass_rate([]) == 0.0
