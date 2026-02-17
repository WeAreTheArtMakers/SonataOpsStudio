from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.clickhouse.client import get_clickhouse
from app.clickhouse.ingest import clickhouse_rows_from_points
from app.config import get_settings
from app.db.postgres import execute, fetch
from app.metrics import clickhouse_ingest_rows_total, kpi_ingest_total

router = APIRouter(tags=["kpis"])


class KpiPointIn(BaseModel):
    timestamp: datetime
    metric_name: str
    value: float
    tags: dict[str, Any] = Field(default_factory=dict)


class KpiIngestRequest(BaseModel):
    workspace_id: str | None = None
    points: list[KpiPointIn]


@router.post("/kpis/ingest")
async def ingest_kpis(payload: KpiIngestRequest) -> dict[str, object]:
    settings = get_settings()
    workspace_id = payload.workspace_id or settings.default_workspace_id
    if not payload.points:
        raise HTTPException(status_code=400, detail="points cannot be empty")

    points = [
        {
            "workspace_id": workspace_id,
            "timestamp": item.timestamp,
            "metric_name": item.metric_name,
            "value": item.value,
            "tags": item.tags,
        }
        for item in payload.points
    ]

    clickhouse = get_clickhouse()
    await asyncio.to_thread(clickhouse.insert_kpi_points, clickhouse_rows_from_points(points))

    for point in points:
        await execute(
            """
            INSERT INTO kpi_points_recent (workspace_id, metric_name, ts, value, tags)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            point["workspace_id"],
            point["metric_name"],
            point["timestamp"],
            float(point["value"]),
            json.dumps(point.get("tags", {})),
        )

    # Keep operational copy bounded per workspace+metric.
    metrics = sorted({point["metric_name"] for point in points})
    for metric in metrics:
        await execute(
            """
            DELETE FROM kpi_points_recent
            WHERE id IN (
                SELECT id
                FROM kpi_points_recent
                WHERE workspace_id = $1 AND metric_name = $2
                ORDER BY ts DESC
                OFFSET $3
            )
            """,
            workspace_id,
            metric,
            get_settings().max_recent_operational_points,
        )

    kpi_ingest_total.inc(len(points))
    clickhouse_ingest_rows_total.inc(len(points))

    return {
        "workspace_id": workspace_id,
        "ingested": len(points),
        "metrics": metrics,
    }


@router.get("/kpis/recent")
async def list_recent_kpis(
    metric: str | None = Query(default=None),
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, object]:
    if metric:
        rows = await fetch(
            """
            SELECT metric_name, ts, value, tags
            FROM kpi_points_recent
            WHERE workspace_id = $1 AND metric_name = $2
            ORDER BY ts DESC
            LIMIT $3
            """,
            workspace_id,
            metric,
            limit,
        )
    else:
        rows = await fetch(
            """
            SELECT metric_name, ts, value, tags
            FROM kpi_points_recent
            WHERE workspace_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            workspace_id,
            limit,
        )

    data = [
        {
            "metric_name": row["metric_name"],
            "timestamp": row["ts"].isoformat(),
            "value": float(row["value"]),
            "tags": row["tags"],
        }
        for row in rows
    ]
    return {"workspace_id": workspace_id, "items": data}


@router.get("/analytics/kpi")
async def analytics_kpi(
    metric: str,
    minutes: int = Query(default=180, ge=5, le=10080),
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    clickhouse = get_clickhouse()
    rows = await asyncio.to_thread(clickhouse.kpi_rollups, workspace_id, metric, minutes)
    return {"workspace_id": workspace_id, "metric": metric, "rows": rows}


@router.get("/analytics/anomalies")
async def analytics_anomalies(
    minutes: int = Query(default=1440, ge=15, le=10080),
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    clickhouse = get_clickhouse()
    data = await asyncio.to_thread(clickhouse.anomalies_analytics, workspace_id, minutes)
    return {"workspace_id": workspace_id, **data}


@router.get("/analytics/audio")
async def analytics_audio(
    minutes: int = Query(default=1440, ge=15, le=10080),
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    clickhouse = get_clickhouse()
    data = await asyncio.to_thread(clickhouse.audio_analytics, workspace_id, minutes)
    return {"workspace_id": workspace_id, "rows": data}
