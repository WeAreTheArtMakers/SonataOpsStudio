from prometheus_client import Counter, Gauge, Histogram

kpi_ingest_total = Counter("kpi_ingest_total", "Total KPI points ingested")
anomaly_detected_total = Counter(
    "anomaly_detected_total",
    "Total anomalies detected",
    labelnames=("metric",),
)
audio_render_total = Counter(
    "audio_render_total",
    "Total audio renders",
    labelnames=("preset",),
)
rag_queries_total = Counter("rag_queries_total", "Total RAG queries")
rag_eval_pass_rate = Gauge("rag_eval_pass_rate", "RAG eval overall pass rate")
clickhouse_ingest_rows_total = Counter(
    "clickhouse_ingest_rows_total",
    "Rows ingested into ClickHouse",
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    labelnames=("method", "route", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
