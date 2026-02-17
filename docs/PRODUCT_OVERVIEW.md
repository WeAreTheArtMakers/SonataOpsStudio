# Product Overview

## Vision
SonataOps Studio turns operations telemetry into a multi-modal decision system: visual dashboards, audible signal layers, and grounded executive narratives.

## Who It Is For
- COO / VP Operations
- CIO / Head of Platform Engineering
- Head of Data / Analytics
- Incident Command / SRE leadership

## Core Outcomes
- Reduce dashboard fatigue with anomaly sonification
- Reduce incident triage time with context-grounded explanations
- Reduce executive reporting overhead using automated daily brief generation

## Primary Capabilities
1. KPI ingestion from API + demo simulator
2. Real-time anomaly detection and severity scoring
3. Sonification engine (SuperCollider) for anomaly windows
4. RAG copilot with citations from internal docs
5. n8n-based agent workflows for incident and briefing automations
6. PromptOps quality and approval layer for LLM safety
7. Full observability stack with traces + metrics + dashboards

## Enterprise Differentiators
- Dual data plane: Postgres + ClickHouse
- Tenant-aware by `workspace_id`
- Tenant-scoped pgvector retrieval
- Prompt/source approval gate before LLM calls
- Signed object URLs for artifact access
- Built-in RAG eval harness (groundedness + safety)
