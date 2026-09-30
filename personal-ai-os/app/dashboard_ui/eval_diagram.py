"""Mermaid source for the Evals page's dedicated architecture diagram.
Every box/edge traces to real code, verified by reading it directly.

Built for the user's ask: a dedicated Evals page covering "arch of eval,
golden datasets we have + synthetic data + eval score + model used for
eval score + types of eval done - llm judge, human in the loop,
deterministic, etc ... feedback from eval score and how it gets tied
back."

Checked first, honestly: this project's own Architecture page diagram
already disclosed the real, central gap this page closes -- evals/ was
"static JSON + .md, no live grading harness." app/evaluation/golden.py's
run_golden_case() (deterministic) and app/evaluation/llm_judge.py's
judge_response() (LLM-as-judge) both existed, real, tested, but had
never been run end-to-end against the real, live Orchestrator over the
real golden dataset until scripts/generate_eval_harness_run.py.
"""

EVAL_DIAGRAM = r"""
flowchart TB
    GOLDEN["evals/golden/basic_routing.json\n(7 real cases, incl. 2 deliberately\nadversarial ones: input, expected_agent,\nexpected_tools, expected_capabilities)"]
    DOMAINGOLDEN["evals/{career,pm,finance,learning,\ncross_domain}/*.json\n(domain-specific synthetic cases,\nfabricated-but-labeled-as-such, per\nthis project's synthetic-data convention)"]
    ADVERSARIAL["evals/adversarial/failure_matrix.md\n(known failure modes: malformed JSON,\ntool hallucination, prompt injection, ...)"]

    GOLDEN --> HARNESS["scripts/generate_eval_harness_run.py\n(the real grading harness --\npreviously did not exist anywhere)"]

    subgraph HARNESS_RUN["One real pass per golden case"]
        direction TB
        ORCH2["Real Orchestrator.handle(case.input)"]
        DET["DETERMINISTIC eval\nrun_golden_case():\nrouted to the right agent?\ncalled the right tool(s)?\n(free, no extra LLM call)"]
        JUDGE["LLM-AS-JUDGE eval\njudge_response(): 1 real structured\nLLM call, 6 scored dimensions\n(correctness, completeness, groundedness,\ncitation_quality, instruction_following, overall)"]
        ORCH2 --> DET
        ORCH2 --> JUDGE
    end
    HARNESS --> ORCH2

    SNAPSHOT["MetricSnapshot\n(app/evaluation/regression.py) --\naggregate scores from this run,\nready for a future regression compare()"]
    DET --> SNAPSHOT
    JUDGE --> SNAPSHOT

    HUMANEVAL["HUMAN-IN-THE-LOOP eval\napp/evaluation/human_eval.py's HumanRating\n(1-5 scale, 6 dimensions) +\njudge_human_correlation() --\nneeds a REAL human's ratings,\nnot fabricatable by this harness"]
    SNAPSHOT -.->|"a real human could rate\nthe same cases, then correlate"| HUMANEVAL

    RESULTS["app/dashboard_ui/eval_harness_run.json\n(committed, real -- pass rate,\njudge scores, real per-call token usage)"]
    SNAPSHOT --> RESULTS

    subgraph FEEDBACK["Feedback tie-back -- Chief of Staff"]
        direction TB
        ERRANALYSIS2["error_analysis.py\n(real trace failures)"]
        EVALHISTORY2["eval_history.json\n(real drift over time)"]
        HARNESSFEED2["harness_feedback.py\nreads RESULTS + error/drift signals,\nproposes ONE evidence-cited\nworkflow suggestion (never auto-applied)"]
        ERRANALYSIS2 --> HARNESSFEED2
        EVALHISTORY2 --> HARNESSFEED2
    end
    RESULTS -.->|"a low eval score is exactly the\nkind of real signal this feeds"| HARNESSFEED2

    FEEDBACKEX["eval_feedback_example.json\n(committed, real -- an actual\nHarnessSuggestion generated from\nthis run's low-scoring case(s))"]
    HARNESSFEED2 --> FEEDBACKEX

    ADVERSARIAL -.->|"documents known failure modes\n(not all yet re-run through HARNESS)"| RESULTS
    DOMAINGOLDEN -.->|"counted live on this page\n(count_cases_by_domain()) --\nnot yet run through HARNESS\n(different input shape per domain)"| RESULTS
"""
