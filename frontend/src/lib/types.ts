export type WorkspaceId = string;

export interface KpiRollupRow {
  bucket: string;
  avg: number;
  min: number;
  max: number;
  points: number;
}

export interface Anomaly {
  anomaly_id: string;
  metric_name: string;
  window_start: string;
  window_end: string;
  severity: number;
  features: Record<string, number>;
  correlations: Array<Record<string, unknown>>;
  detected_at: string;
}

export interface SourceItem {
  id: number;
  title: string;
  snippet: string;
  url?: string;
  score?: number;
  meta?: Record<string, unknown>;
}

export interface CopilotResponse {
  query_id: string;
  workspace_id: string;
  answer: string;
  top_sources: SourceItem[];
  confidence: number;
  prompt_version: string;
  provider: string;
}

export interface Brief {
  brief_id: string;
  title: string;
  body_md: string;
  data: Record<string, unknown>;
  created_at: string;
}

export interface EvalResult {
  case_id: number;
  question: string;
  grounded_pass: boolean;
  safety_pass: boolean;
  notes: string;
  created_at: string;
}

export interface EventMessage {
  id: number;
  type: string;
  payload: Record<string, unknown>;
  created_at: string;
}
