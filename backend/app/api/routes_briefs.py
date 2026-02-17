from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.agents.events import emit_realtime_event
from app.config import get_settings
from app.db.postgres import execute, fetch, fetchrow
from app.utils.ids import new_id

router = APIRouter(tags=["briefs"])


class BriefCreateRequest(BaseModel):
    workspace_id: str | None = None
    title: str
    body_md: str
    data: dict[str, object] = Field(default_factory=dict)


@router.post("/briefs/create")
async def create_brief(payload: BriefCreateRequest) -> dict[str, object]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id
    brief_id = new_id()

    await execute(
        """
        INSERT INTO briefs (brief_id, workspace_id, title, body_md, data)
        VALUES ($1::uuid, $2, $3, $4, $5::jsonb)
        """,
        brief_id,
        workspace_id,
        payload.title,
        payload.body_md,
        json.dumps(payload.data),
    )

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, 'system', 'brief.create', $2::jsonb)
        """,
        workspace_id,
        json.dumps({"brief_id": brief_id, "title": payload.title}),
    )

    await emit_realtime_event(
        workspace_id,
        "brief.created",
        {"brief_id": brief_id, "title": payload.title},
    )

    return {"brief_id": brief_id, "workspace_id": workspace_id}


@router.get("/briefs")
async def list_briefs(
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    rows = await fetch(
        """
        SELECT brief_id, title, body_md, data, created_at
        FROM briefs
        WHERE workspace_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        workspace_id,
        limit,
    )

    return {
        "workspace_id": workspace_id,
        "items": [
            {
                "brief_id": str(row["brief_id"]),
                "title": row["title"],
                "body_md": row["body_md"],
                "data": row["data"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/briefs/{brief_id}")
async def get_brief(
    brief_id: str,
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, object]:
    row = await fetchrow(
        """
        SELECT brief_id, title, body_md, data, created_at
        FROM briefs
        WHERE brief_id = $1::uuid AND workspace_id = $2
        """,
        brief_id,
        workspace_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="brief not found")

    return {
        "brief_id": str(row["brief_id"]),
        "title": row["title"],
        "body_md": row["body_md"],
        "data": row["data"],
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/briefs/{brief_id}/export")
async def export_brief(
    brief_id: str,
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> Response:
    row = await fetchrow(
        """
        SELECT title, body_md
        FROM briefs
        WHERE brief_id = $1::uuid AND workspace_id = $2
        """,
        brief_id,
        workspace_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="brief not found")

    title_safe = str(row["title"]).replace(" ", "-").lower()
    content = f"# {row['title']}\n\n{row['body_md']}\n"

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, 'system', 'brief.export', $2::jsonb)
        """,
        workspace_id,
        json.dumps({"brief_id": brief_id}),
    )

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={title_safe}.md",
        },
    )
