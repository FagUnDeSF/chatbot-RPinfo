export type QaAnswerType = "answered" | "insufficient_data";

export interface QaIntentResponse {
  kind: string;
  erp_query_name: string | null;
}

export interface QaAskResponse {
  answer_id: string;
  answer_type: QaAnswerType;
  intent: QaIntentResponse;
  rows: readonly Record<string, string | number | boolean | null>[];
  source: string | null;
  premises: readonly string[];
  reason: string | null;
  prompt_version: string;
  provider: string;
  model: string | null;
  fallback_active: boolean;
  fallback_reason: string | null;
  escalation_requested: boolean;
  escalation_granted: boolean;
  pii_redacted_pos_egress: boolean;
  pii_redacted_categories: readonly string[];
}

export interface QaClientHeaders {
  fallback: string | null;
  escalationDenied: string | null;
  escalation: string | null;
}

export interface QaClientSuccess {
  ok: true;
  body: QaAskResponse;
  headers: QaClientHeaders;
  elapsedMs: number;
}

export type QaClientErrorKind = "pii" | "rate-limit" | "forbidden" | "server" | "network";

export interface QaClientFailure {
  ok: false;
  kind: QaClientErrorKind;
  retryAt: string | null;
  question: string;
  elapsedMs: number;
}

export type QaClientResult = QaClientSuccess | QaClientFailure;
