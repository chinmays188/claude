# Voice Interface

## Example 1 — Voice turn returns a spoken-ready response

Input:
Transcript "Explain RAG." posted to `/voice/turn`.

Expected:
- Response routes through the same `Orchestrator` as text (Milestone 2) — no
  separate "voice-only" logic path
- `response_text` is the agent's plain-text answer, ready for `SpeechSynthesisUtterance`
- A `session_id` is returned, whether or not one was supplied

## Example 2 — Session continuity across requests

Input:
Two separate HTTP requests carrying the same `session_id`.

Expected:
- Both requests are served by the same `VoiceSession` instance (via `VoiceSessionStore`)
  — necessary because a browser can't hold a server-side session between page loads
  on its own; the browser must round-trip the `session_id` it was given

## Example 3 — Latency is measured per turn, not just logged as a vague "it was slow"

Input:
A voice turn including client-measured `stt_latency_ms`.

Expected:
- `VoiceTurn` records `stt_latency_ms` (from the browser), `agent_latency_ms`
  (measured server-side around the orchestrator call), and `total_latency_ms`
  (sum) — matching Section 8's "voice latency measurement" requirement as three
  distinct numbers, not one blended figure

## Example 4 — Empty transcript rejected clearly

Input:
An empty or whitespace-only transcript (e.g. STT produced nothing usable).

Expected:
- `VoiceSession.handle_transcript()` raises `ValueError`
- The HTTP layer (`/voice/turn`) turns this into a `400`, not a `500` or a silent
  no-op

## Example 5 — Ambiguous voice request still asks for clarification

Input:
A transcript the classifier can't confidently route (Milestone 2's existing
"unclear" behavior).

Expected:
- `response_text` is the same clarification message text-mode users would get —
  voice does not silently guess just because it's a different modality

## Example 6 — Voice vs. text comparison (evaluation)

Input:
A mixed set of `InteractionResult`s across both modes.

Expected:
- `compare_interactions()` reports task completion rate, average latency, and
  correction rate *separately* per mode — voice is never assumed to perform
  identically to text just because the underlying agent logic is shared

## Non-goals for this milestone

- STT/TTS themselves run entirely in the browser (Web Speech API) — no server-side
  speech model is implemented, matching Section 5's stack table
  ("Voice STT/TTS: Browser ... initially")
- Interruption handling (barge-in while the agent is still responding) is not
  implemented — the browser's `SpeechRecognition`/`speechSynthesis` APIs used here
  are single-turn request/response, not a streaming duplex channel
- No authentication on the voice endpoint — anyone who can reach the FastAPI
  process can start a session; this is a local-first, single-user Phase 2 build
