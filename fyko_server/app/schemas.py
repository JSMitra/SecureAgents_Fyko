"""Pydantic schemas for request/response bodies."""

from typing import Optional

from pydantic import BaseModel, HttpUrl


# ---------------------------------------------------------------------------
# /ann/request
# ---------------------------------------------------------------------------


class AnnRequestCreate(BaseModel):
    callback_url: str
    use_complex_model: bool = False


class AnnRequestCreatedResponse(BaseModel):
    ulid: str
    status: str


# ---------------------------------------------------------------------------
# /ann/status/{ulid}
# ---------------------------------------------------------------------------


class AnnStatusResponse(BaseModel):
    ulid: str
    status: str
    model_name: Optional[str] = None


# ---------------------------------------------------------------------------
# /internal/model-ready
# ---------------------------------------------------------------------------


class ModelReadyPayload(BaseModel):
    ulid: str
    model_name: str


class ModelReadyResponse(BaseModel):
    ok: bool
