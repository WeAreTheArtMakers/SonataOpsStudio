from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.db.postgres import fetch

router = APIRouter(tags=["events"])


async def _poll_events(
    workspace_id: str,
    last_id: int,
) -> tuple[list[dict[str, object]], int]:
    rows = await fetch(
        """
        SELECT id, event_type, payload, created_at
        FROM realtime_events
        WHERE workspace_id = $1 AND id > $2
        ORDER BY id ASC
        LIMIT 100
        """,
        workspace_id,
        last_id,
    )
    events: list[dict[str, object]] = []
    for row in rows:
        event = {
            "id": int(row["id"]),
            "type": str(row["event_type"]),
            "payload": row["payload"],
            "created_at": row["created_at"].isoformat(),
        }
        events.append(event)
        last_id = max(last_id, int(row["id"]))
    return events, last_id


async def _sse_generator(
    workspace_id: str,
    start_id: int,
) -> AsyncGenerator[str, None]:
    last_id = start_id
    while True:
        events, last_id = await _poll_events(workspace_id, last_id)
        if events:
            for event in events:
                yield f"id: {event['id']}\n"
                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event)}\n\n"
        else:
            yield ": keepalive\n\n"
        await asyncio.sleep(1)


@router.get("/events/sse")
async def stream_sse(
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
    last_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(workspace_id=workspace_id, start_id=last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    await ws.accept()
    workspace_id = ws.query_params.get("workspace_id", get_settings().default_workspace_id)
    last_id = int(ws.query_params.get("last_event_id", "0"))

    try:
        while True:
            events, last_id = await _poll_events(workspace_id, last_id)
            for event in events:
                await ws.send_json(event)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
