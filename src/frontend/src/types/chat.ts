import type { QaAskResponse, QaClientHeaders } from "./qa";

export type ChatMessageKind = "user" | "loading" | "assistant" | "attention";
export type AssistantVariant = "success" | "escalated" | "fallback" | "insufficient";
export type AttentionVariant = "pii" | "rate-limit" | "forbidden" | "server" | "cancelled";

export interface UserMessage {
  id: string;
  kind: "user";
  question: string;
  timestamp: string;
}

export interface LoadingMessage {
  id: string;
  kind: "loading";
  question: string;
  startedAt: number;
}

export interface AssistantMessage {
  id: string;
  kind: "assistant";
  variant: AssistantVariant;
  question: string;
  answer: string;
  source: string;
  premises: readonly string[];
  timestamp: string;
  timestampMs: number;
  sequenceNumber: number;
  protocol: string;
  headers: QaClientHeaders;
  elapsedMs: number;
  raw: QaAskResponse | null;
}

export interface AttentionMessage {
  id: string;
  kind: "attention";
  variant: AttentionVariant;
  question: string;
  message: string;
  actionLabel: string | null;
  retryAt: string | null;
  timestamp: string;
}

export type ChatMessage = UserMessage | LoadingMessage | AssistantMessage | AttentionMessage;

export interface ChatController {
  messages: readonly ChatMessage[];
  draft: string;
  isSubmitting: boolean;
  hint: string;
  statusLabel: string;
  setDraft: (value: string) => void;
  submit: () => Promise<void>;
  cancel: () => void;
  retry: (question: string) => Promise<void>;
  reformulate: (question: string) => void;
}
