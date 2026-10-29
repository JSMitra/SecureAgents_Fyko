"""Internal routes called by ANN Generator workers."""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnnRequest
from app.schemas import ModelReadyPayload, ModelReadyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/model-ready", response_model=ModelReadyResponse)
async def model_ready(
    payload: ModelReadyPayload,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Called by a worker once a model is stored in GridFS.

    Updates the PostgreSQL record to COMPLETED and fires the original
    callback_url supplied by the API consumer.
    """
    # Fetch the record to obtain the callback_url.
    from sqlalchemy import select

    result = await db.execute(
        select(AnnRequest).where(AnnRequest.ulid == payload.ulid)
    )
    record: AnnRequest | None = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="ANN request not found")

    # Update status and model_name.
    await db.execute(
        update(AnnRequest)
        .where(AnnRequest.ulid == payload.ulid)
        .values(
            status="COMPLETED",
            model_name=payload.model_name,
        )
    )
    await db.commit()
    logger.info("Marked %s as COMPLETED (model=%s)", payload.ulid, payload.model_name)

    # Fire the consumer callback asynchronously (best-effort).
    callback_url = record.callback_url
    download_url = f"/ann/model/{payload.ulid}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                callback_url,
                json={
                    "ulid": payload.ulid,
                    "download_url": download_url,
                },
            )
            resp.raise_for_status()
            logger.info(
                "Callback delivered to %s (HTTP %d)", callback_url, resp.status_code
            )
    except Exception as exc:
        # Log and continue — the consumer can poll /ann/status instead.
        logger.warning("Callback to %s failed: %s", callback_url, exc)

    return ModelReadyResponse(ok=True)
