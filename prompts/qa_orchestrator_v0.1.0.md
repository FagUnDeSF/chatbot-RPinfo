---
prompt_id: qa_orchestrator
versao: 0.1.0
modelo: null
provider: stub-deterministico
provider_role: prova-controlada-sprint-001
temperature_target: 0.2
max_tokens: null
eval_set: eval-sets/qa_orchestrator_v0.1.0_baseline.yaml
versao_prod: false
sprint_origem: 001
cand_origem: S1-C04
atualizado_em: 2026-05-21
---

# Prompt versionado — qa_orchestrator v0.1.0

> Fase Sprint 001: prova controlada. Provider real (LLM) NÃO é usado; o orquestrador roda com `StubDeterministicLlmProvider` que renderiza premissas via template puro sobre as linhas retornadas pelo `ErpReadonlyService`. Este arquivo de prompt declara o contrato esperado quando LLM real for promovido (post-Sprint 001) e governa o template determinístico atual.

## 1. Decisão (ADR-style)

- **Decisão.** Orquestrador determinístico de Q&A com classificador de intent por keywords + execução via camada `erp_readonly` + renderização templated. LLM real entra em sprint futura, com ADR-LLM emitido pelo Tech-Lead-Senior antes da promoção.
- **Alternativas avaliadas.**
  - (a) LLM real (Anthropic Claude Haiku 4.5) desde Sprint 001 — descartado: introduz custo + latência + risco de alucinação em prova controlada sem ganho sobre baseline determinístico para os 2 cenários da cand.
  - (b) Função-pura sem prompt versionado — descartado: viola disciplina inegociável do pack ("prompt do orquestrador entra em arquivo versionado").
- **Rationale.** Cumpre o critério de aceite literal sem materializar risco de alucinação; mantém prompt versionado vivo para futura promoção; observabilidade e Fallback Matrix já operam sob contrato real.

## 2. System prompt (para futura promoção LLM real)

```
Você é um orquestrador determinístico de pergunta-resposta sobre dado ERP read-only.

Restrições inegociáveis:
- Responda SOMENTE com base em rows recebidos do serviço `erp_readonly`. NUNCA invente número, SKU, loja, período, venda, estoque ou margem.
- Se as rows estiverem vazias, retorne negativa honesta com motivo `dado_indisponivel`.
- Se o intent não estiver na allowlist (`inventory_risk`, `sales_summary`), retorne negativa honesta com motivo `intent_nao_reconhecido`.
- NUNCA persista ou ecoe identificador pessoal (CPF, CNPJ, WhatsApp, conversa). Se a pergunta contiver, ignore o identificador e processe apenas o intent estrutural.
- Sempre declare a `source` consultada e as `premises` factuais que sustentam a resposta.
- Margem e estoque fantasma NUNCA podem ser apresentados como acurados antes de comparação contra relatório oficial (CG-06).

Persona: assistente interno técnico, tom factual, sem opinião.
```

## 3. User template

```
Pergunta: {{question}}
Intent classificado: {{intent_kind}}
Query ERP: {{erp_query_name | none-if-unknown}}
Rows: {{rows_json}}
```

## 4. Few-shot examples

(Reservado para promoção LLM real. Sprint 001 não usa few-shots — stub determinístico.)

## 5. Fallback Matrix (CRITICAL — inegociável do pack)

| Estado do dado / permissão                              | Caminho     | answer_type           | reason                          | Saída                                                                                                |
|---------------------------------------------------------|-------------|-----------------------|---------------------------------|------------------------------------------------------------------------------------------------------|
| Intent reconhecido + query allowlistada + rows ≥ 1      | Positivo    | `answered`            | (vazio)                         | `rows` + `source` + `premises` factuais; `reason = null`                                             |
| Intent reconhecido + query allowlistada + rows == 0     | Negativa    | `insufficient_data`   | `dado_indisponivel`             | `rows = []`; `premises = []`; `source` preservada; `reason = "dado_indisponivel"`                    |
| Intent NÃO reconhecido                                  | Negativa    | `insufficient_data`   | `intent_nao_reconhecido`        | `rows = []`; `premises = []`; `source = null`; `reason = "intent_nao_reconhecido"`                   |
| Intent reconhecido + sem permissão RBAC (audit recusa)  | Negativa    | (exception ao caller) | `role_cannot_record_source`     | erro HTTP 403 surfaceado pelo controller; ver §7                                                     |
| LLM real indisponível (provider down) — POST-SPRINT 001 | Negativa    | `insufficient_data`   | `provider_indisponivel`         | reservado para roadmap; stub determinístico não tem esse estado                                      |
| Resposta candidata contém identificador pessoal cru     | Negativa    | (bloqueio interno)    | `pii_detectado_pre_egress`      | reservado para roadmap (filtro PII pós-LLM); stub não gera output livre, então não dispara em S001   |

**Princípio:** o orquestrador NUNCA cai em alucinação. Toda saída ou é templated sobre rows reais, ou é negativa honesta com motivo enumerado.

## 6. Estrutura observável (metadado registrado por chamada)

Por chamada (sem persistir payload bruto):

- `answer_id` (uuid)
- `intent.kind` (`inventory_risk` | `sales_summary` | `unknown`)
- `intent.erp_query_name` (string ou null)
- `answer_type` (`answered` | `insufficient_data`)
- `reason` (string enumerada ou null)
- `source` (string ou null — copiada de `ErpReadonlyResult.source`)
- `row_count` (int)
- `prompt_version` (= `0.1.0`)
- `provider` (= `stub-deterministico` em S001)
- `model` (= null em S001)
- `latency_ms` (medido pelo trace, registrado em observability/llm/qa_orchestrator_trace.yaml)

CG-04 aplicado: nenhum identificador pessoal bruto (CPF, CNPJ, WhatsApp, conversa) é persistido — `AuditQueryEvent` registra apenas metadado estrutural via `AuditService.record_query_event`.

## 7. Budget e orçamento declarado

- **Sprint 001 — stub determinístico:** custo por chamada = USD 0; latência alvo p95 < 50 ms (em-process Python sem rede); cache-hit rate n/a (sem provider remoto).
- **Roadmap (não aplicado em S001):** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) como candidato inicial; custo estimado < USD 0,002 por chamada para janelas curtas; latência alvo p95 < 1500 ms; ADR-LLM do TL deve fixar provider + modelo + cota antes de promoção.

## 8. Guardrails NIVEL-0 declarados (Sprint 001)

Decisão de não invocar `guarda-em-camadas` bloqueante nesta cand: stub determinístico + output 100% templated + zero processamento de PII + sem prompt injection efetiva (parser determinístico antes do LLM-stub). Guardrails operacionais aplicados:

- **Input.** Pergunta validada por DTO Pydantic: comprimento mínimo 3 / máximo 500 caracteres; nenhum payload aninhado livre.
- **Intent classifier.** Allowlist fechada de intents (`inventory_risk`, `sales_summary`); qualquer outro → `unknown` → negativa honesta.
- **ERP query.** Apenas queries no allowlist do `InMemoryErpReadonlyRepository` chegam ao backend; limite de linhas controlado por `ErpReadonlyService` (configurado `erp_readonly_max_rows`).
- **Output.** Template puro sobre rows estruturadas — sem string format livre vindo do usuário.
- **Audit.** Toda chamada registra metadado via `AuditSource.QA_ORCHESTRATOR` sem payload bruto.

**Fronteira explícita.** Antes de promover provider real (LLM) para produção, é OBRIGATÓRIO invocar `ai-engineer-senior > guarda-em-camadas` para gerar handoff cross-skill V5 com Security definindo política (input rules + output rules + permissões + threshold de prompt injection + fallback acionável). Sem essa V5, dispara AP-13-LLM CRITICAL.

## 9. Eval set associado

`eval-sets/qa_orchestrator_v0.1.0_baseline.yaml` — 2 casos golden (cenário positivo + cenário de negativa) suficientes para a cand controlada. Gate de promoção quantitativo: ambos passam.

## 10. Versionamento e ciclo

- Patch (`0.1.x`): ajuste de keyword, premise rendering, ou texto auxiliar sem mudança de contrato.
- Minor (`0.x.0`): adição de intent na allowlist OU adição de provider real opcional (mantém stub como fallback).
- Major (`x.0.0`): mudança de contrato de DTO `QaAskRequest`/`QaAskResponse` OU substituição definitiva do stub por LLM real (requer ADR-LLM emitida pelo TL + handoff `guarda-em-camadas` V5 Security).
