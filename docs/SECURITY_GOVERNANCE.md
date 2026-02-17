# Security & Governance

## Data Classification
- **Public**: non-sensitive demo metrics
- **Internal**: KPI trends, anomaly metadata, runbooks
- **Confidential**: incident notes, internal release plans
- **Restricted**: regulated identifiers (PII/financial account patterns)

## PII Redaction
Before snippets are sent to LLM providers:
- email patterns are masked
- phone numbers are masked
- IBAN-like account patterns are masked

Implementation: `backend/app/utils/redaction.py`

## PromptOps Approval Sandbox
For every copilot query, backend computes:
- `prompt_hash`
- `sources_hash`
- `prompt_preview`
- selected source excerpts

If `PROMPTOPS_REQUIRE_APPROVAL=true` and package is not approved:
- request is saved in `prompt_approval_requests`
- LLM call is blocked until approval endpoint is used

Demo default: `PROMPTOPS_AUTO_APPROVE=true` for smoother local run.

## RBAC
Demo mode keeps endpoints open. Production recommendation:
- SSO + OIDC
- route-level role mapping (`analyst`, `ops_lead`, `exec`, `admin`)
- workspace-level resource policy enforcement

## Audit Logging
All critical actions are logged in `audit_logs`:
- copilot queries and source usage
- audio renders
- brief creation/export
- prompt approvals

## Storage Security
- MinIO access via short-lived signed URLs
- object keys partitioned by workspace + metric + anomaly/artifact id
- no long-lived public links in production

## Hardening Checklist
- enable TLS at ingress
- rotate MinIO/DB credentials
- restrict n8n ingress to trusted network
- enforce provider egress allowlist
- enable row-level security in Postgres for tenants
- secrets from Vault/KMS (not `.env`)
