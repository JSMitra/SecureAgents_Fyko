"""
ANN Generator Worker
====================

Subscribes to the ``ann_requests`` RabbitMQ queue, generates a FYKO ANN model,
persists it to MongoDB GridFS, updates PostgreSQL, and notifies the Fyko Server.

Environment variables:
    RABBITMQ_URL      amqp://fyko:fykopass@rabbitmq:5672/
    MONGODB_URL       mongodb://fyko:fykopass@mongodb:27017/
    POSTGRES_URL_SYNC postgresql://fyko:fykopass@postgres:5432/fykoDb
    FYKO_SERVER_URL   http://fyko-server:8000
    WORKER_ID         unique worker identifier (set via K8s downward API)
"""

import io
import json
import logging
import os
import pickle
import sys
import time

import gridfs
import pika
import psycopg2
import requests
from pymongo import MongoClient

from ann_builder import generate_ANN

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] worker=%(worker_id)s %(message)s",
)

WORKER_ID: str = os.environ.get("WORKER_ID", "worker-unknown")

# Add worker_id to every log record automatically.
_old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    record.worker_id = WORKER_ID
    return record


logging.setLogRecordFactory(_record_factory)

logger = logging.getLogger(__name__)

RABBITMQ_URL: str = os.environ.get(
    "RABBITMQ_URL", "amqp://fyko:fykopass@rabbitmq:5672/"
)
MONGODB_URL: str = os.environ.get(
    "MONGODB_URL", "mongodb://fyko:fykopass@mongodb:27017/"
)
POSTGRES_URL_SYNC: str = os.environ.get(
    "POSTGRES_URL_SYNC", "postgresql://fyko:fykopass@postgres:5432/fykoDb"
)
FYKO_SERVER_URL: str = os.environ.get("FYKO_SERVER_URL", "http://fyko-server:8000")

QUEUE_NAME = "ann_requests"

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_pg_conn():
    """Return a new psycopg2 connection (caller is responsible for closing)."""
    return psycopg2.connect(POSTGRES_URL_SYNC)


def _mark_completed(ulid: str, model_name: str) -> None:
    """Update ann_requests row to COMPLETED in PostgreSQL."""
    conn = _get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE ann_requests
                       SET status = 'COMPLETED',
                           model_name = %s,
                           updated_at = NOW()
                     WHERE ulid = %s
                    """,
                    (model_name, ulid),
                )
        logger.info("PostgreSQL: marked %s COMPLETED", ulid)
    finally:
        conn.close()


def _save_model_to_gridfs(ulid: str, model) -> str:
    """Pickle the Keras model and store it in MongoDB GridFS.

    Returns the filename used (``{ulid}.pkl``).
    """
    filename = f"{ulid}.pkl"
    client = MongoClient(MONGODB_URL)
    try:
        db = client["fyko"]
        fs = gridfs.GridFS(db)

        # Serialise model to bytes in memory.
        buf = io.BytesIO()
        pickle.dump(model, buf)
        buf.seek(0)

        # Remove any existing file with the same name (idempotent retry safety).
        for old in fs.find({"filename": filename}):
            fs.delete(old._id)

        fs.put(buf.read(), filename=filename)
        logger.info("GridFS: stored %s", filename)
    finally:
        client.close()

    return filename


def _notify_fyko_server(ulid: str, model_name: str) -> None:
    """POST to /internal/model-ready on the Fyko Server."""
    url = f"{FYKO_SERVER_URL}/internal/model-ready"
    payload = {"ulid": ulid, "model_name": model_name}
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    logger.info("Fyko Server notified for %s (HTTP %d)", ulid, resp.status_code)


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


def _handle_message(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
) -> None:
    try:
        data = json.loads(body.decode())
        ulid: str = data["ulid"]
        use_complex_model: bool = bool(data.get("use_complex_model", False))
        logger.info("Received job: ulid=%s use_complex_model=%s", ulid, use_complex_model)

        # 1. Generate the ANN model.
        logger.info("Generating ANN for %s …", ulid)
        model = generate_ANN(use_complex_model=use_complex_model)

        # 2. Persist to MongoDB GridFS.
        model_name = _save_model_to_gridfs(ulid, model)

        # 3. Update PostgreSQL.
        _mark_completed(ulid, model_name)

        # 4. Notify Fyko Server.
        _notify_fyko_server(ulid, model_name)

        # 5. Acknowledge the message only after all steps succeed.
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Job %s completed and ACKed.", ulid)

    except Exception as exc:
        logger.exception("Failed to process message: %s", exc)
        # Negative-acknowledge without requeue to avoid poison-pill loops.
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ---------------------------------------------------------------------------
# RabbitMQ connection with retry
# ---------------------------------------------------------------------------


def _connect_rabbitmq(retries: int = 10, delay: float = 5.0) -> pika.BlockingConnection:
    params = pika.URLParameters(RABBITMQ_URL)
    for attempt in range(1, retries + 1):
        try:
            conn = pika.BlockingConnection(params)
            logger.info("Connected to RabbitMQ (attempt %d)", attempt)
            return conn
        except pika.exceptions.AMQPConnectionError as exc:
            if attempt == retries:
                logger.error("Could not connect to RabbitMQ after %d attempts", retries)
                raise
            logger.warning(
                "RabbitMQ not ready (attempt %d/%d): %s — retrying in %.1fs",
                attempt,
                retries,
                exc,
                delay,
            )
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("ANN Generator Worker starting (id=%s)", WORKER_ID)

    connection = _connect_rabbitmq()
    channel = connection.channel()

    # Declare the same non-durable queue the server publishes to.
    channel.queue_declare(queue=QUEUE_NAME, durable=False)

    # Process one message at a time (exclusive processing per instance).
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_handle_message)

    logger.info("Waiting for messages on queue '%s' …", QUEUE_NAME)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Interrupted — stopping worker.")
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()
