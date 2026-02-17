# RAG Evaluation Playbook

## Objectives
- Validate groundedness (answers are cited and relevant)
- Validate safety (no PII leakage, no unsupported critical claims)

## Datasets
Stored in Postgres table `rag_eval_cases` and seeded in demo:
- anomaly cause analysis prompts
- release impact prompts
- campaign influence prompts

## Metrics
- **Grounded pass**: answer has citations and at least one expected source family matches
- **Safety pass**: no unmasked PII, low unverifiable claim risk
- **Overall pass rate**: mean of grounded+safety pass across run

## Procedure
1. Ingest or update eval cases.
2. Run `POST /rag/eval/run` with `limit=N`.
3. View summary at `GET /rag/eval/results`.
4. Review failed cases in admin UI.
5. Update prompt version in `app/rag/prompts.py` and rerun.

## Failure Triage
- Missing citations -> tighten system instruction and citation parser.
- Wrong source priority -> adjust retriever top_k or source weighting.
- Safety failures -> strengthen redaction patterns and post-generation checks.

## Release Gate Recommendation
- grounded pass >= 0.85
- safety pass >= 0.95
- no critical PII failure
