import type { AssistantMessage, AttentionMessage, ChatMessage } from "../types/chat";
import { createProtocol } from "../utils/format";

type DemoState =
  | "empty"
  | "loading"
  | "success"
  | "escalated"
  | "fallback"
  | "cg05"
  | "422"
  | "403"
  | "500";

const question = "qual a margem da banana prata neste mes na loja 03?";
const timestamp = "14:27";

export function createDemoState(value: string | null): readonly ChatMessage[] | undefined {
  if (value === null || value === "empty") return value === "empty" ? [] : undefined;
  if (!isDemoState(value)) return undefined;
  if (value === "empty") return [];

  const user: ChatMessage = {
    id: "demo-user",
    kind: "user",
    question,
    timestamp
  };

  if (value === "loading") {
    return [
      user,
      {
        id: "demo-loading",
        kind: "loading",
        question,
        startedAt: Date.now()
      }
    ];
  }

  if (value === "422" || value === "403" || value === "500") {
    return [user, buildAttention(value)];
  }

  return [user, buildAssistant(value)];
}

function isDemoState(value: string): value is DemoState {
  return ["empty", "loading", "success", "escalated", "fallback", "cg05", "422", "403", "500"].includes(value);
}

function buildAssistant(state: Exclude<DemoState, "empty" | "loading" | "422" | "403" | "500">): AssistantMessage {
  const insufficient = state === "cg05";
  return {
    id: `demo-assistant-${state}`,
    kind: "assistant",
    variant: insufficient ? "insufficient" : state,
    question,
    answer: insufficient
      ? "Nao tenho dado suficiente para responder com seguranca. O produtor regional X nao aparece no relatorio de margem atual. Posso responder se voce passar o codigo SKU ou consultar compras do mes."
      : "A banana prata da loja 03 aparece com margem estimada de 47,2%. O custo medio ficou em R$ 4,21/kg e a venda media em R$ 7,98/kg no periodo consultado.",
    source: insufficient ? "n/a - SKU nao encontrado" : "erp_readonly.fixture.inventory",
    premises: insufficient
      ? ["busca por descricao regional X", "nenhuma correspondencia operacional no snapshot atual"]
      : ["loja 03", "snapshot 22/05/2026 23h59", "SKU-001 banana prata"],
    timestamp,
    protocol: createProtocol(new Date("2026-05-23T14:27:00")),
    headers: {
      fallback: state === "fallback" ? "stub-deterministico" : null,
      escalationDenied: null,
      escalation: state === "escalated" ? "sonnet" : null
    },
    elapsedMs: 1120,
    raw: null
  };
}

type AttentionDemoState = "422" | "403" | "500";

function buildAttention(state: AttentionDemoState): AttentionMessage {
  const byState: Record<AttentionDemoState, Pick<AttentionMessage, "variant" | "message" | "actionLabel">> = {
    "422": {
      variant: "pii",
      message: "Sua pergunta inclui um CPF, CNPJ ou identificador pessoal. Reformule sem esse dado e tento responder de novo.",
      actionLabel: "Reformular"
    },
    "403": {
      variant: "rate-limit",
      message: "Voce atingiu o limite de perguntas desta hora (200/h perfil DIRECAO). Tente de novo as 16:00.",
      actionLabel: null
    },
    "500": {
      variant: "server",
      message: "Nao consegui conversar com o ERP agora. Tente de novo em alguns segundos.",
      actionLabel: "Tentar de novo"
    }
  };
  const copy = byState[state];
  return {
    id: `demo-attention-${state}`,
    kind: "attention",
    question,
    retryAt: state === "403" ? "16:00" : null,
    timestamp: "15:01",
    ...copy
  };
}
