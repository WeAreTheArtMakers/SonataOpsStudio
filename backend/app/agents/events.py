from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from statistics import median
from typing import Any

from app.agents.n8n_client import N8NClient
from app.clickhouse.client import get_clickhouse
from app.config import get_settings
from app.db.postgres import execute, fetch, fetchrow
from app.metrics import anomaly_detected_total, audio_render_total
from app.sonification.features import compute_anomaly_features
from app.sonification.mapping import map_features_to_control_curves
from app.sonification.sc_engine import create_mp3_preview, render_wav
from app.storage.artifacts import artifact_keys
from app.storage.minio_client import get_minio
from app.utils.ids import new_id
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


async def emit_realtime_event(workspace_id: str, event_type: str, payload: dict[str, Any]) -> None:
    await execute(
        """
        INSERT INTO realtime_events (workspace_id, event_type, payload)
        VALUES ($1, $2, $3::jsonb)
        """,
        workspace_id,
        event_type,
        json.dumps(payload),
    )


def _detect_anomaly_candidate(points: list[tuple[datetime, float]]) -> dict[str, Any] | None:
    if len(points) < 24:
        return None

    values = [float(v) for _, v in points]
    features = compute_anomaly_features(values)
    severity = int(features["severity"])

    # Require either strong robust z-score or residual anomaly to reduce noise.
    if not (
        features["robust_z"] >= 2.6
        or features["residual"] >= 2.4
        or (severity >= 70 and features["change_point"] >= 2.2)
    ):
        return None

    end_ts = points[-1][0]
    start_ts = points[max(0, len(points) - 20)][0]
    return {
        "window_start": start_ts,
        "window_end": end_ts,
        "severity": severity,
        "features": features,
    }


async def run_anomaly_detection_cycle(workspace_id: str, n8n: N8NClient) -> int:
    clickhouse = get_clickhouse()
    metrics = clickhouse.metric_names(workspace_id, minutes=240)
    created = 0

    for metric in metrics:
        raw_points = clickhouse.recent_points(workspace_id, metric, minutes=180)
        points: list[tuple[datetime, float]] = []
        for ts, value in raw_points:
            if isinstance(ts, str):
                normalized = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                normalized = ts
            if normalized.tzinfo is None:
                normalized = normalized.replace(tzinfo=timezone.utc)
            points.append((normalized, float(value)))

        candidate = _detect_anomaly_candidate(points)
        if not candidate:
            continue

        # Dedup in a short horizon.
        existing = await fetchrow(
            """
            SELECT anomaly_id, severity
            FROM anomalies
            WHERE workspace_id = $1 AND metric_name = $2
              AND window_end >= NOW() - INTERVAL '8 minutes'
            ORDER BY detected_at DESC
            LIMIT 1
            """,
            workspace_id,
            metric,
        )
        if existing and abs(int(existing["severity"]) - int(candidate["severity"])) <= 8:
            continue

        anomaly_id = new_id()
        await execute(
            """
            INSERT INTO anomalies (
                anomaly_id, workspace_id, metric_name,
                window_start, window_end, severity, features
            )
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7::jsonb)
            """,
            anomaly_id,
            workspace_id,
            metric,
            candidate["window_start"],
            candidate["window_end"],
            candidate["severity"],
            json.dumps(candidate["features"]),
        )

        clickhouse.insert_anomaly(
            (
                workspace_id,
                anomaly_id,
                metric,
                candidate["window_start"],
                candidate["window_end"],
                int(candidate["severity"]),
                json.dumps(candidate["features"]),
                utcnow(),
            )
        )

        anomaly_detected_total.labels(metric=metric).inc()
        created += 1

        event_payload = {
            "anomaly_id": anomaly_id,
            "workspace_id": workspace_id,
            "metric_name": metric,
            "severity": int(candidate["severity"]),
            "window_start": candidate["window_start"].isoformat(),
            "window_end": candidate["window_end"].isoformat(),
            "features": candidate["features"],
        }

        await emit_realtime_event(workspace_id, "anomaly.detected", event_payload)
        await n8n.anomaly_correlator(event_payload)
        if int(candidate["severity"]) >= 78:
            await n8n.incident_narrator(event_payload)

    return created


async def _claim_next_audio_job(workspace_id: str) -> dict[str, Any] | None:
    row = await fetchrow(
        """
        WITH candidate AS (
            SELECT job_id
            FROM audio_jobs
            WHERE workspace_id = $1 AND status = 'queued'
            ORDER BY created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE audio_jobs
        SET status = 'processing', updated_at = NOW()
        WHERE job_id = (SELECT job_id FROM candidate)
        RETURNING *
        """,
        workspace_id,
    )
    return dict(row) if row else None


async def run_audio_job_cycle(workspace_id: str) -> int:
    job = await _claim_next_audio_job(workspace_id)
    if not job:
        return 0

    clickhouse = get_clickhouse()
    minio = get_minio()

    try:
        metric = str(job["metric_name"])
        start_ts = job["start_ts"]
        end_ts = job["end_ts"]
        duration = int(job["duration_seconds"])
        preset = str(job["preset"])

        minutes = max(5, int((end_ts - start_ts).total_seconds() // 60) + 5)
        series = clickhouse.recent_points(workspace_id, metric, minutes=minutes)
        if not series:
            raise RuntimeError("no kpi points found for requested window")

        values = [float(v) for _, v in series]
        feature_pack = compute_anomaly_features(values)
        controls = map_features_to_control_curves(metric, feature_pack, preset)

        correlation_seed = abs(hash(str(job["correlation_id"]))) % 2_000_000
        wav_path, render_ms, engine = await render_wav(controls, duration, correlation_seed)
        mp3_path = await create_mp3_preview(wav_path)

        artifact_id = new_id()
        key_wav, key_mp3 = artifact_keys(workspace_id, metric, artifact_id)
        minio.upload_file(key_wav, wav_path, "audio/wav")
        minio.upload_file(key_mp3, mp3_path, "audio/mpeg")

        await execute(
            """
            INSERT INTO audio_artifacts (
                artifact_id, workspace_id, anomaly_id, metric_name, preset,
                duration_seconds, minio_key_wav, minio_key_mp3, render_ms
            ) VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, $9)
            """,
            artifact_id,
            workspace_id,
            job["anomaly_id"],
            metric,
            preset,
            duration,
            key_wav,
            key_mp3,
            render_ms,
        )

        await execute(
            """
            UPDATE audio_jobs
            SET status = 'completed', artifact_id = $2::uuid, updated_at = NOW()
            WHERE job_id = $1::uuid
            """,
            job["job_id"],
            artifact_id,
        )

        clickhouse.insert_audio_render(
            (
                workspace_id,
                artifact_id,
                str(job["anomaly_id"] or ""),
                metric,
                preset,
                duration,
                render_ms,
                utcnow(),
            )
        )

        audio_render_total.labels(preset=preset).inc()

        await emit_realtime_event(
            workspace_id,
            "audio.render.completed",
            {
                "job_id": str(job["job_id"]),
                "artifact_id": artifact_id,
                "metric_name": metric,
                "preset": preset,
                "render_ms": render_ms,
                "engine": engine,
            },
        )
        return 1

    except Exception as exc:  # noqa: BLE001
        logger.exception("audio job failed")
        await execute(
            """
            UPDATE audio_jobs
            SET status = 'failed', error = $2, updated_at = NOW()
            WHERE job_id = $1::uuid
            """,
            job["job_id"],
            str(exc),
        )
        await emit_realtime_event(
            workspace_id,
            "audio.render.failed",
            {
                "job_id": str(job["job_id"]),
                "metric_name": str(job["metric_name"]),
                "error": str(exc),
            },
        )
        return 0


async def worker_loop() -> None:
    settings = get_settings()
    workspace_id = settings.default_workspace_id
    n8n = N8NClient()
    anomaly_every = 30.0
    last_anomaly_ts = 0.0

    while True:
        now = asyncio.get_event_loop().time()

        if now - last_anomaly_ts >= anomaly_every:
            created = await run_anomaly_detection_cycle(workspace_id, n8n)
            if created:
                logger.info("anomaly cycle created=%s", created)
            last_anomaly_ts = now

        await run_audio_job_cycle(workspace_id)
        await asyncio.sleep(2)


async def build_daily_brief_data(workspace_id: str) -> dict[str, Any]:
    rows = await fetch(
        """
        SELECT metric_name, severity, detected_at
        FROM anomalies
        WHERE workspace_id = $1 AND detected_at >= NOW() - INTERVAL '24 hours'
        ORDER BY severity DESC
        LIMIT 25
        """,
        workspace_id,
    )
    severities = [int(row["severity"]) for row in rows]
    p95 = 0
    if severities:
        sorted_values = sorted(severities)
        idx = max(0, int(round(len(sorted_values) * 0.95)) - 1)
        p95 = sorted_values[idx]

    return {
        "count": len(rows),
        "p95_severity": p95,
        "median_severity": int(median(severities)) if severities else 0,
        "top": [
            {
                "metric": row["metric_name"],
                "severity": int(row["severity"]),
                "detected_at": row["detected_at"].isoformat(),
            }
            for row in rows[:8]
        ],
    }


def deterministic_correlation_seed(correlation_id: str) -> int:
    rng = random.Random(correlation_id)
    return rng.randint(1, 10_000_000)
