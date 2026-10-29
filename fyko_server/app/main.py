"""Fyko Server — FastAPI application entry point."""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import ann, internal
from app.services.poller import run_poller
from app.services.rabbitmq import close_rabbitmq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fyko Server",
    description="ANN generation request broker for the FYKO (ForYourKeysOnly) system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(ann.router)
app.include_router(internal.router)


# ---------------------------------------------------------------------------
# Lifespan events
# ---------------------------------------------------------------------------

_poller_task: asyncio.Task | None = None


@app.on_event("startup")
async def on_startup() -> None:
    global _poller_task
    logger.info("Starting Fyko Server …")
    await init_db()
    _poller_task = asyncio.create_task(run_poller(), name="ann-poller")
    logger.info("Background poller scheduled.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _poller_task
    logger.info("Shutting down Fyko Server …")
    if _poller_task and not _poller_task.done():
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass
    await close_rabbitmq()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
