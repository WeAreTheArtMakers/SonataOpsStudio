from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from opentelemetry import trace

from app.config import get_settings
from app.clickhouse.queries import (
    ANOMALY_ANALYTICS_QUERY,
    AUDIO_ANALYTICS_QUERY,
    KPI_ROLLUP_QUERY,
    SEVERITY_ANALYTICS_QUERY,
)

logger = logging.getLogger(__name__)

_ch: "ClickHouseService | None" = None


class ClickHouseService:
    def __init__(self) -> None:
        settings = get_settings()
        parsed = urlparse(settings.clickhouse_url)
        host = parsed.hostname or "clickhouse"
        port = parsed.port or 8123
        self.client: Client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
            self.client.command(stmt)

    def insert_kpi_points(self, rows: list[tuple[object, ...]]) -> None:
        if not rows:
            return
        tracer = trace.get_tracer("sonataops.clickhouse")
        with tracer.start_as_current_span("clickhouse.insert.kpi_points") as span:
            span.set_attribute("db.system", "clickhouse")
            span.set_attribute("db.operation", "insert")
            self.client.insert(
                "kpi_points_raw",
                rows,
                column_names=["workspace_id", "metric_name", "ts", "value", "tags"],
            )

    def insert_anomaly(self, row: tuple[object, ...]) -> None:
        self.client.insert(
            "anomalies_raw",
            [row],
            column_names=[
                "workspace_id",
                "anomaly_id",
                "metric_name",
                "window_start",
                "window_end",
                "severity",
                "features",
                "detected_at",
            ],
        )

    def insert_audio_render(self, row: tuple[object, ...]) -> None:
        self.client.insert(
            "audio_renders",
            [row],
            column_names=[
                "workspace_id",
                "artifact_id",
                "anomaly_id",
                "metric_name",
                "preset",
                "duration_seconds",
                "render_ms",
                "created_at",
            ],
        )

    def metric_names(self, workspace_id: str, minutes: int = 180) -> list[str]:
        result = self.client.query(
            """
            SELECT DISTINCT metric_name
            FROM kpi_points_raw
            WHERE workspace_id = %(workspace_id)s
              AND ts >= now() - toIntervalMinute(%(minutes)s)
            """,
            parameters={"workspace_id": workspace_id, "minutes": minutes},
        )
        return [str(row[0]) for row in result.result_rows]

    def recent_points(self, workspace_id: str, metric_name: str, minutes: int = 120) -> list[tuple[str, float]]:
        result = self.client.query(
            """
            SELECT ts, value
            FROM kpi_points_raw
            WHERE workspace_id = %(workspace_id)s
              AND metric_name = %(metric_name)s
              AND ts >= now() - toIntervalMinute(%(minutes)s)
            ORDER BY ts ASC
            """,
            parameters={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "minutes": minutes,
            },
        )
        return [(row[0], float(row[1])) for row in result.result_rows]

    def kpi_rollups(self, workspace_id: str, metric_name: str, minutes: int) -> list[dict[str, object]]:
        result = self.client.query(
            KPI_ROLLUP_QUERY,
            parameters={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "minutes": minutes,
            },
        )
        rows: list[dict[str, object]] = []
        for row in result.result_rows:
            rows.append(
                {
                    "bucket": row[0].isoformat(),
                    "avg": float(row[1]),
                    "min": float(row[2]),
                    "max": float(row[3]),
                    "points": int(row[4]),
                }
            )
        return rows

    def anomalies_analytics(self, workspace_id: str, minutes: int) -> dict[str, list[dict[str, object]]]:
        counts = self.client.query(
            ANOMALY_ANALYTICS_QUERY,
            parameters={"workspace_id": workspace_id, "minutes": minutes},
        )
        p95 = self.client.query(
            SEVERITY_ANALYTICS_QUERY,
            parameters={"workspace_id": workspace_id, "minutes": minutes},
        )

        return {
            "counts": [
                {
                    "metric": row[0],
                    "bucket": row[1].isoformat(),
                    "count": int(row[2]),
                }
                for row in counts.result_rows
            ],
            "severity_p95": [
                {
                    "metric": row[0],
                    "bucket": row[1].isoformat(),
                    "p95": float(row[2]),
                }
                for row in p95.result_rows
            ],
        }

    def audio_analytics(self, workspace_id: str, minutes: int) -> list[dict[str, object]]:
        result = self.client.query(
            AUDIO_ANALYTICS_QUERY,
            parameters={"workspace_id": workspace_id, "minutes": minutes},
        )
        return [
            {
                "metric": row[0],
                "preset": row[1],
                "renders": int(row[2]),
                "avg_render_ms": float(row[3]),
            }
            for row in result.result_rows
        ]

    def dump(self) -> str:
        return json.dumps({"status": "ok"})


def init_clickhouse() -> None:
    global _ch
    if _ch:
        return
    _ch = ClickHouseService()
    _ch.init_schema()
    logger.info("clickhouse initialized")


def get_clickhouse() -> ClickHouseService:
    if _ch is None:
        raise RuntimeError("clickhouse is not initialized")
    return _ch
