"""
Database setup: SQLAlchemy async (PostgreSQL via asyncpg) + Motor (MongoDB).

PostgreSQL schema (applied at startup):
    CREATE TABLE IF NOT EXISTS ann_requests (
        ulid VARCHAR(26) PRIMARY KEY,
        callback_url TEXT NOT NULL,
        use_complex_model BOOLEAN DEFAULT FALSE,
        status VARCHAR(20) DEFAULT 'PENDING',
        published BOOLEAN DEFAULT FALSE,
        model_name VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
"""

import os

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# PostgreSQL (asyncpg)
# ---------------------------------------------------------------------------

POSTGRES_URL: str = os.environ.get(
    "POSTGRES_URL",
    "postgresql+asyncpg://fyko:fykopass@postgres:5432/fykoDb",
)

engine = create_async_engine(POSTGRES_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create tables if they do not exist and run the DDL."""
    from sqlalchemy import text  # local import to avoid circular issues

    async with engine.begin() as conn:
        # Use raw DDL so we stay compatible with the exact schema specified.
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ann_requests (
                    ulid VARCHAR(26) PRIMARY KEY,
                    callback_url TEXT NOT NULL,
                    use_complex_model BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    published BOOLEAN DEFAULT FALSE,
                    model_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
        )


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that provides an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# MongoDB (Motor)
# ---------------------------------------------------------------------------

MONGODB_URL: str = os.environ.get(
    "MONGODB_URL",
    "mongodb://fyko:fykopass@mongodb:27017/",
)

_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
    return _mongo_client


def get_mongo_db():
    """Return the 'fyko' database handle."""
    return get_mongo_client()["fyko"]
