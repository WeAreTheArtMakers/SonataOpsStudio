from __future__ import annotations

from fastapi import APIRouter

from app.clickhouse.client import get_clickhouse
from app.db.postgres import fetchval
from app.storage.minio_client import get_minio

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    postgres_ok = False
    clickhouse_ok = False
    minio_ok = False

    try:
        _ = await fetchval("SELECT 1")
        postgres_ok = True
    except Exception:
        postgres_ok = False

    try:
        clickhouse_ok = get_clickhouse().dump() == '{"status": "ok"}'
    except Exception:
        clickhouse_ok = False

    try:
        minio_ok = get_minio().client.bucket_exists(get_minio().bucket)
    except Exception:
        minio_ok = False

    overall = postgres_ok and clickhouse_ok and minio_ok
    return {
        "status": "ok" if overall else "degraded",
        "postgres": postgres_ok,
        "clickhouse": clickhouse_ok,
        "minio": minio_ok,
    }
