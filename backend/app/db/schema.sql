CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS kpi_points_recent (
    id BIGSERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kpi_recent_workspace_metric_ts
    ON kpi_points_recent (workspace_id, metric_name, ts DESC);

CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    severity INT NOT NULL,
    features JSONB NOT NULL,
    correlations JSONB NOT NULL DEFAULT '[]'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anomalies_workspace_detected
    ON anomalies (workspace_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_workspace_metric
    ON anomalies (workspace_id, metric_name);

CREATE TABLE IF NOT EXISTS audio_artifacts (
    artifact_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    anomaly_id UUID,
    metric_name TEXT NOT NULL,
    preset TEXT NOT NULL,
    duration_seconds INT NOT NULL,
    controls JSONB NOT NULL DEFAULT '{}'::jsonb,
    minio_key_wav TEXT NOT NULL,
    minio_key_mp3 TEXT NOT NULL,
    render_ms INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audio_artifacts_workspace_created
    ON audio_artifacts (workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audio_jobs (
    job_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    anomaly_id UUID,
    metric_name TEXT NOT NULL,
    start_ts TIMESTAMPTZ NOT NULL,
    end_ts TIMESTAMPTZ NOT NULL,
    preset TEXT NOT NULL,
    duration_seconds INT NOT NULL,
    controls JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'queued',
    error TEXT,
    correlation_id TEXT NOT NULL,
    artifact_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audio_jobs_workspace_status
    ON audio_jobs (workspace_id, status, created_at);

ALTER TABLE audio_jobs
    ADD COLUMN IF NOT EXISTS controls JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE audio_artifacts
    ADD COLUMN IF NOT EXISTS controls JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT,
    chunk_text TEXT NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace
    ON rag_documents (workspace_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
    ON rag_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_rag_documents_tenant_aware
    ON rag_documents (workspace_id, id);

CREATE TABLE IF NOT EXISTS rag_queries (
    query_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    top_sources JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    prompt_version TEXT NOT NULL,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_eval_cases (
    case_id BIGSERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    question TEXT NOT NULL,
    expected_keywords TEXT[] NOT NULL,
    expected_sources TEXT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, question)
);

CREATE TABLE IF NOT EXISTS rag_eval_results (
    run_id UUID NOT NULL,
    case_id BIGINT NOT NULL REFERENCES rag_eval_cases(case_id),
    grounded_pass BOOLEAN NOT NULL,
    safety_pass BOOLEAN NOT NULL,
    notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rag_eval_results_run_id ON rag_eval_results (run_id);

CREATE TABLE IF NOT EXISTS prompt_approval_requests (
    request_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    sources_hash TEXT NOT NULL,
    prompt_preview TEXT NOT NULL,
    sources_preview JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    UNIQUE (workspace_id, prompt_hash, sources_hash)
);

CREATE TABLE IF NOT EXISTS briefs (
    brief_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body_md TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_briefs_workspace_created
    ON briefs (workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS realtime_events (
    id BIGSERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_realtime_events_workspace_id
    ON realtime_events (workspace_id, id DESC);
