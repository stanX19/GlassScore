from __future__ import annotations

import asyncio
import atexit
from typing import Optional

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver, BasePostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from openpyxl.descriptors import Typed
from psycopg_pool import AsyncConnectionPool

from src.database import get_async_db_pool

_already_set_up: bool = False


async def _get_saver() -> AsyncPostgresSaver | InMemorySaver:
    pool = await get_async_db_pool()
    if isinstance(pool, AsyncConnectionPool):
        return AsyncPostgresSaver(conn=pool)
    else:
        return InMemorySaver()

async def ensure_setup():
    global _already_set_up

    if _already_set_up:
        return
    _already_set_up = True
    saver = await _get_saver()
    if isinstance(saver, AsyncPostgresSaver):
        await saver.setup()

async def get_chat_postgres_saver_async() -> AsyncPostgresSaver:
    """
    Asynchronous PostgresSaver using a shared asyncpg pool.
    Reuses the pool for performance and connection safety.
    """
    await ensure_setup()
    return await _get_saver()

