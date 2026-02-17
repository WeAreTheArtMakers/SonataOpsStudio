from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.events import emit_realtime_event
from app.config import get_settings
from app.db.postgres import execute, fetch, fetchrow

router = APIRouter(tags=["anomalies"])


class CorrelationIn(BaseModel):
    summary: str
    sources: list[dict[str, object]] = Field(default_factory=list)


class CorrelationsRequest(BaseModel):
    workspace_id: str | None = None
    correlations: list[CorrelationIn]


@router.get("/anomalies")
async def list_anomalies(
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
    metric: str | None = Query(default=None),
    severity_min: int = Query(default=0, ge=0, le=100),
    minutes: int = Query(default=1440, ge=5, le=10080),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, object]:
    if metric:
        rows = await fetch(
            f"""
            SELECT anomaly_id, metric_name, window_start, window_end, severity, features, correlations, detected_at
            FROM anomalies
            WHERE workspace_id = $1
              AND severity >= $2
              AND metric_name = $3
              AND detected_at >= NOW() - INTERVAL '{minutes} minutes'
            ORDER BY detected_at DESC
            LIMIT $4
            """,
            workspace_id,
            severity_min,
            metric,
            limit,
        )
    else:
        rows = await fetch(
            f"""
            SELECT anomaly_id, metric_name, window_start, window_end, severity, features, correlations, detected_at
            FROM anomalies
            WHERE workspace_id = $1
              AND severity >= $2
              AND detected_at >= NOW() - INTERVAL '{minutes} minutes'
            ORDER BY detected_at DESC
            LIMIT $3
            """,
            workspace_id,
            severity_min,
            limit,
        )
    items = [
        {
            "anomaly_id": str(row["anomaly_id"]),
            "metric_name": row["metric_name"],
            "window_start": row["window_start"].isoformat(),
            "window_end": row["window_end"].isoformat(),
            "severity": int(row["severity"]),
            "features": row["features"],
            "correlations": row["correlations"],
            "detected_at": row["detected_at"].isoformat(),
        }
        for row in rows
    ]
    return {"workspace_id": workspace_id, "items": items}


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly(
    anomaly_id: str,
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    row = await fetchrow(
        """
        SELECT anomaly_id, metric_name, window_start, window_end, severity, features, correlations, detected_at
        FROM anomalies
        WHERE anomaly_id = $1::uuid AND workspace_id = $2
        """,
        anomaly_id,
        workspace_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="anomaly not found")

    return {
        "anomaly_id": str(row["anomaly_id"]),
        "metric_name": row["metric_name"],
        "window_start": row["window_start"].isoformat(),
        "window_end": row["window_end"].isoformat(),
        "severity": int(row["severity"]),
        "features": row["features"],
        "correlations": row["correlations"],
        "detected_at": row["detected_at"].isoformat(),
    }


@router.post("/anomalies/{anomaly_id}/correlations")
async def add_correlations(anomaly_id: str, payload: CorrelationsRequest) -> dict[str, object]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id

    current = await fetchrow(
        """
        SELECT correlations
        FROM anomalies
        WHERE anomaly_id = $1::uuid AND workspace_id = $2
        """,
        anomaly_id,
        workspace_id,
    )
    if not current:
        raise HTTPException(status_code=404, detail="anomaly not found")

    existing = list(current["correlations"])
    merged = existing + [item.model_dump() for item in payload.correlations]

    await execute(
        """
        UPDATE anomalies
        SET correlations = $3::jsonb
        WHERE anomaly_id = $1::uuid AND workspace_id = $2
        """,
        anomaly_id,
        workspace_id,
        json.dumps(merged),
    )

    await emit_realtime_event(
        workspace_id,
        "anomaly.correlated",
        {
            "anomaly_id": anomaly_id,
            "correlations": merged,
        },
    )

    return {"anomaly_id": anomaly_id, "correlations": merged}
