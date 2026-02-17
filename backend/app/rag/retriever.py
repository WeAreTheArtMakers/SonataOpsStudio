from __future__ import annotations

from typing import Any

from app.db.postgres import fetch
from app.rag.llm_provider import LLMProvider
from app.utils.redaction import redact_pii


def _to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def retrieve_sources(
    workspace_id: str,
    query: str,
    provider: LLMProvider,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    embedding = (await provider.embed([query]))[0]
    vector_literal = _to_pgvector_literal(embedding)

    rows = await fetch(
        """
        SELECT id, title, source_url, chunk_text, meta,
               (1 - (embedding <=> $2::vector)) AS score
        FROM rag_documents
        WHERE workspace_id = $1
        ORDER BY embedding <=> $2::vector
        LIMIT $3
        """,
        workspace_id,
        vector_literal,
        top_k,
    )

    sources: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        snippet = redact_pii(str(row["chunk_text"]))
        sources.append(
            {
                "id": idx,
                "doc_id": str(row["id"]),
                "title": row["title"],
                "url": row["source_url"],
                "snippet": snippet,
                "meta": row["meta"],
                "score": float(row["score"]),
            }
        )
    return sources
