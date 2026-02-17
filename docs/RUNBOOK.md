# Runbook

## Startup
```bash
cp .env.example .env
docker compose up --build
```

Or run conflict-safe startup (auto free ports + seed):
```bash
make listen-demo
```

## Seed Demo
```bash
curl -X POST http://localhost:8000/admin/seed-demo
```

## Smoke Checks
- `GET /health`
- `GET /admin/status`
- open frontend dashboard
- trigger one audio render and verify playback URL

## Common Ops
### Ingest KPI points
```bash
curl -X POST http://localhost:8000/kpis/ingest \
  -H "content-type: application/json" \
  -d '{"workspace_id":"demo-workspace","points":[{"timestamp":"2026-02-17T10:00:00Z","metric_name":"Sales","value":123.4,"tags":{"region":"NA"}}]}'
```

### Trigger manual exec brief workflow
```bash
curl -X POST http://localhost:8000/admin/trigger-exec-brief
```

### Generate audio
```bash
curl -X POST http://localhost:8000/audio/render \
  -H "content-type: application/json" \
  -d '{"workspace_id":"demo-workspace","metric_name":"RiskScore","start":"2026-02-17T09:00:00Z","end":"2026-02-17T10:00:00Z","preset":"Risk Tension","duration":18}'
```

## Troubleshooting
- No audio output:
  - check worker logs for `sclang` failures
  - fallback renderer should still generate WAV
- No traces:
  - confirm `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`
  - verify Jaeger UI and collector logs
- No dashboard data:
  - verify Prometheus targets and backend `/metrics`
- n8n flow not firing:
  - verify webhook URL env values and n8n node activation

## Recovery
- Rebuild backend only:
```bash
docker compose up --build backend-api backend-worker
```
- Reset persistent volumes:
```bash
docker compose down -v
```

## Screenshots
```bash
SONATA_SCREENSHOT_BASE_URL=http://localhost:3000 make screenshots
```
