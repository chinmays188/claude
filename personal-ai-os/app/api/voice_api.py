from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.providers.gemini_provider import GeminiProvider
from app.voice.session import VoiceSessionStore

app = FastAPI(title="Personal AI OS — Voice Interface")

_default_session_store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm=GeminiProvider()))


def get_session_store() -> VoiceSessionStore:
    return _default_session_store


class TranscriptRequest(BaseModel):
    session_id: str | None = None
    transcript: str
    stt_latency_ms: float | None = None


class TranscriptResponse(BaseModel):
    session_id: str
    response_text: str
    agent_latency_ms: float
    total_latency_ms: float


@app.post("/voice/turn", response_model=TranscriptResponse)
def voice_turn(
    request: TranscriptRequest, session_store: VoiceSessionStore = Depends(get_session_store)
) -> TranscriptResponse:
    if not request.transcript or not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript must not be empty.")

    session = session_store.get_or_create(request.session_id)
    turn = session.handle_transcript(request.transcript, stt_latency_ms=request.stt_latency_ms)

    return TranscriptResponse(
        session_id=session.session_id,
        response_text=turn.response_text,
        agent_latency_ms=turn.agent_latency_ms,
        total_latency_ms=turn.total_latency_ms,
    )


@app.get("/", response_class=HTMLResponse)
def voice_page() -> str:
    return _VOICE_PAGE_HTML


_VOICE_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Personal AI OS — Voice</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
  button { font-size: 1rem; padding: 10px 20px; margin-right: 8px; }
  #transcript, #response { white-space: pre-wrap; border: 1px solid #ccc; padding: 12px; margin-top: 12px; min-height: 40px; }
  #status { color: #666; font-size: 0.9rem; }
</style>
</head>
<body>
  <h1>Personal AI OS — Voice</h1>
  <button id="startBtn">Start listening</button>
  <button id="stopBtn" disabled>Stop</button>
  <p id="status">Idle.</p>
  <h3>You said:</h3>
  <div id="transcript"></div>
  <h3>Response:</h3>
  <div id="response"></div>

<script>
let sessionId = null;
let recognition = null;
let sttStart = null;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function setStatus(text) { document.getElementById("status").textContent = text; }

if (!SpeechRecognition) {
  setStatus("Browser Web Speech API not supported. Try Chrome.");
} else {
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    sttStart = performance.now();
    setStatus("Listening...");
    document.getElementById("startBtn").disabled = true;
    document.getElementById("stopBtn").disabled = false;
  };

  recognition.onerror = (event) => {
    setStatus("STT error: " + event.error);
    document.getElementById("startBtn").disabled = false;
    document.getElementById("stopBtn").disabled = true;
  };

  recognition.onresult = async (event) => {
    const sttLatencyMs = performance.now() - sttStart;
    const transcript = event.results[0][0].transcript;
    document.getElementById("transcript").textContent = transcript;
    setStatus("Thinking...");

    try {
      const res = await fetch("/voice/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          transcript: transcript,
          stt_latency_ms: sttLatencyMs,
        }),
      });
      if (!res.ok) throw new Error("Request failed: " + res.status);
      const data = await res.json();
      sessionId = data.session_id;
      document.getElementById("response").textContent = data.response_text;
      setStatus(`Done. Agent: ${data.agent_latency_ms.toFixed(0)}ms, Total: ${data.total_latency_ms.toFixed(0)}ms`);

      const utterance = new SpeechSynthesisUtterance(data.response_text);
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      setStatus("Error: " + err.message);
    }
  };

  recognition.onend = () => {
    document.getElementById("startBtn").disabled = false;
    document.getElementById("stopBtn").disabled = true;
  };

  document.getElementById("startBtn").addEventListener("click", () => recognition.start());
  document.getElementById("stopBtn").addEventListener("click", () => recognition.stop());
}
</script>
</body>
</html>
"""
