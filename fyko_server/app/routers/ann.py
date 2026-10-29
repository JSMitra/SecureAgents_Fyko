"""ANN routes: /ann/request, /ann/status/{ulid}, /ann/model/{ulid}."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from python_ulid import ULID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_mongo_db
from app.models import AnnRequest
from app.schemas import AnnRequestCreate, AnnRequestCreatedResponse, AnnStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ann", tags=["ann"])


# ---------------------------------------------------------------------------
# POST /ann/request
# ---------------------------------------------------------------------------


@router.post("/request", response_model=AnnRequestCreatedResponse, status_code=202)
async def create_ann_request(
    payload: AnnRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    ulid_str = str(ULID())

    record = AnnRequest(
        ulid=ulid_str,
        callback_url=payload.callback_url,
        use_complex_model=payload.use_complex_model,
        status="PENDING",
        published=False,
    )
    db.add(record)
    await db.commit()

    logger.info("Created ANN request %s", ulid_str)
    return AnnRequestCreatedResponse(ulid=ulid_str, status="PENDING")


# ---------------------------------------------------------------------------
# GET /ann/status/{ulid}
# ---------------------------------------------------------------------------


@router.get("/status/{ulid}", response_model=AnnStatusResponse)
async def get_ann_status(
    ulid: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(AnnRequest).where(AnnRequest.ulid == ulid)
    )
    record: AnnRequest | None = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="ANN request not found")

    return AnnStatusResponse(
        ulid=record.ulid,
        status=record.status,
        model_name=record.model_name,
    )


# ---------------------------------------------------------------------------
# GET /ann/model/{ulid}
# ---------------------------------------------------------------------------


@router.get("/model/{ulid}")
async def download_model(
    ulid: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Verify the record exists and is completed.
    result = await db.execute(
        select(AnnRequest).where(AnnRequest.ulid == ulid)
    )
    record: AnnRequest | None = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="ANN request not found")

    if record.status != "COMPLETED" or record.model_name is None:
        raise HTTPException(
            status_code=409,
            detail=f"Model not ready yet (status={record.status})",
        )

    # Stream the file from MongoDB GridFS.
    mongo_db = get_mongo_db()
    bucket = AsyncIOMotorGridFSBucket(mongo_db)

    try:
        grid_out = await bucket.open_download_stream_by_name(record.model_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Model file not found in GridFS")

    async def _stream():
        while True:
            chunk = await grid_out.read(65536)
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.model_name}"'
        },
    )
