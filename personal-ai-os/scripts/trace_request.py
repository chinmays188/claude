"""Interactive trace CLI: run a real request through the real router + tool
agent, using the live Gemini API, and print every step in detail.

Not part of the dashboard on purpose (see specs/dashboard_ui.md's non-goals
— the dashboard never makes live LLM calls). This script is the actual
place to answer "how does the router route, what tool gets called, what's
the input/output" for a real, live query. Requires GEMINI_API_KEY to be set.

Usage:
    PYTHONPATH=. python scripts/trace_request.py "Should I learn Kubernetes for my career?"

    # Also run the domain's eval/regression suite against the routed
    # domain's golden cases after tracing the live request:
    PYTHONPATH=. python scripts/trace_request.py "..." --with-eval
"""

import argparse
import json
import sys

from app.config import require_gemini_key
from app.domains.router import Domain, DomainRouter, DomainRoutingError
from app.providers.gemini_provider import GeminiProvider
from app.agents.tool_agent import ToolAgent
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from app.evaluation.domain_golden import load_domain_cases

# Only tools that are safe to actually invoke live, with no external
# credentials/side effects, are wired in here (calendar/email/github tools
# need real integration credentials this script doesn't assume you have).
DEFAULT_TOOLS = [CalculatorTool()]

DOMAIN_EVAL_DIR = {
    Domain.CAREER: "career",
    Domain.PM: "pm",
    Domain.FINANCE: "finance",
    Domain.LEARNING: "learning",
}


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def trace(text: str, with_eval: bool) -> None:
    require_gemini_key()
    llm = GeminiProvider()

    _print_header("1. ROUTING")
    router = DomainRouter(llm)
    try:
        classification = router.route(text)
    except DomainRoutingError as exc:
        print(f"Routing FAILED: {exc}")
        sys.exit(1)

    print(f"Input:      {text}")
    print(f"Model:      {llm.model_name}")
    print(f"Domain(s):  {[d.value for d in classification.domains] or 'UNCLEAR'}")
    print(f"Confidence: {classification.confidence:.2f}")
    print(f"Cross-domain: {classification.is_cross_domain}")

    if classification.is_unclear:
        print("\nRequest was classified UNCLEAR (below confidence threshold) — "
              "stopping here, no agent/tool run for an unrouted request.")
        return

    _print_header("2. AGENT + TOOL CALLS")
    tools = ToolRegistry(DEFAULT_TOOLS)
    print(f"Registered tools: {[t.name for t in DEFAULT_TOOLS]}")

    agent = ToolAgent(llm, tools)
    response = agent.run(text)

    print(f"\nAgent:       {agent.name} ({type(agent).__name__})")
    print(f"Tool calls:  {response.tool_calls or '(none — answered directly)'}")
    print(f"Stop reason: {response.stop_reason}")
    print(f"\n--- Output ---\n{response.output}")

    if with_eval:
        for domain in classification.domains:
            eval_dir = DOMAIN_EVAL_DIR.get(domain)
            if not eval_dir:
                continue
            _print_header(f"3. GOLDEN CASES — {domain.value}")
            # There is no generic "run a golden case through the LLM and
            # grade it" harness in this codebase (checked: app/evaluation/
            # domain_golden.py only loads/counts cases). Real grading is
            # per-workflow, e.g. app/evaluation/career_eval.py's checks run
            # against a specific already-produced JdAnalysisResult/
            # InterviewStory, and the full regression suite runs via
            # pytest, not from a live single request. This section shows
            # what's real and points at where the rest actually lives.
            cases = load_domain_cases(eval_dir)
            print(f"Golden cases on disk for '{eval_dir}': {len(cases)}")
            for case in cases[:5]:
                print(f"  - [{case.category or 'uncategorized'}] {case.id}")
            if len(cases) > 5:
                print(f"  ... and {len(cases) - 5} more")
            print(
                "\nFull eval/regression suite (per-workflow grading + version-over-version "
                "regression comparison) runs via pytest, not per live request:\n"
                f"    PYTHONPATH=. pytest tests/ -k {eval_dir} -v"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", help="The request to route and run, in quotes.")
    parser.add_argument(
        "--with-eval", action="store_true",
        help="Also run the routed domain's golden-case eval suite (extra live LLM calls).",
    )
    args = parser.parse_args()
    trace(args.text, args.with_eval)


if __name__ == "__main__":
    main()
