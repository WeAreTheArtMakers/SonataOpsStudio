from __future__ import annotations

import json
import math
import random
from datetime import timedelta
from typing import Any

from app.clickhouse.client import get_clickhouse
from app.clickhouse.ingest import clickhouse_rows_from_points
from app.db.postgres import execute
from app.utils.time import utcnow


async def seed_demo(workspace_id: str) -> dict[str, Any]:
    now = utcnow()
    metrics = ["Sales", "RiskScore", "Traffic", "Latency"]
    points: list[dict[str, Any]] = []

    for minute in range(0, 360):
        ts = now - timedelta(minutes=360 - minute)
        for metric in metrics:
            base = {
                "Sales": 180.0,
                "RiskScore": 40.0,
                "Traffic": 1200.0,
                "Latency": 95.0,
            }[metric]
            seasonal = {
                "Sales": math.sin(minute / 22) * 15,
                "RiskScore": math.sin(minute / 15) * 8,
                "Traffic": math.sin(minute / 9) * 160,
                "Latency": math.sin(minute / 11) * 13,
            }[metric]
            noise = random.Random(f"{metric}:{minute}").uniform(-4, 4)
            value = base + seasonal + noise
            if minute % 87 == 0 and metric in {"RiskScore", "Latency"}:
                value += 28
            points.append(
                {
                    "workspace_id": workspace_id,
                    "timestamp": ts,
                    "metric_name": metric,
                    "value": float(round(value, 3)),
                    "tags": {
                        "region": "NA",
                        "channel": "demo",
                    },
                }
            )

    clickhouse = get_clickhouse()
    clickhouse.insert_kpi_points(clickhouse_rows_from_points(points))

    await execute("DELETE FROM kpi_points_recent WHERE workspace_id = $1", workspace_id)
    insert_sql = """
    INSERT INTO kpi_points_recent (workspace_id, metric_name, ts, value, tags)
    VALUES ($1, $2, $3, $4, $5::jsonb)
    """
    for point in points[-1200:]:
        await execute(
            insert_sql,
            point["workspace_id"],
            point["metric_name"],
            point["timestamp"],
            point["value"],
            json.dumps(point["tags"]),
        )

    docs = [
        {
            "title": "Release Notes - Payments v3.2",
            "text": "2026-02-16 deployment introduced retry backoff changes. RiskScore spikes were observed for 15 minutes after rollout.",
            "source_url": "internal://release-notes/payments-v3-2",
            "meta": {"type": "release_notes", "team": "platform"},
        },
        {
            "title": "Campaign Calendar - Q1",
            "text": "Major acquisition campaign launched 09:00 UTC, expected traffic increase 18-24 percent for North America and EMEA.",
            "source_url": "internal://marketing/calendar-q1",
            "meta": {"type": "campaign_calendar", "owner": "marketing"},
        },
        {
            "title": "Runbook - Latency Spikes",
            "text": "If latency exceeds baseline by 20 percent with increased traffic, validate CDN invalidation backlog and database connection saturation.",
            "source_url": "internal://runbooks/latency-spikes",
            "meta": {"type": "runbook", "service": "edge"},
        },
    ]

    await execute(
        """
        INSERT INTO rag_eval_cases (workspace_id, question, expected_keywords, expected_sources)
        VALUES
          ($1, 'Why did RiskScore increase after deployment?', ARRAY['deployment', 'retry', 'risk'], ARRAY['release', 'runbook']),
          ($1, 'What explains the Traffic surge today?', ARRAY['campaign', 'traffic'], ARRAY['campaign']),
          ($1, 'How should we respond to Latency anomalies?', ARRAY['latency', 'cdn', 'database'], ARRAY['runbook'])
        ON CONFLICT (workspace_id, question) DO NOTHING
        """,
        workspace_id,
    )

    return {
        "seeded_points": len(points),
        "docs": docs,
        "workspace_id": workspace_id,
    }
