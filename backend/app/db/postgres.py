from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

import asyncpg
from opentelemetry import trace

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_postgres() -> None:
    global _pool
    if _pool:
        return

    settings = get_settings()
    _pool = await asyncpg.create_pool(
        settings.postgres_url,
        min_size=2,
        max_size=20,
        command_timeout=60,
    )

    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")
    async with _pool.acquire() as conn:
        # Serialize schema initialization across API and worker processes.
        lock_id = 842180019947
        await conn.execute("SELECT pg_advisory_lock($1)", lock_id)
        try:
            await conn.execute(schema_sql)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)

    logger.info("postgres initialized")


async def close_postgres() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def _require_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("postgres pool is not initialized")
    return _pool


async def execute(query: str, *args: Any) -> str:
    tracer = trace.get_tracer("sonataops.postgres")
    with tracer.start_as_current_span("postgres.execute") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", query[:300])
        pool = _require_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)


async def fetch(query: str, *args: Any) -> Sequence[asyncpg.Record]:
    tracer = trace.get_tracer("sonataops.postgres")
    with tracer.start_as_current_span("postgres.fetch") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", query[:300])
        pool = _require_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    tracer = trace.get_tracer("sonataops.postgres")
    with tracer.start_as_current_span("postgres.fetchrow") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", query[:300])
        pool = _require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args: Any) -> Any:
    tracer = trace.get_tracer("sonataops.postgres")
    with tracer.start_as_current_span("postgres.fetchval") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", query[:300])
        pool = _require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)


async def transaction(query: str, rows: list[tuple[Any, ...]]) -> None:
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(query, rows)
