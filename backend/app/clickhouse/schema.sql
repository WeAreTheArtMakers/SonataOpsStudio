CREATE TABLE IF NOT EXISTS kpi_points_raw (
    workspace_id String,
    metric_name LowCardinality(String),
    ts DateTime64(3, 'UTC'),
    value Float64,
    tags String
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, ts);

CREATE TABLE IF NOT EXISTS anomalies_raw (
    workspace_id String,
    anomaly_id String,
    metric_name LowCardinality(String),
    window_start DateTime64(3, 'UTC'),
    window_end DateTime64(3, 'UTC'),
    severity UInt16,
    features String,
    detected_at DateTime64(3, 'UTC')
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, detected_at, anomaly_id);

CREATE TABLE IF NOT EXISTS audio_renders (
    workspace_id String,
    artifact_id String,
    anomaly_id String,
    metric_name LowCardinality(String),
    preset LowCardinality(String),
    duration_seconds UInt16,
    render_ms UInt32,
    created_at DateTime64(3, 'UTC')
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, created_at, artifact_id);

CREATE TABLE IF NOT EXISTS kpi_1m_rollup (
    workspace_id String,
    metric_name LowCardinality(String),
    bucket DateTime,
    avg_value Float64,
    min_value Float64,
    max_value Float64,
    points UInt64
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, bucket);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_kpi_1m_rollup
TO kpi_1m_rollup
AS
SELECT
    workspace_id,
    metric_name,
    toStartOfMinute(ts) AS bucket,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value,
    count() AS points
FROM kpi_points_raw
GROUP BY workspace_id, metric_name, bucket;

CREATE TABLE IF NOT EXISTS anomaly_counts_15m (
    workspace_id String,
    metric_name LowCardinality(String),
    bucket DateTime,
    anomaly_count UInt64
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, bucket);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_anomaly_counts_15m
TO anomaly_counts_15m
AS
SELECT
    workspace_id,
    metric_name,
    toStartOfInterval(detected_at, INTERVAL 15 MINUTE) AS bucket,
    count() AS anomaly_count
FROM anomalies_raw
GROUP BY workspace_id, metric_name, bucket;

CREATE TABLE IF NOT EXISTS severity_p95_1h (
    workspace_id String,
    metric_name LowCardinality(String),
    bucket DateTime,
    severity_p95 Float64
) ENGINE = MergeTree
ORDER BY (workspace_id, metric_name, bucket);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_severity_p95_1h
TO severity_p95_1h
AS
SELECT
    workspace_id,
    metric_name,
    toStartOfHour(detected_at) AS bucket,
    quantile(0.95)(severity) AS severity_p95
FROM anomalies_raw
GROUP BY workspace_id, metric_name, bucket;
