# Online Deployment (Free-Tier, Stable)

## Goal
Run the full SonataOps pipeline online with free-tier services while keeping architecture intact:
- FastAPI API + worker
- Postgres + pgvector
- ClickHouse
- MinIO
- n8n
- Prometheus + Grafana + OTel + Jaeger
- Next.js frontend

## Recommended Free-Tier Stack
1. **Oracle Cloud Always Free VM**
- 1 ARM instance can host Docker Compose for the full stack.
- This is the only practical way to keep all components together without paid managed services.

2. **Cloudflare Free (optional but recommended)**
- DNS + SSL proxy for stable HTTPS domain.

3. **GitHub Pages Free**
- Landing page and public project overview.
- Live URL: [https://wearetheartmakers.github.io/SonataOpsStudio/](https://wearetheartmakers.github.io/SonataOpsStudio/)

## One-Time Setup
1. Create an Oracle Cloud Always Free Ubuntu VM.
2. Open inbound ports:
- `80`, `443` (public app)
- optionally `22` (SSH)
3. Point domain to VM IP (optional). If skipped, use VM IP with HTTP.

## Deploy Commands (from your machine)
```bash
scp -i <ssh_key> deploy/free-tier/bootstrap.sh <user>@<vm_ip>:/tmp/bootstrap.sh
ssh -i <ssh_key> <user>@<vm_ip> 'SONATA_DOMAIN=<your-domain-or-vm-ip> bash /tmp/bootstrap.sh'
```

## Update Commands
```bash
ssh -i <ssh_key> <user>@<vm_ip> 'cd /opt/sonataops-studio && bash deploy/free-tier/update.sh'
```

## Compose Mode
Use cloud override:
```bash
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

What this does:
- keeps internal services off public ports
- exposes only Caddy on `80/443`
- routes all traffic to frontend, frontend proxies `/api/*` to backend internally

## GitHub Actions Auto-Deploy (Optional)
Workflow file:
- `.github/workflows/deploy-free-vm.yml`

Set these repo secrets:
- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `VM_DOMAIN` (optional; use domain or VM IP)

Once set, every push to `main` deploys automatically.

## Health Checks
- App: `http(s)://<domain-or-ip>`
- API health via frontend proxy: `http(s)://<domain-or-ip>/api/health`

## Tradeoffs
- Always Free VM resources are limited; use this for demo/staging, not heavy production.
- For production-grade scale, move Postgres/ClickHouse/Object Storage to managed plans.
