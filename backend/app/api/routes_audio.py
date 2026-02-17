from __future__ import annotations

from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.events import emit_realtime_event
from app.config import get_settings
from app.db.postgres import execute, fetchrow
from app.storage.minio_client import get_minio
from app.utils.ids import new_id

router = APIRouter(tags=["audio"])


class AudioRenderRequest(BaseModel):
    workspace_id: str | None = None
    anomaly_id: str | None = None
    metric_name: str
    start: datetime
    end: datetime
    preset: str = Field(default="Executive Minimal")
    duration: int = Field(default=20, ge=5, le=180)
    controls: dict[str, float] = Field(default_factory=dict)


class AudioUrlResponse(BaseModel):
    artifact_id: str
    format: str
    url: str
    expires_seconds: int


@router.post("/audio/render")
async def queue_audio_render(payload: AudioRenderRequest) -> dict[str, object]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id
    if payload.end <= payload.start:
        raise HTTPException(status_code=400, detail="end must be greater than start")

    job_id = new_id()
    correlation_id = new_id()

    await execute(
        """
        INSERT INTO audio_jobs (
            job_id, workspace_id, anomaly_id, metric_name, start_ts,
            end_ts, preset, duration_seconds, controls, status, correlation_id
        ) VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, $9::jsonb, 'queued', $10)
        """,
        job_id,
        workspace_id,
        payload.anomaly_id,
        payload.metric_name,
        payload.start,
        payload.end,
        payload.preset,
        payload.duration,
        json.dumps(payload.controls),
        correlation_id,
    )

    await emit_realtime_event(
        workspace_id,
        "audio.render.queued",
        {
            "job_id": job_id,
            "metric_name": payload.metric_name,
            "preset": payload.preset,
            "duration": payload.duration,
            "controls": payload.controls,
        },
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "workspace_id": workspace_id,
    }


@router.get("/audio/jobs/{job_id}")
async def get_audio_job(
    job_id: str,
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    row = await fetchrow(
        """
        SELECT job_id, metric_name, preset, duration_seconds, controls, status, error, artifact_id, created_at, updated_at
        FROM audio_jobs
        WHERE job_id = $1::uuid AND workspace_id = $2
        """,
        job_id,
        workspace_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="job not found")

    controls = row["controls"] or {}
    if isinstance(controls, str):
        try:
            controls = json.loads(controls)
        except json.JSONDecodeError:
            controls = {}

    return {
        "job_id": str(row["job_id"]),
        "metric_name": row["metric_name"],
        "preset": row["preset"],
        "duration_seconds": int(row["duration_seconds"]),
        "controls": controls,
        "status": row["status"],
        "error": row["error"],
        "artifact_id": str(row["artifact_id"]) if row["artifact_id"] else None,
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.get("/audio/{artifact_id}/url", response_model=AudioUrlResponse)
async def get_audio_url(
    artifact_id: str,
    fmt: str = Query(default="mp3", pattern="^(wav|mp3)$"),
    expires_seconds: int = Query(default=300, ge=30, le=3600),
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> AudioUrlResponse:
    row = await fetchrow(
        """
        SELECT minio_key_wav, minio_key_mp3
        FROM audio_artifacts
        WHERE artifact_id = $1::uuid AND workspace_id = $2
        """,
        artifact_id,
        workspace_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="artifact not found")

    key = row["minio_key_wav"] if fmt == "wav" else row["minio_key_mp3"]
    signed = get_minio().signed_url(key, expires_seconds=expires_seconds)

    return AudioUrlResponse(
        artifact_id=artifact_id,
        format=fmt,
        url=signed,
        expires_seconds=expires_seconds,
    )
