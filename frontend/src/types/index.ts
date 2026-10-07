export type AnalysisStatus =
  | 'SUCCESS'
  | 'PARTIAL'
  | 'FAILED'
  | 'UNAVAILABLE'
  | 'NOT_VERIFIED'
  | 'INSUFFICIENT_EVIDENCE'
  | 'PENDING'
  | 'created';

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface DependencyStatus {
  status: 'ready' | 'unavailable' | 'degraded';
  message: string;
  latency_ms: number | null;
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded' | 'unavailable';
  timestamp: string;
  services: {
    database: DependencyStatus;
    redis: DependencyStatus;
    minio: DependencyStatus;
  };
}

export interface Investigation {
  id: string;
  title?: string | null;
  description?: string | null;
  status: AnalysisStatus | string;
  vera_version: string;
  created_at: string;
  updated_at: string;
  evidence_count?: number;
  evidence?: Array<Record<string, unknown>>;
  result_summary?: string | null;
  state?: Record<string, unknown> | null;
}

export interface CreateInvestigationPayload {
  title?: string;
  description?: string;
  text?: string;
  input_type?: string;
  metadata?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id?: string;
    details?: unknown;
  };
}
