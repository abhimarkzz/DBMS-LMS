"""
Database Session Management

Configures the async SQLAlchemy engine and session factory.
Using asyncpg driver for full async PostgreSQL support.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# The engine manages the connection pool.
# pool_pre_ping=True tests connections before using them — prevents
# "connection closed" errors after the DB restarts or idle timeout.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=not settings.is_production,  # Log SQL in development only
)

# Session factory — creates sessions bound to the engine.
# expire_on_commit=False prevents SQLAlchemy from expiring ORM objects
# after commit, which would cause lazy-load errors in async contexts.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Called at startup to verify the database connection is working.
    Does NOT run migrations — migrations are handled by the SQL scripts
    in database/postgres/migrations/.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully.")
    except Exception as exc:
        logger.error("Could not connect to database: %s", exc)
        raise


async def check_db_connection() -> bool:
    """
    Quick connectivity check used by the /ready health endpoint.
    Returns True if the DB is reachable, False otherwise.
    Does NOT raise — the caller decides what to do with the result.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
