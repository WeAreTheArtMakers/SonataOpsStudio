from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.events import build_daily_brief_data
from app.agents.n8n_client import N8NClient
from app.config import get_settings
from app.db.postgres import execute, fetch, fetchrow
from app.db.seed import seed_demo
from app.rag.indexer import IngestDoc, ingest_documents
from app.rag.llm_provider import build_llm_provider

router = APIRouter(tags=["admin"])


class PromptApprovalRequest(BaseModel):
    request_id: str
    workspace_id: str | None = None
    approved_by: str = "admin"


class TriggerBriefRequest(BaseModel):
    workspace_id: str | None = None
    actor: str = "admin"


@router.get("/admin/status")
async def admin_status() -> dict[str, object]:
    workspace_id = get_settings().default_workspace_id

    anomaly_count = await fetchrow(
        "SELECT COUNT(*) AS c FROM anomalies WHERE workspace_id = $1", workspace_id
    )
    job_stats = await fetch(
        """
        SELECT status, COUNT(*) AS c
        FROM audio_jobs
        WHERE workspace_id = $1
        GROUP BY status
        """,
        workspace_id,
    )
    briefs_count = await fetchrow(
        "SELECT COUNT(*) AS c FROM briefs WHERE workspace_id = $1", workspace_id
    )
    rag_queries = await fetchrow(
        "SELECT COUNT(*) AS c FROM rag_queries WHERE workspace_id = $1", workspace_id
    )

    return {
        "workspace_id": workspace_id,
        "anomalies": int(anomaly_count["c"]),
        "audio_jobs": {row["status"]: int(row["c"]) for row in job_stats},
        "briefs": int(briefs_count["c"]),
        "rag_queries": int(rag_queries["c"]),
    }


@router.post("/admin/seed-demo")
async def admin_seed_demo() -> dict[str, object]:
    workspace_id = get_settings().default_workspace_id
    seeded = await seed_demo(workspace_id)

    provider = build_llm_provider()
    docs = [
        IngestDoc(
            title=item["title"],
            text=item["text"],
            source_url=item["source_url"],
            metadata=item["meta"],
        )
        for item in seeded["docs"]
    ]
    chunks = await ingest_documents(workspace_id, docs, provider)

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, 'admin', 'seed.demo', $2::jsonb)
        """,
        workspace_id,
        json.dumps({"points": seeded["seeded_points"], "chunks": chunks}),
    )

    return {
        "workspace_id": workspace_id,
        "seeded_points": seeded["seeded_points"],
        "rag_chunks": chunks,
    }


@router.get("/admin/promptops/requests")
async def list_prompt_requests() -> dict[str, object]:
    workspace_id = get_settings().default_workspace_id
    rows = await fetch(
        """
        SELECT request_id, status, approved_by, created_at, approved_at, prompt_preview, sources_preview
        FROM prompt_approval_requests
        WHERE workspace_id = $1
        ORDER BY created_at DESC
        LIMIT 100
        """,
        workspace_id,
    )

    return {
        "workspace_id": workspace_id,
        "items": [
            {
                "request_id": str(row["request_id"]),
                "status": row["status"],
                "approved_by": row["approved_by"],
                "created_at": row["created_at"].isoformat(),
                "approved_at": row["approved_at"].isoformat() if row["approved_at"] else None,
                "prompt_preview": row["prompt_preview"],
                "sources_preview": row["sources_preview"],
            }
            for row in rows
        ],
    }


@router.post("/admin/promptops/approve")
async def approve_prompt(payload: PromptApprovalRequest) -> dict[str, object]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id

    row = await fetchrow(
        """
        UPDATE prompt_approval_requests
        SET status = 'approved', approved_by = $3, approved_at = NOW()
        WHERE request_id = $1::uuid AND workspace_id = $2
        RETURNING request_id
        """,
        payload.request_id,
        workspace_id,
        payload.approved_by,
    )
    if not row:
        raise HTTPException(status_code=404, detail="approval request not found")

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, $2, 'prompt.approve', $3::jsonb)
        """,
        workspace_id,
        payload.approved_by,
        json.dumps({"request_id": payload.request_id}),
    )

    return {
        "workspace_id": workspace_id,
        "request_id": payload.request_id,
        "status": "approved",
    }


@router.post("/admin/trigger-exec-brief")
async def trigger_exec_brief(payload: TriggerBriefRequest | None = None) -> dict[str, object]:
    data = payload or TriggerBriefRequest()
    workspace_id = data.workspace_id or get_settings().default_workspace_id

    summary = await build_daily_brief_data(workspace_id)
    n8n = N8NClient()
    webhook_payload = {
        "workspace_id": workspace_id,
        "summary": summary,
        "actor": data.actor,
    }
    await n8n.exec_brief_generator(webhook_payload)

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, $2, 'exec_brief.trigger', $3::jsonb)
        """,
        workspace_id,
        data.actor,
        json.dumps(webhook_payload),
    )

    return {
        "workspace_id": workspace_id,
        "triggered": True,
        "summary": summary,
    }
