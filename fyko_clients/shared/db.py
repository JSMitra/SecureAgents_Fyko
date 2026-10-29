"""
db.py — Synchronous helpers for PostgreSQL and MongoDB.

PostgreSQL  → stores RSA public keys in `agent_keys`
MongoDB     → Secret Plan Creator logs queries in `query_logs`
"""

import os
import logging
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

_POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://fyko:fykopass@postgres:5432/fykoDb")


def _get_pg_conn():
    """Open a new psycopg2 connection (caller responsible for closing)."""
    return psycopg2.connect(_POSTGRES_URL)


def ensure_agent_keys_table() -> None:
    """
    Create the `agent_keys` table if it does not already exist.
    Safe to call on every startup.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS agent_keys (
        agent_name  VARCHAR(100) PRIMARY KEY,
        public_key_pem TEXT NOT NULL,
        created_at  TIMESTAMP DEFAULT NOW()
    );
    """
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    logger.info("agent_keys table ensured.")


def upsert_agent_public_key(agent_name: str, public_key_pem: str) -> None:
    """
    Insert or update the public key PEM for *agent_name*.
    Uses PostgreSQL UPSERT so it is idempotent on restarts.
    """
    sql = """
    INSERT INTO agent_keys (agent_name, public_key_pem, created_at)
    VALUES (%s, %s, %s)
    ON CONFLICT (agent_name) DO UPDATE
        SET public_key_pem = EXCLUDED.public_key_pem,
            created_at     = EXCLUDED.created_at;
    """
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (agent_name, public_key_pem, datetime.now(timezone.utc)))
        conn.commit()
    logger.info("Upserted public key for agent '%s'.", agent_name)


def fetch_agent_public_key(agent_name: str) -> str | None:
    """
    Return the public key PEM for *agent_name*, or None if not found.
    """
    sql = "SELECT public_key_pem FROM agent_keys WHERE agent_name = %s;"
    with _get_pg_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (agent_name,))
            row = cur.fetchone()
    if row is None:
        logger.warning("No public key found for agent '%s'.", agent_name)
        return None
    return row["public_key_pem"]


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------

_MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://fyko:fykopass@mongodb:27017/")
_MONGO_DB    = "fykoDb"
_MONGO_COLL  = "query_logs"

_mongo_client: MongoClient | None = None


def _get_mongo_collection():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(_MONGODB_URL)
    return _mongo_client[_MONGO_DB][_MONGO_COLL]


def log_query(
    ulid: str,
    query: str,
    response: str,
    ann_model_ulid: str,
) -> None:
    """
    Insert a query-log document into MongoDB `query_logs`.
    Called by Secret Plan Creator after receiving the reviewer's answer.
    """
    doc = {
        "ulid": ulid,
        "query": query,
        "response": response,
        "ann_model_ulid": ann_model_ulid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _get_mongo_collection().insert_one(doc)
    logger.info("Logged query '%s' to MongoDB.", ulid)
