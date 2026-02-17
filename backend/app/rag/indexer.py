from __future__ import annotations

import json
from dataclasses import dataclass

from llama_index.core.node_parser import SentenceSplitter

from app.db.postgres import execute
from app.rag.llm_provider import LLMProvider
from app.utils.ids import new_id


@dataclass
class IngestDoc:
    title: str
    text: str
    source_url: str | None
    metadata: dict[str, object]


def _to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def ingest_documents(
    workspace_id: str,
    docs: list[IngestDoc],
    provider: LLMProvider,
) -> int:
    splitter = SentenceSplitter(chunk_size=420, chunk_overlap=60)
    inserted = 0

    for doc in docs:
        chunks = splitter.split_text(doc.text)
        embeddings = await provider.embed(chunks)
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            await execute(
                """
                INSERT INTO rag_documents (id, workspace_id, title, source_url, chunk_text, meta, embedding)
                VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, $7::vector)
                """,
                new_id(),
                workspace_id,
                doc.title,
                doc.source_url,
                chunk,
                json.dumps(doc.metadata),
                _to_pgvector_literal(embedding),
            )
            inserted += 1
    return inserted
