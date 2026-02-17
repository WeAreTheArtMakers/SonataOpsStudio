from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db.postgres import execute, fetch, fetchrow
from app.metrics import rag_eval_pass_rate, rag_queries_total
from app.rag.evals import evaluate_groundedness, evaluate_safety
from app.rag.indexer import IngestDoc, ingest_documents
from app.rag.llm_provider import build_llm_provider
from app.rag.policies import assert_prompt_approval, build_prompt_package
from app.rag.prompts import resolve_prompt_template
from app.rag.retriever import retrieve_sources
from app.utils.ids import new_id
from app.utils.redaction import redact_pii

router = APIRouter(tags=["rag"])


class RAGIngestDoc(BaseModel):
    title: str
    text: str
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGIngestRequest(BaseModel):
    workspace_id: str | None = None
    docs: list[RAGIngestDoc]


class CopilotAskRequest(BaseModel):
    workspace_id: str | None = None
    user_id: str = "demo-user"
    question: str
    mode: str = "anomaly_explainer"
    context: dict[str, Any] = Field(default_factory=dict)


class EvalRunRequest(BaseModel):
    workspace_id: str | None = None
    limit: int = Field(default=5, ge=1, le=50)


async def _ask_copilot_internal(payload: CopilotAskRequest) -> dict[str, Any]:
    settings = get_settings()
    workspace_id = payload.workspace_id or settings.default_workspace_id
    provider = build_llm_provider()

    sources = await retrieve_sources(workspace_id, payload.question, provider, top_k=4)
    template = resolve_prompt_template(payload.mode)

    sources_block = "\n".join(
        f"[{src['id']}] {src['title']} | {src['snippet']} | url={src['url']}"
        for src in sources
    )
    context_text = json.dumps(payload.context, ensure_ascii=True)
    user_prompt = template.user.format(
        question=redact_pii(payload.question),
        context=context_text,
        sources=sources_block,
    )

    package = build_prompt_package(template.system + "\n" + user_prompt, sources)
    approved, request_id = await assert_prompt_approval(workspace_id, payload.user_id, package)
    if not approved:
        raise HTTPException(
            status_code=412,
            detail={
                "message": "Prompt package pending approval",
                "request_id": request_id,
                "workspace_id": workspace_id,
            },
        )

    answer = await provider.chat(template.system, user_prompt)

    avg_score = sum(float(item.get("score", 0.0)) for item in sources) / max(len(sources), 1)
    confidence = max(0.05, min(0.99, (avg_score + 1) / 2))

    query_id = new_id()
    await execute(
        """
        INSERT INTO rag_queries (
            query_id, workspace_id, user_id, question, answer, top_sources,
            confidence, prompt_version, trace_id
        ) VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
        """,
        query_id,
        workspace_id,
        payload.user_id,
        payload.question,
        answer,
        json.dumps(sources),
        confidence,
        template.version,
        None,
    )

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, $2, 'copilot.ask', $3::jsonb)
        """,
        workspace_id,
        payload.user_id,
        json.dumps(
            {
                "query_id": query_id,
                "source_titles": [s["title"] for s in sources],
                "prompt_version": template.version,
                "approval_request_id": request_id,
            }
        ),
    )

    rag_queries_total.inc()

    return {
        "query_id": query_id,
        "workspace_id": workspace_id,
        "answer": answer,
        "top_sources": sources,
        "confidence": confidence,
        "prompt_version": template.version,
        "provider": provider.name,
    }


@router.post("/rag/ingest")
async def ingest_rag(payload: RAGIngestRequest) -> dict[str, object]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id
    if not payload.docs:
        raise HTTPException(status_code=400, detail="docs cannot be empty")

    provider = build_llm_provider()
    docs = [
        IngestDoc(
            title=doc.title,
            text=doc.text,
            source_url=doc.source_url,
            metadata=doc.metadata,
        )
        for doc in payload.docs
    ]

    inserted = await ingest_documents(workspace_id, docs, provider)

    await execute(
        """
        INSERT INTO audit_logs (workspace_id, actor, action, details)
        VALUES ($1, 'admin', 'rag.ingest', $2::jsonb)
        """,
        workspace_id,
        json.dumps({"docs": len(payload.docs), "chunks": inserted}),
    )

    return {
        "workspace_id": workspace_id,
        "docs": len(payload.docs),
        "chunks_inserted": inserted,
    }


@router.post("/copilot/ask")
async def copilot_ask(payload: CopilotAskRequest) -> dict[str, Any]:
    return await _ask_copilot_internal(payload)


@router.post("/rag/eval/run")
async def run_eval(payload: EvalRunRequest) -> dict[str, Any]:
    workspace_id = payload.workspace_id or get_settings().default_workspace_id
    run_id = new_id()

    cases = await fetch(
        """
        SELECT case_id, question, expected_keywords, expected_sources
        FROM rag_eval_cases
        WHERE workspace_id = $1
        ORDER BY case_id ASC
        LIMIT $2
        """,
        workspace_id,
        payload.limit,
    )
    if not cases:
        raise HTTPException(status_code=404, detail="no eval cases found")

    pass_count = 0
    results: list[dict[str, Any]] = []

    for case in cases:
        question = str(case["question"])
        ask_result = await _ask_copilot_internal(
            CopilotAskRequest(
                workspace_id=workspace_id,
                user_id="eval-bot",
                question=question,
                mode="anomaly_explainer",
                context={"eval_case": int(case["case_id"])},
            )
        )

        grounded_pass, grounded_note = evaluate_groundedness(
            ask_result["answer"],
            ask_result["top_sources"],
            list(case["expected_sources"]),
        )
        safety_pass, safety_note = evaluate_safety(ask_result["answer"])
        if grounded_pass and safety_pass:
            pass_count += 1

        notes = f"grounded={grounded_note}; safety={safety_note}"
        await execute(
            """
            INSERT INTO rag_eval_results (run_id, case_id, grounded_pass, safety_pass, notes)
            VALUES ($1::uuid, $2, $3, $4, $5)
            """,
            run_id,
            int(case["case_id"]),
            grounded_pass,
            safety_pass,
            notes,
        )

        results.append(
            {
                "case_id": int(case["case_id"]),
                "question": question,
                "grounded_pass": grounded_pass,
                "safety_pass": safety_pass,
                "notes": notes,
                "sample_answer": ask_result["answer"][:240],
            }
        )

    pass_rate = pass_count / max(len(cases), 1)
    rag_eval_pass_rate.set(pass_rate)

    return {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "cases": len(cases),
        "overall_pass_rate": pass_rate,
        "results": results,
    }


@router.get("/rag/eval/results")
async def eval_results(
    workspace_id: str = Query(default_factory=lambda: get_settings().default_workspace_id),
) -> dict[str, Any]:
    latest = await fetchrow(
        """
        SELECT run_id
        FROM rag_eval_results rer
        JOIN rag_eval_cases rec ON rer.case_id = rec.case_id
        WHERE rec.workspace_id = $1
        ORDER BY rer.created_at DESC
        LIMIT 1
        """,
        workspace_id,
    )
    if not latest:
        return {"workspace_id": workspace_id, "runs": []}

    rows = await fetch(
        """
        SELECT rer.run_id, rer.case_id, rer.grounded_pass, rer.safety_pass, rer.notes, rer.created_at,
               rec.question
        FROM rag_eval_results rer
        JOIN rag_eval_cases rec ON rer.case_id = rec.case_id
        WHERE rec.workspace_id = $1 AND rer.run_id = $2::uuid
        ORDER BY rer.case_id ASC
        """,
        workspace_id,
        str(latest["run_id"]),
    )

    items = [
        {
            "run_id": str(row["run_id"]),
            "case_id": int(row["case_id"]),
            "question": row["question"],
            "grounded_pass": bool(row["grounded_pass"]),
            "safety_pass": bool(row["safety_pass"]),
            "notes": row["notes"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]

    overall = (
        sum(1 for item in items if item["grounded_pass"] and item["safety_pass"])
        / max(len(items), 1)
    )
    rag_eval_pass_rate.set(overall)

    return {
        "workspace_id": workspace_id,
        "run_id": str(latest["run_id"]),
        "overall_pass_rate": overall,
        "items": items,
    }
