from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.db.postgres import execute, fetchrow
from app.utils.ids import new_id


@dataclass
class PromptPackage:
    prompt_hash: str
    sources_hash: str
    prompt_preview: str
    sources_preview: list[dict[str, Any]]


def build_prompt_package(prompt_text: str, sources: list[dict[str, Any]]) -> PromptPackage:
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    normalized_sources = [
        {
            "title": source.get("title"),
            "snippet": source.get("snippet", "")[:320],
            "url": source.get("url"),
        }
        for source in sources
    ]
    sources_hash = hashlib.sha256(
        json.dumps(normalized_sources, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return PromptPackage(
        prompt_hash=prompt_hash,
        sources_hash=sources_hash,
        prompt_preview=prompt_text[:800],
        sources_preview=normalized_sources,
    )


async def assert_prompt_approval(
    workspace_id: str,
    actor: str,
    package: PromptPackage,
) -> tuple[bool, str | None]:
    settings = get_settings()

    row = await fetchrow(
        """
        SELECT request_id, status
        FROM prompt_approval_requests
        WHERE workspace_id = $1 AND prompt_hash = $2 AND sources_hash = $3
        """,
        workspace_id,
        package.prompt_hash,
        package.sources_hash,
    )

    if not settings.promptops_require_approval:
        return True, None

    if row and row["status"] == "approved":
        return True, str(row["request_id"])

    if settings.promptops_auto_approve:
        request_id = str(row["request_id"]) if row else new_id()
        await execute(
            """
            INSERT INTO prompt_approval_requests (
                request_id, workspace_id, prompt_hash, sources_hash,
                prompt_preview, sources_preview, status, approved_by, approved_at
            )
            VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, 'approved', $7, NOW())
            ON CONFLICT (workspace_id, prompt_hash, sources_hash)
            DO UPDATE SET status = 'approved', approved_by = EXCLUDED.approved_by, approved_at = NOW()
            """,
            request_id,
            workspace_id,
            package.prompt_hash,
            package.sources_hash,
            package.prompt_preview,
            json.dumps(package.sources_preview),
            actor,
        )
        return True, request_id

    request_id = str(row["request_id"]) if row else new_id()
    await execute(
        """
        INSERT INTO prompt_approval_requests (
            request_id, workspace_id, prompt_hash, sources_hash,
            prompt_preview, sources_preview, status
        )
        VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, 'pending')
        ON CONFLICT (workspace_id, prompt_hash, sources_hash)
        DO NOTHING
        """,
        request_id,
        workspace_id,
        package.prompt_hash,
        package.sources_hash,
        package.prompt_preview,
        json.dumps(package.sources_preview),
    )
    return False, request_id
