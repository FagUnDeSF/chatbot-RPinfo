import { useCallback, useMemo, useReducer, useRef } from "react";

import { askQa } from "../services/qaClient";
import type { ChatController, ChatMessage } from "../types/chat";
import type { QaClientFailure, QaClientSuccess } from "../types/qa";
import { createProtocol, formatTime, rowsToAnswer } from "../utils/format";

const HINTS = [
  "ex.: qual a margem da banana prata neste mes?",
  "ex.: tem ruptura grande de iogurte hoje na loja 03?",
  "ex.: como esta o custo medio do arroz tio joao?"
] as const;

interface State {
  messages: readonly ChatMessage[];
  draft: string;
  isSubmitting: boolean;
  statusLabel: string;
}

type Action =
  | { type: "set-draft"; value: string }
  | { type: "start"; question: string; user: ChatMessage; loading: ChatMessage }
  | { type: "finish"; loadingId: string; message: ChatMessage }
  | { type: "cancel"; loadingId: string; message: ChatMessage }
  | { type: "reformulate"; question: string };

const initialState: State = {
  messages: [],
  draft: "",
  isSubmitting: false,
  statusLabel: "ERP CONECTADO"
};

export function useChatController(seedMessages?: readonly ChatMessage[]): ChatController {
  const [state, dispatch] = useReducer(reducer, {
    ...initialState,
    messages: seedMessages ?? []
  });
  const abortRef = useRef<AbortController | null>(null);
  const hint = useMemo(() => HINTS[Math.floor(Math.random() * HINTS.length)], []);

  const submitQuestion = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (trimmed.length < 3 || abortRef.current !== null) return;

    const abortController = new AbortController();
    abortRef.current = abortController;
    const id = crypto.randomUUID();
    const userMessage: ChatMessage = {
      id: `user-${id}`,
      kind: "user",
      question: trimmed,
      timestamp: formatTime()
    };
    const loadingMessage: ChatMessage = {
      id: `loading-${id}`,
      kind: "loading",
      question: trimmed,
      startedAt: Date.now()
    };
    dispatch({ type: "start", question: trimmed, user: userMessage, loading: loadingMessage });

    const result = await askQa({ question: trimmed, signal: abortController.signal });
    abortRef.current = null;
    const message = result.ok ? buildAssistantMessage(trimmed, result) : buildAttentionMessage(result);
    dispatch({ type: "finish", loadingId: loadingMessage.id, message });
  }, []);

  const submit = useCallback(async () => {
    await submitQuestion(state.draft);
  }, [state.draft, submitQuestion]);

  const retry = useCallback(async (question: string) => {
    await submitQuestion(question);
  }, [submitQuestion]);

  const cancel = useCallback(() => {
    const loading = state.messages.find((message) => message.kind === "loading");
    if (!loading) return;
    abortRef.current?.abort();
    abortRef.current = null;
    dispatch({
      type: "cancel",
      loadingId: loading.id,
      message: {
        id: `attention-${crypto.randomUUID()}`,
        kind: "attention",
        variant: "cancelled",
        question: loading.question,
        message: "Consulta cancelada.",
        actionLabel: null,
        retryAt: null,
        timestamp: formatTime()
      }
    });
  }, [state.messages]);

  const reformulate = useCallback((question: string) => {
    dispatch({ type: "reformulate", question });
  }, []);

  return {
    messages: state.messages,
    draft: state.draft,
    isSubmitting: state.isSubmitting,
    hint,
    statusLabel: state.statusLabel,
    setDraft: (value) => dispatch({ type: "set-draft", value }),
    submit,
    cancel,
    retry,
    reformulate
  };
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "set-draft":
      return { ...state, draft: action.value };
    case "start":
      return {
        ...state,
        draft: "",
        isSubmitting: true,
        messages: [...state.messages, action.user, action.loading]
      };
    case "finish":
      return {
        ...state,
        isSubmitting: false,
        messages: state.messages.map((message) =>
          message.id === action.loadingId ? action.message : message
        )
      };
    case "cancel":
      return {
        ...state,
        isSubmitting: false,
        messages: state.messages.map((message) =>
          message.id === action.loadingId ? action.message : message
        )
      };
    case "reformulate":
      return { ...state, draft: action.question };
  }
}

function buildAssistantMessage(question: string, result: QaClientSuccess): ChatMessage {
  const isInsufficient = result.body.answer_type === "insufficient_data";
  const variant = isInsufficient
    ? "insufficient"
    : result.headers.escalation !== null || result.body.escalation_granted
      ? "escalated"
      : result.headers.fallback !== null || result.body.fallback_active
        ? "fallback"
        : "success";

  return {
    id: `assistant-${result.body.answer_id}`,
    kind: "assistant",
    variant,
    question,
    answer: isInsufficient
      ? "Nao tenho dado suficiente para responder com seguranca. A consulta nao encontrou base operacional suficiente. Posso responder se voce passar um codigo SKU ou periodo mais preciso."
      : rowsToAnswer(result.body.rows),
    source: result.body.source ?? "n/a",
    premises: result.body.premises.length > 0 ? result.body.premises : ["criterios insuficientes para consulta conclusiva"],
    timestamp: formatTime(),
    protocol: createProtocol(),
    headers: result.headers,
    elapsedMs: result.elapsedMs,
    raw: result.body
  };
}

function buildAttentionMessage(result: QaClientFailure): ChatMessage {
  const messageByKind: Record<QaClientFailure["kind"], { message: string; action: string | null }> = {
    pii: {
      message: "Sua pergunta inclui um CPF, CNPJ ou identificador pessoal. Reformule sem esse dado e tento responder de novo.",
      action: "Reformular"
    },
    "rate-limit": {
      message: `Voce atingiu o limite de perguntas desta hora (200/h perfil DIRECAO). Tente de novo as ${result.retryAt ?? "proxima janela"}.`,
      action: null
    },
    forbidden: {
      message: "Voce atingiu o limite de perguntas desta hora (200/h perfil DIRECAO). Tente de novo as proxima janela.",
      action: null
    },
    server: {
      message: "Nao consegui conversar com o ERP agora. Tente de novo em alguns segundos.",
      action: "Tentar de novo"
    },
    network: {
      message: "Nao consegui conversar com o ERP agora. Tente de novo em alguns segundos.",
      action: "Tentar de novo"
    }
  };
  const copy = messageByKind[result.kind];
  return {
    id: `attention-${crypto.randomUUID()}`,
    kind: "attention",
    variant: result.kind === "network" ? "server" : result.kind,
    question: result.question,
    message: copy.message,
    actionLabel: copy.action,
    retryAt: result.retryAt,
    timestamp: formatTime()
  };
}
