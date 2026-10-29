"""
agent.py — Secret Plan Reviewer core logic.

Responsibilities:
  1. RSA key-pair generation + registration in PostgreSQL on startup.
  2. Process incoming A2A tasks (queued via RabbitMQ):
       - "key_share" task: RSA-decrypt key material, download ANN model,
         store in memory keyed by key_share_task_id.
       - "query" task: AES-decrypt the question using the stored model,
         call Gemini to answer, AES-encrypt the answer, return as artifact.
  3. Expose task status via in-memory dict.
"""

import asyncio
import base64
import json
import logging
import os
import pickle
import time

import aio_pika
import httpx
import google.generativeai as genai

from shared.crypto_utils import (
    generate_rsa_keypair,
    public_key_to_pem,
    rsa_decrypt,
)
from shared.fyko_ann import generate_aes_key, decrypt_with_aes, encrypt_with_aes
from shared.db import ensure_agent_keys_table, upsert_agent_public_key

logger = logging.getLogger(__name__)

FYKO_SERVER_URL = os.getenv("FYKO_SERVER_URL", "http://fyko-server:8000")
RABBITMQ_URL    = os.getenv("RABBITMQ_URL",    "amqp://fyko:fykopass@rabbitmq:5672/")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "")
AGENT_NAME      = "secret_plan_reviewer"
QUEUE_NAME      = "reviewer_tasks"

# ── Gemini setup ──────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-2.0-flash")


def _gemini(prompt: str) -> str:
    try:
        resp = _gemini_model.generate_content(prompt)
        return resp.text.strip()
    except Exception as exc:
        logger.error("Gemini error: %s", exc)
        return "Intelligence unavailable at this time."


# ── In-memory state ───────────────────────────────────────────────────────────

# tasks: task_id → {"status": {"state": ...}, "artifacts": [...]}
tasks: dict[str, dict] = {}

# key_sessions: key_share_task_id → {"model": <keras model>, "random_string": str, "utc_time": int}
key_sessions: dict[str, dict] = {}

# ── RSA key pair ──────────────────────────────────────────────────────────────
_private_key = None
_public_key  = None


def init_agent() -> None:
    """Called once at startup to register RSA key pair in PG."""
    global _private_key, _public_key
    _private_key, _public_key = generate_rsa_keypair()
    pub_pem = public_key_to_pem(_public_key)
    ensure_agent_keys_table()
    upsert_agent_public_key(AGENT_NAME, pub_pem)
    logger.info("Secret Plan Reviewer initialised (RSA key registered).")


# ── RabbitMQ worker ───────────────────────────────────────────────────────────

async def _process_message(message: aio_pika.IncomingMessage) -> None:
    """
    Callback invoked for each RabbitMQ message on the reviewer_tasks queue.
    The message body is a JSON blob with the full A2A task dict.
    """
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            task_id  = body["id"]
            text_parts = body.get("message", {}).get("parts", [])
            text = next(
                (p["text"] for p in text_parts if p.get("type") == "text"), ""
            )
            payload = json.loads(text)
            task_type = payload.get("type")

            if task_type == "key_share":
                await _handle_key_share(task_id, payload)
            elif task_type == "query":
                await _handle_query(task_id, payload)
            else:
                logger.warning("Unknown task type '%s' for task %s.", task_type, task_id)
                tasks[task_id] = {
                    "id": task_id,
                    "status": {"state": "failed"},
                    "artifacts": [{"parts": [{"type": "text", "text": f"Unknown task type: {task_type}"}]}],
                }
        except Exception as exc:
            logger.exception("Error processing task: %s", exc)
            try:
                tasks[task_id]["status"] = {"state": "failed"}
            except Exception:
                pass


async def _handle_key_share(task_id: str, payload: dict) -> None:
    """
    Decrypt the key material from Creator, download the ANN model, store in
    key_sessions keyed by task_id.
    """
    try:
        encrypted_b64 = payload["payload"]
        encrypted_bytes = base64.b64decode(encrypted_b64)
        key_material_json = rsa_decrypt(encrypted_bytes, _private_key)
        key_material = json.loads(key_material_json)

        model_ulid    = key_material["model_ulid"]
        random_string = key_material["random_string"]
        utc_time      = key_material["utc_time"]

        # Download model from FykoServer
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(f"{FYKO_SERVER_URL}/ann/model/{model_ulid}")
            resp.raise_for_status()
            model = pickle.loads(resp.content)

        key_sessions[task_id] = {
            "model":         model,
            "random_string": random_string,
            "utc_time":      utc_time,
        }
        tasks[task_id] = {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [{"parts": [{"type": "text", "text": "key_share_accepted"}]}],
        }
        logger.info("key_share task %s processed; model %s loaded.", task_id, model_ulid)
    except Exception as exc:
        logger.exception("key_share task %s failed: %s", task_id, exc)
        tasks[task_id] = {
            "id": task_id,
            "status": {"state": "failed"},
            "artifacts": [{"parts": [{"type": "text", "text": str(exc)}]}],
        }


async def _handle_query(task_id: str, payload: dict) -> None:
    """
    Decrypt the query, call Gemini, encrypt the answer, store as artifact.
    """
    try:
        key_share_task_id = payload["key_share_task_id"]
        encrypted_query   = payload["payload"]

        # Wait for the key_session to be ready (in case tasks arrive out of order)
        deadline = time.time() + 60.0
        while key_share_task_id not in key_sessions:
            if time.time() > deadline:
                raise TimeoutError(
                    f"key_session for key_share_task_id={key_share_task_id} not ready."
                )
            await asyncio.sleep(1.0)

        session       = key_sessions[key_share_task_id]
        model         = session["model"]
        random_string = session["random_string"]
        utc_time      = session["utc_time"]

        # Regenerate AES key (deterministic from same inputs)
        aes_key_hex = generate_aes_key(model, random_string, utc_time)

        # Decrypt the query
        plain_query = decrypt_with_aes(encrypted_query, aes_key_hex)
        logger.info("Decrypted query for task %s: %s", task_id, plain_query[:80])

        # Ask Gemini
        answer = _gemini(
            f"""You are a knowledgeable film critic and analyst.
Answer the following question about recent movies concisely and accurately
(aim for 3-5 sentences):

{plain_query}"""
        )

        # Encrypt the answer
        encrypted_answer = encrypt_with_aes(answer, aes_key_hex)

        tasks[task_id] = {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [{"parts": [{"type": "text", "text": encrypted_answer}]}],
        }
        logger.info("Query task %s completed.", task_id)
    except Exception as exc:
        logger.exception("Query task %s failed: %s", task_id, exc)
        tasks[task_id] = {
            "id": task_id,
            "status": {"state": "failed"},
            "artifacts": [{"parts": [{"type": "text", "text": str(exc)}]}],
        }


async def start_rabbitmq_consumer(app) -> None:
    """
    Connect to RabbitMQ, declare the queue, and start consuming.
    Stores the connection on `app.state` so the shutdown hook can close it.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel    = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(QUEUE_NAME, durable=False)
    await queue.consume(_process_message)

    app.state.rabbitmq_connection = connection
    logger.info("RabbitMQ consumer started on queue '%s'.", QUEUE_NAME)


async def stop_rabbitmq_consumer(app) -> None:
    conn = getattr(app.state, "rabbitmq_connection", None)
    if conn and not conn.is_closed:
        await conn.close()
        logger.info("RabbitMQ connection closed.")


async def enqueue_task(task: dict) -> None:
    """
    Publish a task dict to the RabbitMQ reviewer_tasks queue.
    Opens a short-lived connection — suitable for the low-volume A2A POST handler.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(QUEUE_NAME, durable=False)
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(task).encode()),
            routing_key=QUEUE_NAME,
        )
    logger.info("Enqueued task %s.", task.get("id"))
