"""
main.py — Secret Plan Creator FastAPI application.

Endpoints
---------
GET  /.well-known/agent.json    Agent Card (A2A discovery)
POST /interact                  Human user sends a movie question
GET  /interact/stream           SSE stream of mission step events (for UI)
POST /ann-callback              FykoServer ANN completion callback
POST /a2a/tasks/send            (optional) Receive A2A tasks from peers
GET  /a2a/tasks/{task_id}       Task status (for completeness)
GET  /health                    Liveness probe
"""

import asyncio
import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Make shared importable when running inside Docker (PYTHONPATH=/app)
sys.path.insert(0, "/app")

from agent import init_agent, handle_user_message, handle_ann_callback

# ── SSE event bus ─────────────────────────────────────────────────────────────
# Maps session_id → asyncio.Queue of SSE event dicts
_sse_queues: dict[str, asyncio.Queue] = {}


def publish_step_event(session_id: str, event: dict) -> None:
    """Publish a mission-step event to all SSE listeners for a session."""
    q = _sse_queues.get(session_id)
    if q:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_agent()
    yield


app = FastAPI(
    title="Secret Plan Creator",
    description="FYKO intelligence operative — movie cover-story agent",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the fyko_ui dev server (localhost:5173) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class InteractRequest(BaseModel):
    message: str
    session_id: str | None = None  # optional SSE session correlator


class AnnCallbackRequest(BaseModel):
    ulid: str
    status: str  # "COMPLETED" | "FAILED" | etc.


class A2ATaskMessage(BaseModel):
    role: str
    parts: list[dict[str, Any]]


class A2ATaskRequest(BaseModel):
    id: str
    message: A2ATaskMessage


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/.well-known/agent.json")
async def agent_card():
    """A2A Agent Card for discovery."""
    return {
        "name": "Secret Plan Creator",
        "description": (
            "An AI agent operative that uses FYKO ANN-derived AES keys "
            "to securely query the Secret Plan Reviewer about recent movies."
        ),
        "version": "1.0.0",
        "url": "http://secret-plan-creator:9001",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "movie_query",
                "name": "Movie Intelligence Query",
                "description": "Ask about the latest movies using secure A2A channel.",
            }
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "secret_plan_creator"}


@app.post("/interact")
async def interact(req: InteractRequest):
    """
    Entry point for human users.
    Accepts a natural-language movie question and returns the secure
    answer obtained from the Secret Plan Reviewer.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    try:
        # Register SSE queue for this session if provided
        if req.session_id:
            _sse_queues[req.session_id] = asyncio.Queue(maxsize=100)

        def event_callback(evt):
            if req.session_id:
                publish_step_event(req.session_id, evt)

        response = await handle_user_message(
            req.message,
            session_id=req.session_id,
            event_cb=event_callback if req.session_id else None,
        )

        # Signal SSE stream that mission is done
        if req.session_id and req.session_id in _sse_queues:
            publish_step_event(req.session_id, {"type": "done", "response": response})

        return {"response": response, "session_id": req.session_id}
    except TimeoutError as exc:
        logger.error("Timeout: %s", exc)
        if req.session_id:
            publish_step_event(req.session_id, {"type": "error", "message": str(exc)})
        raise HTTPException(status_code=504, detail=str(exc))
    except Exception as exc:
        logger.exception("Error in /interact: %s", exc)
        if req.session_id:
            publish_step_event(req.session_id, {"type": "error", "message": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Clean up queue after response is sent
        if req.session_id:
            _sse_queues.pop(req.session_id, None)


@app.get("/interact/stream")
async def interact_stream(session_id: str = Query(...)):
    """
    Server-Sent Events stream for a running mission session.
    The UI connects here with the session_id before calling POST /interact.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_queues[session_id] = queue

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield "data: {\"type\": \"heartbeat\"}\n\n"
        finally:
            _sse_queues.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/ann-callback")
async def ann_callback(req: AnnCallbackRequest):
    """
    Receives ANN readiness notifications from FykoServer.
    """
    handle_ann_callback(req.ulid, req.status)
    return {"acknowledged": True}


# ── Minimal A2A endpoint stubs (creator is mostly a sender, not a receiver) ──

_creator_tasks: dict[str, dict] = {}


@app.post("/a2a/tasks/send")
async def a2a_send(req: A2ATaskRequest):
    """Accept an incoming A2A task (reserved for future peer communication)."""
    _creator_tasks[req.id] = {
        "id": req.id,
        "status": {"state": "completed"},
        "artifacts": [{"parts": [{"type": "text", "text": "acknowledged"}]}],
    }
    return _creator_tasks[req.id]


@app.get("/a2a/tasks/{task_id}")
async def a2a_get(task_id: str):
    task = _creator_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=False)
