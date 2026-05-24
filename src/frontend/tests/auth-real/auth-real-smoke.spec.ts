import { expect, request, test } from "@playwright/test";

const backendUrl = process.env.AUTH_REAL_BACKEND_URL ?? "http://127.0.0.1:8000";
const username = process.env.AUTH_REAL_USERNAME ?? "rp-direcao";
const token = process.env.AUTH_REAL_TOKEN;

test("auth-real-smoke conecta ao backend local sem mock", async () => {
  expect(
    token,
    "Defina AUTH_REAL_TOKEN com o valor local autorizado antes de rodar npm run test:e2e:auth-real"
  ).toBeTruthy();

  const api = await request.newContext({ baseURL: backendUrl });
  const response = await api.post("/api/v1/qa/ask", {
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Username": username,
      "X-Internal-Token": token ?? "",
      "X-LLM-Escalate": "sonnet",
      "Idempotency-Key": `auth-real-${crypto.randomUUID()}`
    },
    data: { question: "Qual o risco de estoque parado da loja 2?" }
  });

  expect(
    response.status(),
    `Backend local deve estar em ${backendUrl} com auth interna real configurada`
  ).toBe(200);

  const body = (await response.json()) as {
    answer_id?: string;
    provider?: string | null;
    fallback_active?: boolean;
  };
  expect(body.answer_id).toBeTruthy();

  const llmHeaders = [
    response.headers()["x-llm-fallback"],
    response.headers()["x-llm-escalation-denied"],
    response.headers()["x-llm-escalation"]
  ].filter(Boolean);
  expect(
    llmHeaders.length,
    "Backend real deve expor ao menos um header X-LLM-* quando fallback ou escalation for acionado"
  ).toBeGreaterThan(0);

  await api.dispose();
});
