import aiosqlite
from fastapi import HTTPException
from contextlib import asynccontextmanager
from typing import Optional, AsyncContextManager, Tuple, Any
import atexit
import sys
import logging

from psycopg import AsyncConnection, AsyncCursor, AsyncServerCursor
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.config import DATABASE_URL
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============================================================================
#                       SQLITE COMPATIBILITY LAYER
# ============================================================================

class _SQLitePoolWrapper:
    """
    Mimics the psycopg_pool interface for an in-memory SQLite database.
    Since in-memory SQLite is wiped when the connection closes,
    we maintain a SINGLE persistent connection.
    """
    def __init__(self):
        self._conn: Optional[aiosqlite.Connection] = None
        self.min_size = 1
        self.max_size = 1

    async def open(self):
        self._conn = await aiosqlite.connect(":memory:")
        self._conn.row_factory = aiosqlite.Row
        logger.info("✓ SQLite in-memory database initialized.")

    async def close(self):
        if self._conn:
            await self._conn.close()
            logger.info("SQLite connection closed.")

    @asynccontextmanager
    async def connection(self):
        """Yields the shared connection."""
        if not self._conn:
            await self.open()
        yield self._conn

    def get_stats(self) -> dict:
        return {"status": "running", "mode": "sqlite_memory"}


# Global async connection pools
_async_db_pool: Optional[AsyncConnectionPool | _SQLitePoolWrapper] = None


async def _check_connection_healthy(conn: AsyncConnection):
    await conn.execute("SELECT 1;")

def _create_async_db_pool(conn_url: str):
    return AsyncConnectionPool(
        conninfo=conn_url,
        min_size=2,
        max_size=10,
        max_waiting=20,
        max_idle=300,
        timeout=30,
        open=False,
        check=_check_connection_healthy,
        kwargs={
            "row_factory": dict_row,
            "prepare_threshold": None,
        },
    )


async def get_async_db_pool() -> AsyncConnectionPool | _SQLitePoolWrapper:
    """Get or initialize the primary database connection pool."""
    global _async_db_pool
    if _async_db_pool:
        return _async_db_pool

    if not DATABASE_URL:
        logger.warning("⚠️ DATABASE_URL not found. Falling back to IN-MEMORY SQLite.")
        _async_db_pool = _SQLitePoolWrapper()
        await _async_db_pool.open()
        return _async_db_pool

    # Warn if using Session Mode (port 5432) for Postgres
    if ":5432/" in DATABASE_URL:
        logger.warning(
            "⚠️  DATABASE_URL is using port 5432 (Session Mode). "
            "This has very limited connections. "
            "Switch to port 6543 (Transaction Mode) for Supabase: "
            "DATABASE_URL=postgresql://...pooler.supabase.com:6543/postgres"
        )

    _async_db_pool = _create_async_db_pool(DATABASE_URL)
    await _async_db_pool.open()
    logger.info(f"✓ Primary database pool opened (size: {_async_db_pool.min_size}-{_async_db_pool.max_size})")
    return _async_db_pool


# ============================================================================
#                    CONNECTION-LEVEL CONTEXT MANAGERS
#           (Use for transactions, commit/rollback control)
# ============================================================================

@asynccontextmanager
async def get_async_db_connection() -> AsyncContextManager[AsyncConnection]:
    """
    Get an async connection to the primary database from the connection pool.

    Use this when you need:
    - Explicit transaction control (commit/rollback)
    - Multiple related statements that must succeed/fail together
    - Multi-table operations requiring transactional integrity

    Example:
        async with get_async_db_connection() as conn:
            cur = conn.cursor()
            await cur.execute("INSERT INTO users ...")
            await cur.execute("INSERT INTO profiles ...")
            await conn.commit()

    The connection is automatically returned to the pool when the context exits.
    """
    pool = await get_async_db_pool()
    conn = None
    try:
        async with pool.connection() as conn:
            yield conn
            await conn.commit()
    except Exception as exc:
        logger.error(f"Database error: {exc}")
        await conn.rollback()
        raise exc
    # Connection automatically returns to pool here


# ============================================================================
#                      CURSOR-LEVEL CONTEXT MANAGERS
#              (Use for read-only queries and simple operations)
# ============================================================================

@asynccontextmanager
async def get_async_db_cursor() -> AsyncContextManager[AsyncCursor | AsyncServerCursor]:
    """
    Get a cursor for read-only queries or simple single-statement operations.

    Use this when you need:
    - Single SELECT queries
    - Single INSERT/UPDATE/DELETE without transaction control
    - Read-only operations
    - Simple operations that don't require rollback

    Example:
        async with get_async_db_cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()

    ⚠️ WARNING: Each call gets a separate connection from the pool.
    Do NOT use this for multi-statement transactions - use get_async_db_connection() instead.
    The connection auto-commits on success.
    """
    async with get_async_db_connection() as conn:
        async with conn.cursor() as cur:
            yield cur


# ============================================================================
#                         CLEANUP AND LIFECYCLE
# ============================================================================

async def close_pools():
    """Close all connection pools gracefully."""
    global _async_db_pool

    if _async_db_pool is not None:
        logger.info("Closing primary database pool...")
        await _async_db_pool.close()
        _async_db_pool = None


@atexit.register
def _sync_close_pools():
    """Synchronous atexit fallback for async pool cleanup."""
    global _async_db_pool

    async def _close_all():
        if _async_db_pool is not None:
            await _async_db_pool.close()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_close_all())
        logger.info("Connection pools closed during shutdown")
    except Exception as e:
        logger.error(f"Error closing async pools during atexit: {e}")
    finally:
        loop.close()


# ============================================================================
#                         HEALTH CHECK & MONITORING
# ============================================================================

async def get_pool_stats() -> dict[str, int]:
    """Get current pool statistics for monitoring."""
    return _async_db_pool.get_stats()


__all__ = [
    # Direct pool access
    "get_async_db_pool",
    # Async connection-level (for transactions)
    "get_async_db_connection",
    # Async cursor-level (for simple queries)
    "get_async_db_cursor",
    # Lifecycle management
    "close_pools",
    "get_pool_stats",
]

if __name__ == '__main__':
    async def main():
        async with get_async_db_cursor() as cur:
            pass
        await close_pools()
    asyncio.run(main())
    print("done")