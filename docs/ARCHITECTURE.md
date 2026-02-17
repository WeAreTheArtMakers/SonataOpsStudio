# Architecture

## Topology
- **Frontend**: Next.js App Router (TypeScript, Tailwind, Recharts)
- **API**: FastAPI async app handling ingestion, retrieval, orchestration
- **Worker**: FastAPI codebase in worker mode handling anomaly scans and audio rendering jobs
- **Storage**:
  - Postgres 15 + pgvector (operational state, jobs, docs, briefs, audit)
  - ClickHouse (raw KPI/anomaly/audio analytics)
  - MinIO (WAV/MP3 artifact objects)
- **Automation**: n8n webhook/schedule flows
- **Observability**: Prometheus + Grafana + OpenTelemetry Collector + Jaeger

## Clean Architecture Layers
- `app/api`: HTTP boundaries and contracts
- `app/db`, `app/clickhouse`, `app/storage`: infrastructure adapters
- `app/rag`, `app/sonification`, `app/agents`: domain services
- `app/utils`: cross-cutting utilities

## Data Model Highlights
- All domain tables include `workspace_id` for multi-tenant partitioning.
- `rag_documents` stores embeddings in pgvector and is always filtered by `workspace_id` during retrieval.
- `audio_jobs` provides durable async queue semantics with `FOR UPDATE SKIP LOCKED`.

## Request and Processing Flows
### KPI Ingestion
1. `POST /kpis/ingest`
2. write raw points to ClickHouse `kpi_points_raw`
3. write recent copy to Postgres `kpi_points_recent`

### Anomaly Loop (worker every 30s)
1. load recent KPI windows from ClickHouse
2. compute robust z-score + residual z-score + volatility + slope
3. persist anomalies to Postgres + ClickHouse
4. trigger n8n anomaly workflows and realtime event feed

### Audio Rendering Loop
1. API inserts `audio_jobs(status='queued')`
2. worker locks job row
3. worker maps features -> control curves
4. worker calls SuperCollider (`sclang`) to render WAV
5. worker creates MP3 preview via ffmpeg
6. upload to MinIO, write `audio_artifacts`
7. mark job complete, push realtime event

### RAG Copilot
1. ingest docs via `POST /rag/ingest`
2. chunk using LlamaIndex splitter
3. embed + store in pgvector
4. retrieve top chunks for `POST /copilot/ask`
5. redaction + prompt package policy check
6. LLM call via pluggable provider
7. answer + citations + confidence + audit logs

## Tracing Strategy
- FastAPI request spans via instrumentation
- manual spans around:
  - asyncpg queries
  - ClickHouse calls
  - MinIO upload/signing
  - n8n webhook requests
  - SuperCollider render subprocess
- trace headers propagated to n8n calls
