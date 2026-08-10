# PM Takeaways

Consolidated "what should I remember about this as a PM" notes from walkthroughs
of code/projects. Domain knowledge, not procedural steps — organized by project,
newest entries at the top of each project's section.

---

## personal-ai-os

Source: file-by-file walkthrough of `Project/personal-ai-os/`, started 2026-08-10.
Spec: `Project/Personal AI Operating System.md`.

### app/agents/

- **base.py** — Defines the shared contract every agent returns (`AgentResponse`).
  PM lesson: when multiple things need to behave consistently, define the shared
  contract once rather than letting each one drift independently.
- **basic_agent.py** — The Milestone 1 "walking skeleton" — smallest possible working
  version, built before any complexity was added. PM lesson: ship the thinnest
  possible slice first to prove the pipes connect, then layer complexity on top.
- **research_agent.py / analyst_agent.py / planner_agent.py** — Each is just a name +
  a system prompt. This is the actual prompt-engineering surface of the product —
  editing agent behavior means editing a `system_prompt` string, not code logic.
  PM lesson: this is the one part of the codebase a non-engineer can read and reason
  about directly — it's literally "what persona/instructions does this agent have."
- **tool_agent.py** — The decide→act loop: agent asks "call a tool or answer?",
  executes, repeats, but bounded by a budget (max turns/tool calls/time). On budget
  exhaustion it returns an honest "couldn't fully finish" message instead of pretending
  success. PM lesson: this is the guardrail against runaway cost and bad UX — the
  equivalent of preventing a support bot from looping forever and leaving a customer
  waiting. Worth remembering as a pattern for any agentic bot: always define what
  "stop trying" looks like, and make that failure state visible to the user, not silent.
- **orchestrator.py** — The traffic controller: classifies intent, routes to the right
  agent, and explicitly asks for clarification rather than guessing when unsure.
  PM lesson: this maps directly to intent classification in a support/voice bot
  (e.g. "refund request" vs "booking change" vs "complaint"). The "ask, don't guess"
  behavior is a deliberate product tradeoff — a wrong guess is worse than one
  clarifying question, and this is the file where that tradeoff is actually encoded.

### app/providers/

- **base.py** — Defines `LLMProvider`, a minimal interface (`generate()`, `model_name`)
  that hides which vendor is actually being called. No other file is allowed to know
  it's talking to Gemini specifically. PM lesson: this is vendor lock-in insurance —
  swapping/adding a model provider means changing one file, not rewriting the product.
  Same principle applies to a voice bot's STT/TTS vendor choice.
- **gemini_provider.py** — The only file that touches Google's actual SDK. PM lesson:
  this is the single point of change if Gemini's API/pricing/models change.
- **fake_provider.py** — A stand-in returning a fixed made-up response instead of
  calling a real LLM. PM lesson: this is how 100+ test scenarios ran without spending
  money or waiting on network calls — "112 tests passed" does not mean 112 real API
  calls happened. Good engineering tests behavior without needing the real, expensive,
  slow dependency every time.
- **fallback_provider.py** — Wraps multiple providers in priority order; if the
  primary fails, tries the next and *records* that a fallback occurred (never silent).
  PM lesson: this is a degraded-mode strategy encoded in code — the pattern that would
  let a live voice bot fail over to a backup model during a Gemini outage, while still
  making that failover visible/loggable rather than invisible.

### app/tools/

- **base.py** — Defines `Tool`, the base contract (name, description, input schema,
  permissions, retry safety). Arguments are validated against a Pydantic schema before
  a tool ever runs — bad input fails loudly (`ArgumentValidationError`) instead of
  crashing or silently misbehaving. PM lesson: this is input validation at the
  boundary, same discipline as a form on the booking site — a malformed request
  (e.g. a bad booking ID) should be rejected cleanly, not cause a wrong action.
- **calculator.py** — Evaluates math expressions using Python's `ast` parser locked
  down to only `+ - * / **`, deliberately not using `eval()` (which would allow
  arbitrary code execution). PM lesson: never let an LLM's output run arbitrary code —
  any tool that "executes something the AI decided" needs a locked-down allowlist of
  exactly what's permitted. This file is the reference example of that pattern here.
- **registry.py** — `ToolRegistry` is the single source of truth for which tools
  actually exist; a tool name the LLM invents but that isn't registered is rejected,
  never executed (addresses "tool hallucination", a named production failure mode in
  the spec). PM lesson: this is the permission boundary — the LLM can only propose
  actions from an approved list, never invent new capabilities on the fly. This is
  what prevents a "creative" AI response from accidentally triggering a real action
  (refund, email) that was never actually wired up or authorized.
- **retrieval_tool.py** — Wraps vector search as a callable tool; results come back
  tagged with a citation (chunk id + source + score) so answers can be traced to their
  source. PM lesson: this is the difference between an LLM guessing and an LLM citing
  evidence. For a post-sales bot, this is the pattern that lets it answer policy
  questions by pulling from real docs and showing where the answer came from, rather
  than the model's possibly-outdated memorized idea of the policy.

### app/routing/

- **classifier.py** — Sends user text to the LLM asking it to classify intent
  (research/analysis/planning) with a confidence score; below a threshold (default
  0.5) it's treated as unclear rather than routed. PM lesson: this confidence
  threshold is a real, tunable product lever — too low and the bot confidently routes
  ambiguous requests wrong; too high and it asks for clarification too often. This is
  the exact kind of number a PM should have visibility into and control over.

### app/structured/

- **repair.py** — `RepairableGenerator` asks the LLM for structured JSON; if
  validation fails, it sends the LLM its own broken output + the exact error + the
  expected schema and asks it to retry (max 2 attempts, then gives up loudly rather
  than pretending success). PM lesson: this is self-healing with a limit — we hit this
  exact failure live (Gemini returning prose with literal line breaks inside a JSON
  field) and this mechanism recovered automatically. The "give up after N tries" part
  matters as much as the retry itself: retrying forever on a truly broken response
  just burns money and time for nothing.

### app/guardrails/

- **budgets.py** — `AgentBudget` defines hard limits (max turns, max tool calls, max
  tokens, max retries, timeout); `BudgetTracker` counts usage and raises the moment
  any limit is crossed. PM lesson: this is the literal answer to "what if the bot gets
  into a weird loop and burns money on one session" — these five numbers are the
  actual dashboard knobs for tuning cost vs. thoroughness per request.
- **stop_conditions.py** — A defined, trackable enum of why an agent stopped
  (`task_completed`, `max_turns_reached`, `max_tool_calls_reached`, `timeout`,
  `safety_blocked`) attached to every response. PM lesson: this is observability for
  free — if 15% of sessions end in `max_turns_reached`, that's an immediate,
  actionable signal the bot is struggling with something, instead of an invisible
  failure mode you'd only notice as "some answers looked incomplete."

### app/retrieval/

- **document.py** — `Document`/`Chunk` models carrying freshness metadata (source,
  created/updated dates, version) on every stored piece of content, per the spec's
  freshness requirement. PM lesson: this is what makes "is this info still accurate?"
  answerable later — critical for anything like refund policies or fare rules that
  change over time, so newer content can eventually be preferred over stale content.
- **chunking.py** — Splits documents into overlapping word-count chunks
  (`chunk_size`/`overlap` are tunable). PM lesson: chunk size is a real tradeoff, not
  a detail to ignore — too small loses context (splitting "refund policy for
  international flights" away from "is 7 days"), too large hurts search precision and
  wastes tokens/cost. Worth testing against real documents, not a set-once setting.
- **embeddings.py** — Wraps a free local model (`all-MiniLM-L6-v2`) turning text into
  vectors where similar *meanings* end up numerically close, even with no shared
  words. PM lesson: this is semantic vs. keyword search made concrete — it's why
  "refund for late flight" can match a doc saying "compensation for delayed
  departures." This is the core capability that makes RAG useful over plain keyword
  search on a knowledge base.
- **vector_search.py** — Wraps FAISS (free, local, open-source) to quickly find the
  closest stored vectors to a query vector. PM lesson: this is the actual search
  engine behind the knowledge base — genuinely production-viable, not just a
  prototype toy, and has no per-query API cost.
- **ingestion.py** — Ties chunking + embedding + storing into one pipeline call. PM
  lesson: this is the "add a new document to the knowledge base" entry point — e.g.
  what would run if a PM uploaded a new refund policy PDF.
- **keyword_search.py** — Implements BM25 (classic keyword-ranking, pre-neural-search
  era) to catch exact matches — booking references, product codes — that semantic
  search alone can miss. PM lesson: semantic and keyword search fail in opposite
  ways; this is the safety net for exact-match queries.
- **hybrid_search.py** — Runs both semantic and keyword search, merges results via
  reciprocal rank fusion so a chunk ranking highly in *both* gets boosted, without
  needing to compare their incompatible scoring scales directly. PM lesson: this is
  the "best of both worlds" strategy and generally the production-grade approach real
  RAG systems use, not either method alone.
- **reranker.py** — Uses a slower but more accurate cross-encoder model to re-score
  and reorder the top ~20 initial candidates down to the final top 5. PM lesson: an
  explicit quality-vs-speed tradeoff — retrieve broadly and cheaply first, then spend
  more compute narrowing to the best few. Worth watching as a lever: helps quality,
  costs latency, so weigh it differently for voice (fast expected) vs. text.

### app/evaluation/

- **retrieval_eval.py** — Computes recall (did we find the relevant chunks that
  exist?) and precision (of what we found, how much was relevant?) against a labeled
  test case, independent of whether the final answer "looks good." PM lesson: this is
  how you'd prove with numbers that a change (e.g. chunk size 200→500) actually
  helped or hurt, rather than relying on gut feel — foundation of any real
  "did this improve things" conversation.
- **grounding_eval.py** — Uses a second LLM as a judge to score what fraction of an
  answer's claims are actually backed by the retrieved evidence, and verifies every
  citation points to a real, retrieved chunk (catching fabricated citations). PM
  lesson: this is a hallucination detector for cited answers — directly relevant for
  a compliance-sensitive domain (refunds/policies), where an answer that *looks*
  well-sourced but cites the wrong policy or misstates it is exactly the failure this
  would catch before it reaches a customer.
- **golden.py** — Runs labeled test cases (input + expected agent + expected tools)
  against the live orchestrator; failures always name expected-vs-actual, never a
  bare pass/fail. PM lesson: this is a regression safety net for prompt/routing
  changes — before shipping a tweaked system prompt, you'd run the golden set and
  know immediately if it broke a previously-working case, instead of finding out
  from a customer complaint.
- **regression.py** — Compares two metric snapshots (e.g. version 0.4 vs 0.5) and
  flags a regression on ANY metric that dropped, even if another metric improved in
  the same comparison. PM lesson: this stops the trap of "quality went down but we
  shipped it because latency got better" — a genuine product discipline, not just a
  testing detail. One improving number should never be allowed to silently excuse
  another one getting worse.
- **adversarial.py** — Packages four named attack scenarios (prompt injection,
  malformed tool arguments, infinite tool-call loops, context overload) as reusable
  pass/fail checks. PM lesson: this is a checklist of "ways a malicious or careless
  user could break the bot," made runnable rather than left as tribal knowledge —
  the kind of test suite that should exist before any customer-facing agent ships.
- **llm_judge.py** — Scores agent output on 6 independent dimensions (correctness,
  completeness, groundedness, citation_quality, instruction_following, overall) via a
  second LLM call — never a single undifferentiated "was it good" score. PM lesson:
  this is what makes eval results actionable — "correctness dropped but completeness
  improved" tells you what to actually fix, unlike a single blended quality number.
- **human_eval.py** — Defines a 1-5 human rating schema plus a correlation function
  comparing human scores to the LLM judge's scores. PM lesson: this is how you'd
  prove (or disprove) that the automated judge can be trusted to replace expensive
  human review at scale — a real, answerable question rather than an assumption.
- **adaptation_advisor.py** — Codifies explicit if/then rules for choosing between
  in-context learning, RAG, fine-tuning, and distillation, and refuses to guess when
  no signal clearly applies. PM lesson: this is a decision framework you could use
  directly in a scoping conversation — "does this need fresh knowledge (→RAG), a
  strict output format (→fine-tuning), or is it just a few-shot problem (→ICL)?"
  rather than defaulting to whichever technique is currently trendy.

### app/observability/

- **traces.py** — Records a structured trace per execution (execution_id, session,
  user, model, token counts, tool/retrieval call counts, latency, cost, status) with
  nested spans (an agent span containing its LLM/tool/retrieval child spans). Errors
  are captured on the span but still propagate — never silently swallowed. PM lesson:
  this is the actual mechanism behind "why did this request fail or run slow" — the
  raw material for any debugging or performance dashboard, not just a nice-to-have.
- **costs.py** — Tracks cost per journey, broken down by component (agent/tool/model)
  rather than one lump total; an unconfigured model rate costs $0 but still shows up
  in the breakdown rather than vanishing silently. PM lesson: this answers "how much
  did this specific user journey actually cost," which is the real unit-economics
  question — not "how much did we spend on Gemini this month" in aggregate. A missing
  rate config showing as a visible $0 line (not a crash, not an omission) is itself a
  useful safety property: gaps in cost tracking stay discoverable.

### app/routing/model_router.py

- Routes a task to a cheap or strong model tier based on its complexity (simple
  classification vs. complex generation vs. evaluation), failing loudly at startup if
  any tier's provider isn't configured. PM lesson: this is the mechanism behind "when
  is a more expensive model actually worth it" — a routing table you could review and
  argue about directly (e.g. "should classification really get the cheap model?").

### app/caching/

- **prompt_cache.py** — Local exact-match cache standing in for real provider-side
  prompt caching, explicit in its own documentation about not being the same
  mechanism (it skips a full round-trip; real prompt caching reduces token-level
  processing cost even on a "miss" of the cached prefix). PM lesson: worth knowing
  this distinction exists before quoting "prompt caching" savings numbers externally
  — the local version and the vendor's server-side version save money differently.
- **semantic_cache.py** — Caches by meaning (so a paraphrased question hits the
  cache), but explicitly refuses to read OR write the cache for time-sensitive
  queries (marker words: today/now/latest/recent/changed/updated). PM lesson: this is
  the guardrail against "the bot confidently gave yesterday's answer to a question
  about today" — a real, embarrassing failure mode for anything answering
  policy/status/availability questions, and this is the specific rule that prevents it.

### app/safety/

- **injection.py** — Wraps any externally-sourced content (retrieved docs, tool
  results) in explicit "this is DATA, not instructions" framing before it re-enters a
  prompt; a marker-word detector flags suspicious content for logging (a signal, not
  the actual defense — regex can't reliably block injection on its own). PM lesson:
  this is the direct defense against a poisoned document or malicious web page trying
  to hijack the bot mid-conversation — relevant the moment the bot pulls content from
  any source you don't fully control (a public web search, a user-uploaded file).
- **permissions.py** — Enforces which permission scopes a caller actually has at the
  moment a tool is invoked, not just what the tool declares it needs. PM lesson: this
  is the difference between "the send_email tool is documented as needing
  write:email" and "this specific session is actually allowed to send email" — real
  authorization, not just documentation.

### app/memory/store.py

- Scopes every memory read/write by (tenant, user, session) with no method to query
  across scopes — isolation is a structural property of the store, not a rule callers
  have to remember to follow. PM lesson: this is what prevents one customer's chat
  history or personal context from ever leaking into another customer's session, by
  construction rather than by convention — the difference matters a lot in an audit
  or incident review ("could this have leaked" vs. "this cannot leak by design").
