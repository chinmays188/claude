"""Mermaid source for the Context Engineering + Memory-specific
architecture diagram shown on the dashboard's dedicated Context & Memory
page. Every box/edge traces to real code, verified by reading it directly.

Built for the user's ask, after a full context-engineering breakdown
(session memory / user memory / long-term memory, how each is called,
turn/summarization, context window/compression, ordering) surfaced 3 real
gaps and this page's 3 follow-up pieces closed them:
  1. PersonalContextEngine (real 4-factor scoring: relevance/importance/
     freshness/confidence) was never called from anywhere -- now wired
     into app/conversation/context_selection.py, used by every
     ConversationSession turn to genuinely SELECT (not just concatenate)
     which context items earn a place under a real token budget.
  2. ContextBuilder's real compression path (drop lowest-priority whole
     section first) was dead code in production -- demonstrated for real
     here via a live, interactive dashboard slider (pure Python, no LLM
     call) showing an actual section get dropped under a tight budget.
  3. lost_in_middle.py's build_positioned_context() had never been run
     against a real request -- scripts/generate_lost_in_middle_experiment.py
     ran it for real against the live Gemini API at 3 positions (start/
     middle/end) with ~200 real filler chunks, committed as a real,
     honest result (no degradation observed at this scale/model -- a real
     finding, not manufactured to look more dramatic).

Relabeled after the user pointed out the dashboard page conflated two
different decisions under "what to keep" with no demo of "what to
retrieve" at all: RETRIEVER (MemoryRetriever.rank()) is the real
RETRIEVE step -- pulling a few relevant memories out of a much larger
pool by query similarity -- and was always drawn here as feeding INTO
SELECT, but the dashboard page itself never demonstrated RETRIEVER
running against a pool larger than the few items SELECT's demo already
assumed were relevant. SELECT (PersonalContextEngine) and CBUILDER
(ContextBuilder) are both the KEEP decision, at two different
granularities (item-level scoring vs. whole-section dropping) -- never
two different stages. DECAY is FORGET. LIM (lost-in-the-middle) is a
4th, separate concept (context ORDER), deliberately not folded into
retrieve/keep/forget.

Expanded further after the user asked for more granularity: "there are
two main components of memory - content and metadata", declarative vs.
procedural memory, storage architectures (vector/graph/hybrid), how
extraction happens, how conflicting info is handled during
consolidation, and an eval system for memory management. Three of
these were genuine code gaps, not just missing demos, closed in this
batch: (a) MemoryType.PROCEDURE added (every prior type was
declarative -- a fact ABOUT the user; PROCEDURE is the first "knowing
how" rule); (b) MemoryGraphBridge wires GraphStore (real, existed for
decisions/goals) into personal memories via NodeType.MEMORY, enabling
real graph traversal ("what is this memory connected to") that vector
similarity alone can't answer; (c) ConflictResolver uses a real LLM
judgment to tell a genuine contradiction apart from a mere
restatement, then marks the old memory SUPERSEDED (never deleted) --
closing the real gap where is_semantic_duplicate() only ever silently
dropped new, possibly-correcting information. A new memory_management_
eval.py golden suite (RETRIEVE/FORGET/conflict-resolution accuracy, all
100% on real hand-crafted cases) closes the last-named gap. These new
pieces are shown in new "0a"-"0f" sections ABOVE the diagram on the
dashboard page, deliberately not redrawn into this flowchart -- adding
6 more subsystems here would make an already-dense diagram unreadable;
the page's own section captions carry the explanation instead.
"""

CONTEXT_MEMORY_DIAGRAM = r"""
flowchart TB
    USERINPUT["User request\n(via ConversationSession.handle())"]

    subgraph SESSION["ConversationSession -- real per-session state"]
        direction TB
        TURNS["Real turn history\n(ConversationTurn list)"]
        BUDGETCHECK{"History over\nhistory_token_budget?"}
        SUMMARIZE["1 real LLM call:\nsummarize older turns"]
        TURNS --> BUDGETCHECK
        BUDGETCHECK -->|yes| SUMMARIZE --> TURNS
    end
    USERINPUT --> SESSION

    subgraph MEMORY["RETRIEVE -- pull a few relevant memories out of ALL stored memories"]
        direction TB
        MEMSTORE2["PersistentMemoryStore\n(SQLite) -- the full real pool"]
        RETRIEVER["MemoryRetriever.rank(query, candidates, top_k)\nreal 4-factor score:\nsimilarity/recency/importance/confirmed"]
        MEMSTORE2 --> RETRIEVER
    end
    SESSION --> RETRIEVER

    subgraph SELECT["KEEP (item-level) -- PersonalContextEngine, real selection not just concatenation"]
        direction TB
        ITEMS["Real ContextItems built from:\nrunning summary, recent turns,\nranked memories"]
        SCORE["score() = w_relevance*relevance +\nw_importance*importance +\nw_freshness*freshness + w_confidence*confidence"]
        FILTER{"Fits under\ncontext_token_budget?"}
        INCLUDE["Included in prompt"]
        EXCLUDE["Excluded\n(inspectable: last_excluded_context)"]
        ITEMS --> SCORE --> FILTER
        FILTER -->|"yes, greedily\nby score"| INCLUDE
        FILTER -->|no| EXCLUDE
    end
    SESSION --> ITEMS
    RETRIEVER --> ITEMS

    ORDERED["Ordered, rendered context text\n(summary -> history -> memory)\n+ 'Current request: ...'"]
    INCLUDE --> ORDERED
    ORDERED -.->|"one plain string --\nOrchestrator.handle() signature\nunchanged"| ORCH2["Orchestrator"]

    subgraph WRITE["Write side -- real gate, never silent"]
        direction TB
        POLICY["MemoryWritePolicy\nclassify -> importance threshold ->\nexact duplicate check -> real semantic\nduplicate check (optional embedding_model) ->\napproval gate"]
        LOWIMP["Low importance:\nwritten immediately"]
        HIGHIMP["High importance:\nqueued for real human approval\n(never auto-written)"]
        POLICY --> LOWIMP
        POLICY --> HIGHIMP
    end
    ORCH2 -.->|"after every turn"| POLICY
    LOWIMP --> MEMSTORE2
    HIGHIMP -->|"approved"| MEMSTORE2

    subgraph DECAY["FORGET -- memory decay, found missing, closed while investigating 'AI Memory'"]
        direction TB
        DECAYCHECK{"user_confirmed?"}
        DECAYCHECK -->|"yes -- human\nalready validated it"| NODECAY["confidence unchanged"]
        DECAYCHECK -->|no| HALFLIFE["Real half-life decay\n(same pattern MemoryRetriever\nalready uses for recency)"]
        HALFLIFE --> REVIEWCHECK{"decayed confidence <\nreview_threshold?"}
        REVIEWCHECK -->|yes| FLAGGED["Flagged for human review --\nNEVER auto-deleted"]
    end
    MEMSTORE2 -.->|"apply_decay() --\nupdate_confidence() only,\nnever touches updated_at"| DECAY

    subgraph CBUILDER["KEEP (section-level) -- ContextBuilder, same decision as SELECT above, coarser granularity"]
        direction TB
        SECTIONS["Named sections, fixed order:\nsystem/memory/retrieved_context/\ntool_results/history/user"]
        OVERBUDGET{"Over max_tokens?"}
        DROP["Drop LOWEST-priority\nWHOLE section, repeat"]
        SECTIONS --> OVERBUDGET
        OVERBUDGET -->|yes| DROP --> OVERBUDGET
    end

    subgraph LIM["Lost-in-the-middle -- real experiment, run live against Gemini"]
        direction TB
        POSITION["build_positioned_context():\ncritical fact at start/middle/end\nof ~200 real filler chunks"]
        REALCALL["Real Gemini call per position\n(pre-generated once, committed --\nno live LLM call on this page)"]
        JUDGE["Deterministic check:\ndoes the real answer contain\nthe fact's specific value?"]
        POSITION --> REALCALL --> JUDGE
    end

    PAGE["Dashboard: Context & Memory page\n(this diagram + all 3 live/committed experiments)"]
    SELECT -.-> PAGE
    CBUILDER -.-> PAGE
    LIM -.-> PAGE
"""
