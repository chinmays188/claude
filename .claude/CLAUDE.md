

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# About Me
- Product Manager at MakeMyTrip (OTA - Online Travel Agency, India)
- Domain: Post-sales customer experience
- Projects : Building Voice bot and chatbot and agent assist and email bot 
- Non-technical background — no code preferences

# Working Style
- Always explain the **why** behind every output or recommendation
- Structure all responses in bullet points — concise, no fluff
- No long paragraphs or summaries of what was just done

# Things to Avoid
- Do not execute any action (file edits, commands, commits, etc.) without explicit approval first
- Do not write code-heavy responses unless specifically asked
- No emojis unless asked
- Work until loop is complete, find a goal. Do not deviate from the goal or mark the task as completed till the time we hit the goal

# Tools & Environment
- OS: macOS
- Editor: VSCode

## Learning

Track two types of knowledge:
- Domain: what things are (product context, user preferences, APIs, naming conventions, team decisions)
- Procedural: how to do things (deploy steps, test commands, review flows)

Organize knowledge as a hierarchy of .md files:
- knowledge/index.md routes to categories
- Categories hold the details
- Progressive disclosure. Read top-down, only load what you need.

Log errors to knowledge/errors.md. Not every error is a mistake:
- Deterministic errors (bad schema, wrong type, missing field) → conclude immediately
- Infrastructure errors (timeout, rate limit, network) → log, no conclusion until pattern emerges
- Conclusions graduate into the relevant domain or procedural file

Actively manage the knowledge system. This is as important as the current task:
- Review knowledge files at the start of each session
- Merge overlapping categories
- Split files that grow too long
- Remove knowledge that's no longer accurate
- Create new categories when patterns emerge
- When you notice something that should be in claude.md but isn't — a pattern, a preference, a correction — propose the edit. Don't wait to be asked.

## Task Delegation

Spawn subagents to isolate context, parallelize independent work, or offload bulk mechanical tasks. Don't spawn when the parent needs the reasoning, when synthesis requires holding things together, or when spawn overhead dominates.

Pick the cheapest model that can do the subtask well:
- Haiku: bulk mechanical work, no judgment
- Sonnet: scoped research, code exploration, in-scope synthesis
- Opus: subtasks needing real planning or tradeoffs

If a subagent realizes it needs a higher tier than itself, return to the parent.

Parent owns final output and cross-spawn synthesis. User instructions override.

## Preferred Tools

### Data Fetching

1. **WebFetch** — free, text-only, works on public pages that don't block bots.
2. **agent-browser CLI** — free, local Rust CLI + Chrome via CDP. For dynamic pages or auth walls that WebFetch can't handle. Returns the accessibility tree with element refs (@e1, @e2) — ~82% fewer tokens than screenshot-based tools. Install: `npm i -g agent-browser && agent-browser install`. Use `snapshot` for AI-friendly DOM state, element refs for interaction.
3. **Notice recurring fetch patterns and propose wrapping them as dedicated tools.** When the same fetch/parse logic comes up more than once, suggest wrapping it as a named tool (e.g. a skill file that calls `agent-browser` with the snapshot and extraction steps baked in for that source). Add the entry to `## Dedicated Tools` below and reference it by name on future calls.

### PDF Files

Use 'pdftotext', not the 'Read' tool. Use 'Read' only when the user directly asks to analyze images or charts inside the document.

## Dedicated Tools

<!-- List project-specific tools here. For each, link to its skill or script file (e.g. `tools/linkedin_fetch.md`). The orchestration logic lives in those files, not here. -->
