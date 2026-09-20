# Personal AI Operating System

# Phase 2 — Personal Intelligence Layer

**Version:** 1.0
**Status:** Build Specification
**Previous Phase:** Phase 1 — AI Engineering Foundation
**Next Phase:** Phase 3 — Personal Domain OS

---

# 1. Phase 2 Vision

Phase 1 established the AI engineering foundation:

* Multi-agent orchestration
* Agent loops
* Skills
* Tools
* MCP/tool contracts
* Structured outputs
* Repair loops
* Guardrails
* RAG
* Retrieval evaluation
* Context engineering
* Model routing
* Fallbacks
* Caching
* Latency engineering
* Observability
* Cost attribution
* Safety
* Regression and adversarial testing

Phase 2 turns that generic AI runtime into a **personal intelligence system**.

The central question changes from:

> "Can the system perform an AI task?"

to:

> **"Can the system understand my personal context, knowledge, history and current situation?"**

The system should become:

```text
Generic AI Runtime
        ↓
Personal Context
        ↓
Personal Knowledge
        ↓
Personal Memory
        ↓
Personal RAG
        ↓
Personal Actions
```

---

# 2. Phase 2 Outcome

At the end of Phase 2, the user should be able to interact with the Personal AI OS through voice or text and ask questions such as:

> "What did I work on last week?"

> "Remind me why I decided to use RAG for this project."

> "Look at my recent GitHub activity and tell me what I accomplished."

> "Here's a screenshot of this error. What is wrong?"

> "Based on what you know about my current goals, what should I focus on today?"

> "Find the relevant documents for this project and summarize the latest decisions."

The system should be able to:

1. Hear the user.
2. Understand the request.
3. Retrieve relevant personal information.
4. Distinguish memory from retrieved knowledge.
5. Use external tools.
6. Ask for approval before consequential actions.
7. Execute longer-running workflows.
8. Maintain a personal decision/history graph.
9. Evaluate personalization quality.
10. Show what the AI did.

---

# 3. Phase 2 Milestones

Phase 2 contains 12 milestones.

```text
18. Voice Interface
19. Personal Knowledge Ingestion
20. Long-Term Memory
21. Personal RAG
22. Multimodal Understanding
23. Personal Context Engine
24. Real-World Integrations
25. Human Approval & Action Layer
26. Long-Running Tasks
27. Personal Event & Decision Graph
28. Personal OS Evaluation
29. Personal AI Dashboard
```

---

# 4. Technology Philosophy

Phase 2 must continue the following principles:

* Free-first
* Local-first
* Provider-independent
* No frontier models required
* No unnecessary cloud infrastructure
* No paid vector database
* No paid observability platform
* No unnecessary framework abstraction
* Every new capability must be measurable

The system should continue using the Phase 1 stack wherever possible.

---

# 5. Technology Stack

| Layer              | Technology                              |
| ------------------ | --------------------------------------- |
| Language           | Python 3.11+                            |
| Backend            | FastAPI                                 |
| Primary LLM        | Gemini 2.5 Flash-Lite / Flash free tier |
| Model fallback     | OpenRouter free models                  |
| Search             | Tavily free tier                        |
| Alternative search | Brave Search                            |
| Database           | SQLite                                  |
| Vector database    | FAISS / Chroma local                    |
| Embeddings         | Local open-source embedding model       |
| Reranker           | Local/open-source reranker              |
| Voice STT          | Browser Web Speech API initially        |
| Voice TTS          | Browser SpeechSynthesis initially       |
| Multimodal         | Free-tier multimodal model              |
| UI                 | Streamlit or simple web UI              |
| Tools              | Python tools + MCP                      |
| Testing            | pytest                                  |
| Evaluation         | Existing Phase 1 evaluation framework   |
| Observability      | Existing SQLite trace system            |
| Hosting            | Local initially                         |
| Version control    | Git + GitHub                            |

---

# 6. Provider Abstraction

No application component should directly depend on Gemini.

Use:

```text
LLMProvider
    ├── GeminiProvider
    ├── OpenRouterProvider
    └── FutureProvider
```

Similarly:

```text
EmbeddingProvider
    ├── LocalEmbeddingProvider
    └── FutureEmbeddingProvider
```

And:

```text
VoiceProvider
    ├── BrowserVoiceProvider
    └── FutureVoiceProvider
```

The goal is to keep the system replaceable.

---

# 7. Architecture

```text
                              USER
                                │
                    ┌───────────┴───────────┐
                    │                       │
                  VOICE                    TEXT
                    │                       │
                    ▼                       │
              Speech-to-Text                │
                    │                       │
                    └───────────┬───────────┘
                                ▼
                        INPUT PROCESSOR
                                │
                                ▼
                     PERSONAL CONTEXT ENGINE
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
          MEMORY               RAG            CURRENT TASK
             │                  │                  │
             └──────────────────┼──────────────────┘
                                ▼
                         TASK CLASSIFIER
                                │
                                ▼
                          ORCHESTRATOR
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
             RESEARCH        ANALYST         PLANNER
               AGENT          AGENT            AGENT
                │               │               │
                └───────────────┼───────────────┘
                                ▼
                           MODEL ROUTER
                                │
                                ▼
                         SKILLS + TOOLS
                                │
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
               GitHub        Calendar        Files
                  │             │             │
                  └─────────────┼─────────────┘
                                ▼
                         ACTION PROPOSAL
                                │
                         POLICY ENGINE
                                │
                        USER APPROVAL
                                │
                                ▼
                             EXECUTE
                                │
                                ▼
                             VERIFY
                                │
                                ▼
                           EVALUATOR
                                │
                                ▼
                         OBSERVABILITY
                                │
                                ▼
                            MEMORY
                                │
                                ▼
                             RESPONSE
                                │
                                ▼
                               TTS
                                │
                                ▼
                              USER
```

---

# 8. Milestone 18 — Voice Interface

## Objective

Make voice a first-class interface.

The user should be able to:

```text
Speak
 ↓
Transcribe
 ↓
Execute Personal AI OS
 ↓
Hear response
```

---

## Architecture

```text
Microphone
    ↓
Browser STT
    ↓
Transcript
    ↓
FastAPI
    ↓
Agent Runtime
    ↓
Response
    ↓
Browser TTS
    ↓
Speaker
```

---

## Requirements

* Microphone input
* Speech-to-text
* Text transcript
* Voice response
* Session continuity
* Streaming
* Interruption handling
* Error handling
* Voice latency measurement

---

## Evaluation

Compare:

```text
Voice interaction
vs
Text interaction
```

Measure:

* Task completion
* STT error rate
* User correction rate
* Time to completion
* First response latency
* Total interaction time

---

# 9. Milestone 19 — Personal Knowledge Ingestion

## Objective

Allow the AI OS to ingest the user's personal knowledge.

Supported initial formats:

```text
PDF
DOCX
TXT
Markdown
CSV
JSON
Images
```

Potential sources:

* Resume
* Product documents
* Project documents
* Interview notes
* Learning notes
* Technical notes
* Portfolio documents
* Decision logs
* Personal goals
* Research

---

## Pipeline

```text
Document
 ↓
Parser
 ↓
Cleaner
 ↓
Metadata Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Store
```

Each document should contain metadata:

```json
{
  "document_id": "...",
  "source": "...",
  "title": "...",
  "created_at": "...",
  "updated_at": "...",
  "version": "...",
  "category": "...",
  "sensitivity": "..."
}
```

---

# 10. Knowledge Security

Every document must have:

```text
owner_id
tenant_id
sensitivity
permissions
```

Potential sensitivity levels:

```text
PUBLIC
PERSONAL
CONFIDENTIAL
HIGHLY_SENSITIVE
```

The retrieval layer must enforce permissions before returning content.

The LLM must never be responsible for enforcing access control.

---

# 11. Milestone 20 — Long-Term Memory

## Objective

Move from conversation history to meaningful personal memory.

Memory types:

```text
Profile
Preference
Goal
Decision
Experience
Achievement
Project
Relationship
Learning
```

---

## Memory architecture

```text
                    MEMORY
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
    Profile         Episodic        Semantic
       │               │               │
       ▼               ▼               ▼
 Preferences        Events        Knowledge
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                    Decisions
```

---

# 12. Memory Write Policy

The system must NOT save every conversation.

Instead:

```text
Conversation
 ↓
Memory Candidate
 ↓
Memory Classifier
 ↓
Importance Score
 ↓
Duplicate Check
 ↓
User Approval if necessary
 ↓
Persistent Memory
```

Memory should have:

```text
memory_id
type
content
source
confidence
created_at
updated_at
importance
user_confirmed
```

---

# 13. Memory Retrieval

Retrieval should consider:

```text
Semantic similarity
Recency
Importance
Explicit user confirmation
Current task relevance
```

Example:

```text
Current request
      ↓
Candidate memories
      ↓
Relevance ranking
      ↓
Top memories
      ↓
Context builder
```

---

# 14. Milestone 21 — Personal RAG

## Objective

Combine personal knowledge and memory.

Example:

> "What did I learn about RAG last month?"

Pipeline:

```text
Question
 ↓
Query Understanding
 ↓
Memory Retrieval
 ↓
Document Retrieval
 ↓
Hybrid Search
 ↓
Reranking
 ↓
Context Builder
 ↓
LLM
 ↓
Citations
```

---

# 15. Personal RAG Sources

Initially:

```text
Documents
Memory
Decision logs
Project notes
Learning notes
```

Later:

```text
GitHub
Email
Calendar
Drive
Slack
Teams
```

---

# 16. Personal RAG Evaluation

Add metrics from Phase 1:

* Recall@K
* Precision@K
* Grounding
* Attribution
* Citation quality

Add personal metrics:

### Memory precision

Did the system retrieve the correct personal memory?

### Memory recall

Did the system retrieve all relevant memories?

### Personalization

Did the response use relevant personal context?

### Temporal correctness

Did it retrieve information from the correct time period?

---

# 17. Milestone 22 — Multimodal Understanding

## Objective

Allow the Personal AI OS to understand:

* Text
* Voice
* Images
* Screenshots
* PDFs
* Tables

Examples:

```text
Screenshot of error
        ↓
AI diagnosis
```

```text
Screenshot of job description
        ↓
JD extraction
```

```text
PDF project document
        ↓
Knowledge ingestion
```

---

# 18. Multimodal Evaluation

Evaluate:

* OCR accuracy
* Table extraction
* Image understanding
* Document understanding
* Groundedness
* Citation quality

Include adversarial examples such as:

* misleading screenshots
* low-quality scans
* partial screenshots
* images containing prompt injection

---

# 19. Milestone 23 — Personal Context Engine

## Objective

Build a system that decides what information should enter the context window.

The context engine receives:

```text
Current request
Conversation history
Memory
Retrieved documents
Tool results
User preferences
Current date/time
```

It produces:

```text
Prioritized context
```

---

# 20. Context Selection

Each context item should have:

```text
relevance
importance
freshness
source
confidence
token_cost
```

Example:

```text
Current JD                HIGH
Relevant resume           HIGH
Relevant project          HIGH
Old interview             MEDIUM
Unrelated conversation    NONE
```

---

# 21. Context Experiments

Run experiments for:

* Context ordering
* Context compression
* Retrieval order
* Memory order
* Tool-result placement
* Lost-in-the-middle
* Token budget

Measure:

```text
Accuracy
Groundedness
Latency
Token usage
Cost
```

---

# 22. Milestone 24 — Real-World Integrations

## Objective

Connect the Personal AI OS to actual services.

Start with read-only integrations.

Recommended order:

```text
1. GitHub
2. Calendar
3. Drive
4. Email
5. Slack / Teams
```

Use MCP/tool abstractions.

---

# 23. GitHub Integration

Example:

> "What did I accomplish on this project this week?"

System:

```text
GitHub
 ↓
Commits
 ↓
Pull Requests
 ↓
Issues
 ↓
Activity summarization
 ↓
Personal context
 ↓
Response
```

Evaluation:

* Correct repository
* Correct time period
* Correct activity
* No fabricated activity

---

# 24. Calendar Integration

Example:

> "What does my day look like?"

System retrieves:

* meetings
* events
* conflicts
* preparation requirements

Do not initially modify calendar events.

Read-only first.

---

# 25. Email Integration

Start read-only.

Examples:

> "What important emails did I receive today?"

> "Which conversations require a response?"

The system should classify:

```text
FYI
Action required
Waiting for response
Commitment
Urgent
```

---

# 26. Milestone 25 — Human Approval & Action Layer

## Objective

Move from:

```text
AI reads
```

to:

```text
AI proposes
 ↓
User approves
 ↓
AI acts
 ↓
AI verifies
```

---

# 27. Action Classes

### READ

No approval.

### WRITE

Usually approval.

### ACT

Approval required.

Examples:

```text
Read GitHub        READ
Create draft       WRITE
Send email         ACT
Create calendar    ACT
Modify GitHub      ACT
```

---

# 28. Action Architecture

```text
Agent
 ↓
Action Proposal
 ↓
Permission Check
 ↓
Risk Assessment
 ↓
Approval UI
 ↓
User Approves
 ↓
Tool Execution
 ↓
Verification
 ↓
Audit Log
```

Every action should generate an audit record.

---

# 29. Milestone 26 — Long-Running Tasks

## Objective

Allow workflows that span multiple steps and potentially multiple execution periods.

Example:

> "Research the top 10 AI PM companies and create a comparison."

---

# 30. Task State Machine

```text
PENDING
 ↓
PLANNING
 ↓
RUNNING
 ↓
WAITING
 ↓
RUNNING
 ↓
EVALUATING
 ↓
COMPLETED
```

Failure:

```text
RUNNING
 ↓
FAILED
 ↓
RECOVERY
 ↓
RUNNING
```

---

# 31. Requirements

Every long-running task requires:

```text
task_id
state
checkpoint
created_at
updated_at
owner
retry_count
progress
dependencies
result
```

Support:

* Pause
* Resume
* Cancel
* Retry
* Recover
* Inspect progress

---

# 32. Milestone 27 — Personal Event & Decision Graph

## Objective

Represent relationships between:

```text
People
Projects
Goals
Decisions
Experiences
Achievements
Documents
Tasks
```

Example:

```text
                    User
                      │
              ┌───────┼────────┐
              ▼       ▼        ▼
           Career   Projects   Goals
              │       │        │
              ▼       ▼        ▼
           AI PM   Voicebot  Career Goal
                      │
                      ▼
                  Achievement
```

---

# 33. Decision Graph

A decision should contain:

```text
decision
date
context
reason
alternatives
chosen_option
expected_outcome
actual_outcome
related_project
```

The system should answer:

> "Why did I make this decision?"

using the decision graph.

---

# 34. Milestone 28 — Personal OS Evaluation

The Phase 1 evaluation framework should now be extended to personal workloads.

Evaluation categories:

## Career

* Resume retrieval
* Interview story retrieval
* JD analysis

## Learning

* Concept explanation
* Exercise generation
* Knowledge recall

## PM

* Project summary
* Feedback analysis
* Stakeholder information retrieval

## Personal Knowledge

* Correct memory
* Correct project
* Correct decision
* Correct timeline

---

# 35. New Personal Metrics

Add:

```text
Personalization
Memory Precision
Memory Recall
Temporal Accuracy
Actionability
Trustworthiness
```

---

# 36. Human Evaluation

Create a simple evaluation interface.

Show:

```text
User request

Retrieved memory

Retrieved documents

Agent response

Citations

Execution trace
```

Human evaluates:

```text
Correctness       1–5
Personalization   1–5
Trust             1–5
Usefulness        1–5
Citations         1–5
```

Compare human scores with LLM-as-judge scores.

---

# 37. Milestone 29 — Personal AI Dashboard

Build a simple dashboard using Streamlit or a lightweight web UI.

Dashboard sections:

```text
Overview
Conversations
Memory
Projects
Decisions
Tasks
Approvals
Agent activity
Evaluations
Cost
Latency
```

---

# 38. Example Dashboard

```text
PERSONAL AI OS

Today's Activity
────────────────────────────

Agent Runs              14
Tasks Completed         11
Pending Approvals        2
Evaluation Score       93%
Avg Latency           2.4s

Memory
────────────────────────────

Memories               312
Decisions               24
Projects                18

AI Health
────────────────────────────

Groundedness           94%
Tool Success           97%
Retrieval Recall       91%
Regression Status      PASS
```

---

# 39. Phase 2 Definition of Done

Phase 2 is complete when:

## Voice

* [ ] Voice input
* [ ] Voice output
* [ ] Streaming
* [ ] Session continuity
* [ ] Voice latency metrics

## Personal Knowledge

* [ ] Document ingestion
* [ ] Metadata
* [ ] Chunking
* [ ] Embeddings
* [ ] Local vector store

## Memory

* [ ] Profile memory
* [ ] Episodic memory
* [ ] Decision memory
* [ ] Memory write policy
* [ ] Memory retrieval

## RAG

* [ ] Personal RAG
* [ ] Hybrid retrieval
* [ ] Reranking
* [ ] Citations
* [ ] Retrieval evaluation

## Context

* [ ] Context builder
* [ ] Prioritization
* [ ] Compression
* [ ] Lost-in-middle experiments

## Multimodal

* [ ] Image
* [ ] Screenshot
* [ ] PDF
* [ ] Voice

## Integrations

* [ ] GitHub
* [ ] Calendar
* [ ] At least one additional integration

## Actions

* [ ] Permission model
* [ ] Approval flow
* [ ] Audit log
* [ ] Verification

## Long-running tasks

* [ ] State machine
* [ ] Checkpointing
* [ ] Resume
* [ ] Retry
* [ ] Cancellation

## Personal evaluation

* [ ] Golden datasets
* [ ] Personal evals
* [ ] Human eval
* [ ] LLM judge
* [ ] Regression testing

## Dashboard

* [ ] Agent activity
* [ ] Memory
* [ ] Tasks
* [ ] Evaluations
* [ ] Cost
* [ ] Latency
