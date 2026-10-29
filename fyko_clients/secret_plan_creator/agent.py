"""
agent.py — Secret Plan Creator core logic.

Responsibilities:
  1. RSA key-pair generation + registration in PostgreSQL on startup.
  2. Handle a human user's movie-related question (/interact):
       a. Request ANN from FykoServer (callback or poll until ready)
       b. Download .pkl model, derive AES key
       c. RSA-encrypt key material → send to Reviewer via A2A
       d. AES-encrypt user query   → send to Reviewer via A2A
       e. Poll Reviewer for answer, decrypt, log to MongoDB, return to user
  3. Handle POST /ann-callback from FykoServer.
  4. Use Gemini LLM to refine vague queries and prettify responses.
"""

import asyncio
import base64
import io
import json
import logging
import os
import pickle
import time
import uuid
from typing import Optional

import httpx
import google.generativeai as genai
from python_ulid import ULID

from shared.crypto_utils import (
    generate_rsa_keypair,
    public_key_to_pem,
    rsa_encrypt,
    load_public_key_from_pem,
)
from shared.fyko_ann import generate_aes_key, encrypt_with_aes, decrypt_with_aes
from shared.db import (
    ensure_agent_keys_table,
    upsert_agent_public_key,
    fetch_agent_public_key,
    log_query,
)

logger = logging.getLogger(__name__)

FYKO_SERVER_URL = os.getenv("FYKO_SERVER_URL", "http://fyko-server:8000")
REVIEWER_URL    = os.getenv("REVIEWER_URL",    "http://secret-plan-reviewer:9002")
CREATOR_URL     = os.getenv("CREATOR_URL",     "http://secret-plan-creator:9001")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "")
AGENT_NAME      = "secret_plan_creator"

# ── Gemini setup ──────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-2.0-flash")


def _gemini(prompt: str) -> str:
    """Call Gemini and return the text response."""
    try:
        resp = _gemini_model.generate_content(prompt)
        return resp.text.strip()
    except Exception as exc:
        logger.error("Gemini error: %s", exc)
        return prompt  # fall back to unmodified text


# ── In-memory state ───────────────────────────────────────────────────────────

# ann_callbacks: ulid → {"status": "PENDING"|"COMPLETED", "model": <bytes|None>}
ann_callbacks: dict[str, dict] = {}

# ── RSA key pair (generated at startup) ───────────────────────────────────────
_private_key = None
_public_key  = None


def init_agent() -> None:
    """
    Called once at application startup:
      - Generate RSA-2048 key pair
      - Ensure PG table exists
      - Register public key in PG
    """
    global _private_key, _public_key
    _private_key, _public_key = generate_rsa_keypair()
    pub_pem = public_key_to_pem(_public_key)
    ensure_agent_keys_table()
    upsert_agent_public_key(AGENT_NAME, pub_pem)
    logger.info("Secret Plan Creator initialised (RSA key registered).")


# ── ANN helpers ───────────────────────────────────────────────────────────────

async def _request_ann() -> str:
    """
    POST to FykoServer to request a new ANN.
    Passes our callback URL and returns the ULID string.
    """
    callback_url = f"{CREATOR_URL}/ann-callback"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{FYKO_SERVER_URL}/ann/request",
            json={"callback_url": callback_url},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["ulid"]


async def _poll_ann_status(ulid: str, interval: float = 5.0, max_wait: float = 300.0) -> None:
    """
    Poll FykoServer every *interval* seconds until the ANN status is COMPLETED
    or *max_wait* seconds elapse.  Updates ann_callbacks[ulid].
    """
    deadline = time.time() + max_wait
    async with httpx.AsyncClient(timeout=30) as client:
        while time.time() < deadline:
            resp = await client.get(f"{FYKO_SERVER_URL}/ann/status/{ulid}")
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "PENDING")
                ann_callbacks[ulid] = ann_callbacks.get(ulid, {})
                ann_callbacks[ulid]["status"] = status
                if status == "COMPLETED":
                    logger.info("ANN %s ready (polled).", ulid)
                    return
            await asyncio.sleep(interval)
    raise TimeoutError(f"ANN {ulid} not ready after {max_wait}s.")


async def _wait_for_ann(ulid: str) -> None:
    """
    Wait for the ANN callback to arrive (set by /ann-callback endpoint).
    Falls back to polling if the callback hasn't arrived within 10 s.
    """
    deadline = time.time() + 10.0
    while time.time() < deadline:
        entry = ann_callbacks.get(ulid, {})
        if entry.get("status") == "COMPLETED":
            return
        await asyncio.sleep(1.0)
    # Fall back to polling
    await _poll_ann_status(ulid)


async def _download_model(ulid: str):
    """
    Download the .pkl model from FykoServer, unpickle, and return the Keras model.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(f"{FYKO_SERVER_URL}/ann/model/{ulid}")
        resp.raise_for_status()
        model = pickle.loads(resp.content)
    logger.info("Downloaded and unpickled model %s.", ulid)
    return model


# ── A2A helpers ───────────────────────────────────────────────────────────────

def _new_task_id() -> str:
    return str(ULID())


def _build_task(task_id: str, text: str) -> dict:
    return {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
        },
    }


async def _send_a2a_task(url: str, task: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{url}/a2a/tasks/send", json=task)
        resp.raise_for_status()
        return resp.json()


async def _poll_a2a_task(
    url: str,
    task_id: str,
    interval: float = 3.0,
    max_wait: float = 120.0,
) -> dict:
    """
    Poll GET /a2a/tasks/{task_id} until state is 'completed' or 'failed'.
    Returns the final task response dict.
    """
    deadline = time.time() + max_wait
    async with httpx.AsyncClient(timeout=30) as client:
        while time.time() < deadline:
            resp = await client.get(f"{url}/a2a/tasks/{task_id}")
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("status", {}).get("state", "working")
                if state in ("completed", "failed"):
                    return data
            await asyncio.sleep(interval)
    raise TimeoutError(f"A2A task {task_id} at {url} did not complete in {max_wait}s.")


def _extract_artifact_text(task_resp: dict) -> str:
    """Pull the first text part from the first artifact in an A2A response."""
    try:
        return task_resp["artifacts"][0]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Cannot extract artifact text from task response: {task_resp}") from exc


# ── Main interaction flow ─────────────────────────────────────────────────────

async def handle_user_message(raw_message: str) -> str:
    """
    Full end-to-end flow for a human user's movie question.
    Returns the final (decrypted, LLM-refined) answer as a string.
    """
    # ── Step 1: refine query with Gemini ─────────────────────────────────────
    refined_query = _gemini(
        f"""You are the Secret Plan Creator — an intelligence operative whose cover
is asking about the latest movies.  A contact sent you this message:

"{raw_message}"

Rewrite it as a crisp, specific question about recent movies (released in the
last 12 months) that an analyst could answer concisely.  Output only the
rewritten question, nothing else."""
    )
    logger.info("Refined query: %s", refined_query)

    # ── Step 2: request ANN from FykoServer ──────────────────────────────────
    model_ulid = await _request_ann()
    ann_callbacks[model_ulid] = {"status": "PENDING"}
    logger.info("ANN requested, ulid=%s", model_ulid)

    await _wait_for_ann(model_ulid)

    # ── Step 3: download model ────────────────────────────────────────────────
    model = await _download_model(model_ulid)

    # ── Step 4: derive AES key ────────────────────────────────────────────────
    random_string = str(uuid.uuid4())
    utc_time      = int(time.time())
    aes_key_hex   = generate_aes_key(model, random_string, utc_time)
    logger.info("AES key derived for model %s.", model_ulid)

    # ── Step 5: fetch Reviewer's RSA public key ───────────────────────────────
    reviewer_pub_pem = None
    for attempt in range(12):          # wait up to ~60 s for reviewer to register
        reviewer_pub_pem = fetch_agent_public_key("secret_plan_reviewer")
        if reviewer_pub_pem:
            break
        logger.warning("Reviewer public key not yet in PG, retrying (%d/12)…", attempt + 1)
        await asyncio.sleep(5)

    if not reviewer_pub_pem:
        raise RuntimeError("Secret Plan Reviewer public key not found in agent_keys.")

    reviewer_pub = load_public_key_from_pem(reviewer_pub_pem)

    # ── Step 6: RSA-encrypt key material → send to Reviewer ──────────────────
    key_material = json.dumps({
        "model_ulid":    model_ulid,
        "random_string": random_string,
        "utc_time":      utc_time,
    })
    encrypted_key_material = base64.b64encode(
        rsa_encrypt(key_material, reviewer_pub)
    ).decode()

    key_share_task_id = _new_task_id()
    key_share_payload = json.dumps({
        "type":    "key_share",
        "payload": encrypted_key_material,
    })
    key_share_task = _build_task(key_share_task_id, key_share_payload)
    await _send_a2a_task(REVIEWER_URL, key_share_task)
    logger.info("Key-share task sent: %s", key_share_task_id)

    # Poll until key_share is processed (Reviewer downloads the model)
    ks_resp = await _poll_a2a_task(REVIEWER_URL, key_share_task_id)
    if ks_resp.get("status", {}).get("state") == "failed":
        raise RuntimeError(f"Reviewer failed to process key_share: {ks_resp}")

    # ── Step 7: AES-encrypt query → send to Reviewer ─────────────────────────
    encrypted_query = encrypt_with_aes(refined_query, aes_key_hex)
    query_task_id   = _new_task_id()
    query_payload   = json.dumps({
        "type":             "query",
        "key_share_task_id": key_share_task_id,  # lets Reviewer find the right model
        "payload":           encrypted_query,
    })
    query_task = _build_task(query_task_id, query_payload)
    await _send_a2a_task(REVIEWER_URL, query_task)
    logger.info("Query task sent: %s", query_task_id)

    # ── Step 8: poll for encrypted answer ────────────────────────────────────
    query_resp = await _poll_a2a_task(REVIEWER_URL, query_task_id)
    if query_resp.get("status", {}).get("state") == "failed":
        raise RuntimeError(f"Reviewer failed to answer query: {query_resp}")

    encrypted_answer = _extract_artifact_text(query_resp)

    # ── Step 9: decrypt answer ────────────────────────────────────────────────
    raw_answer = decrypt_with_aes(encrypted_answer, aes_key_hex)

    # ── Step 10: log to MongoDB ───────────────────────────────────────────────
    interaction_ulid = str(ULID())
    log_query(
        ulid=interaction_ulid,
        query=refined_query,
        response=raw_answer,
        ann_model_ulid=model_ulid,
    )

    # ── Step 11: Gemini prettify ──────────────────────────────────────────────
    final_response = _gemini(
        f"""You are the Secret Plan Creator. You received this intelligence report
about recent movies:

"{raw_answer}"

Rewrite it in the voice of a suave intelligence operative sharing a briefing.
Keep it concise (≤ 150 words), engaging, and themed around movies as a cover
story. Output only the briefing text."""
    )

    return final_response


def handle_ann_callback(ulid: str, status: str) -> None:
    """
    Called by the /ann-callback endpoint when FykoServer POSTs a completion
    notification.
    """
    entry = ann_callbacks.get(ulid, {})
    entry["status"] = status
    ann_callbacks[ulid] = entry
    logger.info("ANN callback received: ulid=%s status=%s", ulid, status)
