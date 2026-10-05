"""Mermaid source for the AI Product Strategy page's dedicated decision
framework diagram. Every box/edge traces to real code
(app/evaluation/ai_product_decision_framework.py), verified by reading
it directly.

Built for the user's ask: "lets check the AI product strategy, build
this decision framework as we go along ... we have already taken lot of
decisions in this project."
"""

DECISION_FRAMEWORK_DIAGRAM = r"""
flowchart TB
    START["A real product need"]

    Q1{"Can this be solved\nwith fixed rules?"}
    START --> Q1
    Q1 -->|yes| T1["DETERMINISTIC LOGIC\n(cheapest, most auditable --\nno learning needed at all)"]

    Q2{"Enough labeled data for\ntraditional ML, AND no\nnatural-language need?"}
    Q1 -->|no| Q2
    Q2 -->|yes| T2["TRADITIONAL ML\n(classification/regression --\ncheaper + more interpretable\nthan an LLM for this shape)"]

    Q3{"Needs natural language\nunderstanding/generation?"}
    Q2 -->|no| Q3
    Q3 -->|no| ERR["No tier matches below LLM --\nneeds a more specific diagnosis\n(ValueError, not a silent guess)"]

    Q4{"Needs grounding in real,\nretrievable knowledge?"}
    Q3 -->|yes| Q4
    Q4 -->|no, and no real\nactions needed| T3["SINGLE LLM CALL\n(the model's own training\nknowledge/reasoning is enough)"]

    Q5{"Needs to take real\nactions, not just answer?"}
    Q4 -->|"yes, but no real\nactions needed"| T4["RAG\n(grounded answers, no actions)"]
    Q4 -->|no| Q5
    Q3 -.->|"(also leads here if\ngrounding not needed)"| Q5

    Q6{"Needs multiple distinct\nkinds of work coordinated\n(research + analysis + planning)?"}
    Q5 -->|yes| Q6

    Q7{"Is the action\nconsequential or\nhard to reverse?"}
    Q6 -->|yes| Q7
    Q7 -->|yes| T7["HUMAN APPROVAL REQUIRED\n(applies ON TOP of multi-agent\ncoordination, not instead of it)"]
    Q7 -->|no| T6["MULTI-AGENT\n(genuinely distinct roles,\ncoordinated together)"]

    Q6 -->|no| Q8{"Is the action\nconsequential or\nhard to reverse?"}
    Q8 -->|yes| T7
    Q8 -->|no| Q9{"Needs ZERO human\nin the loop?"}
    Q9 -->|yes| T9["AUTONOMOUS EXECUTION\n(low-risk/reversible,\ngenuinely no human needed)"]
    Q9 -->|no| T5["AGENT / TOOL CALLING\n(a real decision loop with\nreal tool access)"]

    REALLOG["app/evaluation/ai_product_decision_log.py --\n~12 REAL decisions this project actually made,\neach citing its real commit/spec source"]
    T1 -.-> REALLOG
    T2 -.-> REALLOG
    T3 -.-> REALLOG
    T4 -.-> REALLOG
    T5 -.-> REALLOG
    T6 -.-> REALLOG
    T7 -.-> REALLOG
    T9 -.-> REALLOG
"""
