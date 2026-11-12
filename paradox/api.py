"""HTTP API for the brain interface:  uvicorn paradox.api:app --port 8100

POST /api/chat      {"session": "...", "text": "..."}  -> server-sent events, one per thinking phase,
                    then a final "reply" event. The 3D brain lights up a region per phase.
POST /api/rate      {"session": "...", "rating": 1-5, "note": "", "conclusion_id": optional}
GET  /api/trace?session=...
GET  /api/health
GET  /            the brain interface itself
"""
from __future__ import annotations

import json
import queue
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pathlib import Path
from pydantic import BaseModel

from .conversation import Session
from .embed import Embedder
from .llm import LLM, LLMError
from .memory import Memory
from .nli import NLI

app = FastAPI(title="Paradox", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

_shared: dict = {}
_sessions: dict[str, Session] = {}
_lock = threading.Lock()   # one thought at a time: the graphics card can only run one model call well


def _parts():
    if not _shared:
        _shared.update(llm=LLM(), nli=NLI(), memory=Memory(embedder=Embedder()))
    return _shared


class ChatIn(BaseModel):
    session: str
    text: str


class RateIn(BaseModel):
    session: str
    rating: int
    note: str = ""
    conclusion_id: int | None = None


def _session(sid: str, emit) -> Session:
    p = _parts()
    s = _sessions.get(sid)
    if s is None:
        s = _sessions[sid] = Session(p["llm"], p["nli"], p["memory"], session_id=sid)
    s.engine.emit = emit
    return s


@app.post("/api/chat")
def chat(body: ChatIn):
    events: queue.Queue = queue.Queue()

    def emit(phase: str, data: dict):
        events.put({"phase": phase, "data": data})

    def work():
        with _lock:
            try:
                reply = _session(body.session, emit).send(body.text)
                events.put({"phase": "reply", "data": {"text": reply.text, "intent": reply.intent,
                                                       "conclusion_id": reply.conclusion_id}})
            except LLMError as e:
                events.put({"phase": "error", "data": {"message": str(e)}})
            finally:
                events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (item := events.get()) is not None:
            yield f"event: {item['phase']}\ndata: {json.dumps(item['data'], ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/rate")
def rate(body: RateIn):
    s = _sessions.get(body.session)
    try:
        if s:
            s.rate(body.rating, body.note, body.conclusion_id)
        elif body.conclusion_id:
            _parts()["memory"].rate(body.conclusion_id, body.rating, body.note)
        else:
            raise ValueError("unknown session")
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/api/trace")
def trace(session: str):
    s = _sessions.get(session)
    return {"trace": s.trace() if s else ""}


UI = Path(__file__).resolve().parent.parent / "ui" / "dist" / "index.html"


@app.get("/")
def interface():
    """The brain interface, built into one file (ui/dist/index.html)."""
    if UI.exists():
        return FileResponse(UI)
    return PlainTextResponse("Interface not built. Run: cd ui && npm install && npm run build", status_code=404)


@app.get("/api/health")
def health():
    llm = _parts()["llm"]
    return {"ok": True, "model": llm.model, "url": llm.url}
