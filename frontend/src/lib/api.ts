import {
  Anomaly,
  Brief,
  CopilotResponse,
  EvalResult,
  KpiRollupRow,
  SourceItem
} from '@/lib/types';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '/api';
export const WORKSPACE_ID = 'demo-workspace';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers || {})
    },
    cache: 'no-store'
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return (await res.json()) as T;
}

export async function getHealth() {
  return request<{ status: string; postgres: boolean; clickhouse: boolean; minio: boolean }>('/health');
}

export async function getAdminStatus() {
  return request<{
    workspace_id: string;
    anomalies: number;
    audio_jobs: Record<string, number>;
    briefs: number;
    rag_queries: number;
  }>(`/admin/status`);
}

export async function seedDemo() {
  return request<{ seeded_points: number; rag_chunks: number }>('/admin/seed-demo', {
    method: 'POST'
  });
}

export async function getKpiAnalytics(metric: string, minutes = 180) {
  return request<{ metric: string; rows: KpiRollupRow[] }>(
    `/analytics/kpi?workspace_id=${WORKSPACE_ID}&metric=${encodeURIComponent(metric)}&minutes=${minutes}`
  );
}

export async function getAnomalyAnalytics(minutes = 1440) {
  return request<{
    counts: Array<{ metric: string; bucket: string; count: number }>;
    severity_p95: Array<{ metric: string; bucket: string; p95: number }>;
  }>(`/analytics/anomalies?workspace_id=${WORKSPACE_ID}&minutes=${minutes}`);
}

export async function getAudioAnalytics(minutes = 1440) {
  return request<{ rows: Array<{ metric: string; preset: string; renders: number; avg_render_ms: number }> }>(
    `/analytics/audio?workspace_id=${WORKSPACE_ID}&minutes=${minutes}`
  );
}

export async function getAnomalies(metric?: string) {
  const metricQuery = metric ? `&metric=${encodeURIComponent(metric)}` : '';
  return request<{ items: Anomaly[] }>(
    `/anomalies?workspace_id=${WORKSPACE_ID}&minutes=1440&severity_min=0${metricQuery}`
  );
}

export async function queueAudioRender(input: {
  anomaly_id?: string;
  metric_name: string;
  start: string;
  end: string;
  preset: string;
  duration: number;
  controls?: {
    tempo_min?: number;
    tempo_max?: number;
    intensity?: number;
    glitch_density?: number;
    harmonizer_mix?: number;
    pad_depth?: number;
    ambient_mix?: number;
    rhythm_density?: number;
  };
}) {
  return request<{ job_id: string; status: string }>('/audio/render', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: WORKSPACE_ID, ...input })
  });
}

export async function getAudioJob(jobId: string) {
  return request<{
    status: string;
    artifact_id?: string;
    error?: string;
    preset: string;
    metric_name: string;
    controls?: Record<string, number>;
  }>(`/audio/jobs/${jobId}?workspace_id=${WORKSPACE_ID}`);
}

export async function getAudioUrl(artifactId: string, format: 'wav' | 'mp3' = 'mp3') {
  return request<{ url: string }>(
    `/audio/${artifactId}/url?workspace_id=${WORKSPACE_ID}&fmt=${format}&expires_seconds=600`
  );
}

export async function askCopilot(input: {
  question: string;
  mode?: string;
  context?: Record<string, unknown>;
}) {
  return request<CopilotResponse>('/copilot/ask', {
    method: 'POST',
    body: JSON.stringify({
      workspace_id: WORKSPACE_ID,
      user_id: 'frontend-user',
      question: input.question,
      mode: input.mode || 'anomaly_explainer',
      context: input.context || {}
    })
  });
}

export async function ingestDocs(docs: Array<{ title: string; text: string; source_url?: string; metadata?: Record<string, unknown> }>) {
  return request<{ docs: number; chunks_inserted: number }>('/rag/ingest', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: WORKSPACE_ID, docs })
  });
}

export async function runEval(limit = 5) {
  return request<{
    run_id: string;
    cases: number;
    overall_pass_rate: number;
    results: Array<{ case_id: number; question: string; grounded_pass: boolean; safety_pass: boolean; notes: string; sample_answer: string }>;
  }>('/rag/eval/run', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: WORKSPACE_ID, limit })
  });
}

export async function getEvalResults() {
  return request<{ run_id?: string; overall_pass_rate?: number; items: EvalResult[] }>(
    `/rag/eval/results?workspace_id=${WORKSPACE_ID}`
  );
}

export async function getBriefs() {
  return request<{ items: Brief[] }>(`/briefs?workspace_id=${WORKSPACE_ID}`);
}

export async function createBrief(input: { title: string; body_md: string; data?: Record<string, unknown> }) {
  return request<{ brief_id: string }>('/briefs/create', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: WORKSPACE_ID, ...input })
  });
}

export async function getPromptApprovals() {
  return request<{
    items: Array<{
      request_id: string;
      status: string;
      approved_by?: string;
      created_at: string;
      prompt_preview: string;
      sources_preview: SourceItem[];
    }>;
  }>('/admin/promptops/requests');
}

export async function approvePrompt(requestId: string) {
  return request<{ status: string }>('/admin/promptops/approve', {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId, approved_by: 'frontend-admin', workspace_id: WORKSPACE_ID })
  });
}

export async function triggerExecBrief() {
  return request<{ triggered: boolean; summary: Record<string, unknown> }>('/admin/trigger-exec-brief', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: WORKSPACE_ID, actor: 'frontend-admin' })
  });
}
