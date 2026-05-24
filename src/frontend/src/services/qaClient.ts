import type { QaAskResponse, QaClientFailure, QaClientResult } from "../types/qa";

const API_BASE_URL = "/api/v1";

interface AskOptions {
  question: string;
  signal: AbortSignal;
  escalate?: boolean;
}

export async function askQa(options: AskOptions): Promise<QaClientResult> {
  const startedAt = performance.now();
  const idempotencyKey = `front-${crypto.randomUUID()}`;

  try {
    const response = await fetch(`${API_BASE_URL}/qa/ask`, {
      method: "POST",
      signal: options.signal,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        ...(options.escalate ? { "X-LLM-Escalate": "sonnet" } : {})
      },
      body: JSON.stringify({ question: options.question })
    });

    const elapsedMs = Math.round(performance.now() - startedAt);

    if (!response.ok) {
      return {
        ok: false,
        kind: mapStatusToErrorKind(response.status),
        retryAt: buildRetryAt(response.headers.get("Retry-After")),
        question: options.question,
        elapsedMs
      };
    }

    const body = (await response.json()) as QaAskResponse;
    return {
      ok: true,
      body,
      headers: {
        fallback: response.headers.get("X-LLM-Fallback"),
        escalationDenied: response.headers.get("X-LLM-Escalation-Denied"),
        escalation: response.headers.get("X-LLM-Escalation")
      },
      elapsedMs
    };
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - startedAt);
    if (error instanceof DOMException && error.name === "AbortError") {
      return {
        ok: false,
        kind: "network",
        retryAt: null,
        question: options.question,
        elapsedMs
      };
    }
    return {
      ok: false,
      kind: "network",
      retryAt: null,
      question: options.question,
      elapsedMs
    };
  }
}

function mapStatusToErrorKind(status: number): QaClientFailure["kind"] {
  if (status === 422) return "pii";
  if (status === 429) return "rate-limit";
  if (status === 403) return "forbidden";
  if (status >= 500) return "server";
  return "network";
}

function buildRetryAt(retryAfter: string | null): string | null {
  if (retryAfter === null) return null;
  const seconds = Number.parseInt(retryAfter, 10);
  if (!Number.isFinite(seconds)) return null;
  const retryDate = new Date(Date.now() + seconds * 1_000);
  return retryDate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
