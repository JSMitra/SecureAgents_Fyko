"""Background asyncio poller.

Every 5 seconds:
  1. Query PostgreSQL for PENDING + unpublished records.
  2. Publish each to RabbitMQ.
  3. Mark the record as published=True.
"""

import asyncio
import logging

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models import AnnRequest
from app.services.rabbitmq import publish_ann_request

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5


async def _poll_once() -> None:
    """Single poll cycle: fetch unpublished PENDING rows and dispatch them."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AnnRequest).where(
                AnnRequest.status == "PENDING",
                AnnRequest.published == False,  # noqa: E712
            )
        )
        rows: list[AnnRequest] = list(result.scalars().all())

        if not rows:
            return

        for row in rows:
            try:
                await publish_ann_request(
                    ulid=row.ulid,
                    callback_url=row.callback_url,
                    use_complex_model=row.use_complex_model,
                )
                await session.execute(
                    update(AnnRequest)
                    .where(AnnRequest.ulid == row.ulid)
                    .values(published=True)
                )
                logger.info("Marked %s as published", row.ulid)
            except Exception as exc:  # pragma: no cover
                logger.error("Failed to publish %s: %s", row.ulid, exc)

        await session.commit()


async def run_poller() -> None:
    """Infinite loop that calls _poll_once every POLL_INTERVAL_SECONDS."""
    logger.info("Poller started — interval=%ds", POLL_INTERVAL_SECONDS)
    while True:
        try:
            await _poll_once()
        except Exception as exc:  # pragma: no cover
            logger.error("Poller cycle error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
