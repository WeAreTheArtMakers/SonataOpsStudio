KPI_ROLLUP_QUERY = """
SELECT bucket, avg_value, min_value, max_value, points
FROM kpi_1m_rollup
WHERE workspace_id = %(workspace_id)s
  AND metric_name = %(metric_name)s
  AND bucket >= now() - toIntervalMinute(%(minutes)s)
ORDER BY bucket ASC
"""

ANOMALY_ANALYTICS_QUERY = """
SELECT metric_name, bucket, anomaly_count
FROM anomaly_counts_15m
WHERE workspace_id = %(workspace_id)s
  AND bucket >= now() - toIntervalMinute(%(minutes)s)
ORDER BY bucket ASC
"""

SEVERITY_ANALYTICS_QUERY = """
SELECT metric_name, bucket, severity_p95
FROM severity_p95_1h
WHERE workspace_id = %(workspace_id)s
  AND bucket >= now() - toIntervalMinute(%(minutes)s)
ORDER BY bucket ASC
"""

AUDIO_ANALYTICS_QUERY = """
SELECT
  metric_name,
  if(preset = 'State Azure', 'modART', preset) AS preset_name,
  count() AS renders,
  avg(render_ms) AS avg_render_ms
FROM audio_renders
WHERE workspace_id = %(workspace_id)s
  AND created_at >= now() - toIntervalMinute(%(minutes)s)
GROUP BY metric_name, preset_name
ORDER BY renders DESC
"""
