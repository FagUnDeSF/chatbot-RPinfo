import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import path from "node:path";

const qaResponse = {
  answer_id: "ans-demo-001",
  answer_type: "answered",
  intent: { kind: "inventory_risk", erp_query_name: "inventory_risk_sample" },
  rows: [{ sku: "SKU-001", produto: "banana prata", loja: 3, margem_pct: 47.2 }],
  source: "erp_readonly.fixture.inventory",
  premises: ["loja 03", "snapshot 22/05/2026 23h59", "SKU-001 banana prata"],
  reason: null,
  prompt_version: "0.2.0",
  provider: "stub-deterministico",
  model: null,
  fallback_active: false,
  fallback_reason: null,
  escalation_requested: false,
  escalation_granted: false,
  pii_redacted_pos_egress: false,
  pii_redacted_categories: []
} as const;

test("fluxo Q&A feliz renderiza fonte, premissas e impressao operacional", async ({ page }) => {
  await page.route("**/api/v1/qa/ask", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "X-LLM-Escalation": "sonnet" },
      body: JSON.stringify(qaResponse)
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "ChatRP Info" })).toBeVisible();
  await expect(page.getByLabel("Pergunta para o ERP")).toBeFocused();

  await page.getByLabel("Pergunta para o ERP").fill("qual a margem da banana prata neste mes na loja 03?");
  await page.getByRole("button", { name: /Perguntar/ }).click();

  await expect(page.getByLabel("Resposta do assistente")).toContainText("FONTE");
  await expect(page.getByLabel("Resposta do assistente")).toContainText("PREMISSAS");
  await expect(page.getByText("modelo escalado")).toBeVisible();
  await expect(page.getByText("SKU-001 banana prata")).toBeVisible();
});

test("axe-core nao encontra violacoes criticas na tela principal", async ({ page }) => {
  await page.goto("/?state=success");
  const results = await new AxeBuilder({ page }).analyze();
  const severe = results.violations.filter((violation) =>
    violation.impact === "critical" || violation.impact === "serious"
  );
  expect(severe).toHaveLength(0);
});

test("captura PNG dos 9 estados visiveis", async ({ page }) => {
  const states = ["empty", "loading", "success", "escalated", "fallback", "cg05", "422", "403", "500"] as const;
  const evidenceDir = path.resolve(process.cwd(), "..", "..", "equipe", "frontend-senior", "screenshots", "S3-C02");

  for (const state of states) {
    await page.goto(`/?state=${state}`);
    await expect(page.getByRole("heading", { name: "ChatRP Info" })).toBeVisible();
    await page.screenshot({
      path: path.join(evidenceDir, `${state}.png`),
      fullPage: true
    });
  }
});
