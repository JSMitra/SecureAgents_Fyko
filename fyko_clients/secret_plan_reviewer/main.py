"""
main.py — Secret Plan Reviewer FastAPI application.

Endpoints
---------
GET  /.well-known/agent.json    Agent Card (A2A discovery)
POST /a2a/tasks/send            Receive task from Secret Plan Creator
GET  /a2a/tasks/{task_id}       Poll task status / retrieve artifact
GET  /health                    Liveness probe
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, "/app")

from agent import (
    init_agent,
    tasks,
    enqueue_task,
    start_rabbitmq_consumer,
    stop_rabbitmq_consumer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_agent()
    await start_rabbitmq_consumer(app)
    yield
    await stop_rabbitmq_consumer(app)


app = FastAPI(
    title="Secret Plan Reviewer",
    description="FYKO intelligence operative — secure movie-knowledge reviewer",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class A2ATaskMessagePart(BaseModel):
    type: str
    text: str


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
        "name": "Secret Plan Reviewer",
        "description": (
            "FYKO-secured reviewer that answers movie intelligence queries "
            "using ANN-derived AES keys shared via RSA-encrypted A2A tasks."
        ),
        "version": "1.0.0",
        "url": "http://secret-plan-reviewer:9002",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "movie_review",
                "name": "Secure Movie Review",
                "description": "Receive and answer AES-encrypted movie questions.",
            }
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "secret_plan_reviewer"}


@app.post("/a2a/tasks/send")
async def a2a_send(req: A2ATaskRequest):
    """
    Accept an incoming A2A task from the Secret Plan Creator.
    Returns immediately with state=working; processing happens asynchronously
    via the RabbitMQ consumer.
    """
    task_dict = req.model_dump()

    # Register task as "working" right away so Creator can poll
    tasks[req.id] = {
        "id": req.id,
        "status": {"state": "working"},
        "artifacts": [],
    }

    # Push to RabbitMQ queue for async processing
    await enqueue_task(task_dict)

    return tasks[req.id]


@app.get("/a2a/tasks/{task_id}")
async def a2a_get(task_id: str):
    """Return the current status (and artifacts if completed) for a task."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9002, reload=False)
