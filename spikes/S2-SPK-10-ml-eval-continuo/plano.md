---
tipo: spike
spike_id: S2-SPK-10-ml-eval-continuo
dimensao: a
titulo: Plano de Eval-Set Evolution
cand: S2-C10
sprint: 002
skill_autora: ml-engineer-senior
data: 2026-05-22
bloqueio_fase_2: F-FUT-5/BL-013
referencias:
  - equipe/pm-senior/prompt-packs/sprint-002/pack-G.md
  - equipe/pm-senior/aceites/2026-05-22_sprint-002_cand-S2-C07_gate-2.md
  - spikes/S1-SPK-05-acuracia-estoque-margem/README.md
---

# Dimensao (a) — Plano de Eval-Set Evolution

> **Spike T** — entrega plano + design; sem codigo de producao (CG-08).
> Design vale para **Fase 1** (uso proprio Decio). Fase 2 B2B exige novo parecer LGPD + ADR + 7 pre-requisitos juridicos (F-FUT-5/BL-013).

## 1. Estado atual do eval-set

**Versao:** v0.2.0  
**Total de casos:** 30  
**Status baseline:** golden 2/2 PASS — F-FUT-1 materializada no aceite Gate 2 S2-C07 (2026-05-22)

| Categoria | Qtd | Proposito |
|---|---|---|
| golden | 2 | Perguntas nucleares do negocio RP Info que NUNCA podem falhar |
| prompt injection | 10 | Tentativas de injecao de instrucao via pergunta |
| jailbreak | 10 | Tentativas de contornar restricoes do sistema |
| refusal evasion | 3 | Perguntas reformuladas para passar pela triagem de intents |
| RP Info domain | 5 | Perguntas reais do dominio supermercado |

**Ancoragem:** Pack G sprint-002 §"30 casos eval-set v0.2.0" (source-of-truth PM).

## 2. Estrategia de adição de casos por categoria

### 2.1 Golden — crescimento por curadoria humana Decio

**Quem decide:** Direcao (Decio Fagundes) com apoio pm-senior.  
**Como adicionar:**
1. Decio identifica uma pergunta que o sistema respondeu corretamente E que representa um caso nucleo do negocio (ex.: "qual o ticket medio da loja X no ultimo mes?").
2. pm-senior valida que o caso nao e duplicata de golden existente.
3. ml-engineer-senior adiciona ao eval-set com `categoria=golden`, executa o eval-set completo.
4. Se o caso novo passa: promovido a golden permanente; se falha: abre retraining-trigger `regressao-em-eval` imediatamente.

**Criterio de golden:** pergunta factual que qualquer funcionario experiente de supermercado saberia que o sistema DEVE responder corretamente + a resposta e verificavel contra dado ERP real.

**Ritmo:** ad hoc (sem cadencia fixa). Estimativa: 1-2 novos golden por trimestre nos primeiros 12 meses.

### 2.2 Adversarial (prompt injection + jailbreak + refusal evasion) — crescimento por vetores detectados em producao

**Quem decide:** ml-engineer-senior com base em sinais dos campos NIVEL-3 do AuditEvent.  
**Como adicionar:**
1. Monitor de producao detecta query com `content_policy_blocked=True` OU `refusal_evasion_attempted=True` que nao esta coberta pelo eval-set.
2. ml-engineer classifica o vetor (injection / jailbreak / evasion).
3. Adiciona ao eval-set com a expectativa de `response_type=FORBIDDEN` (o sistema DEVE recusar).
4. Executa eval-set completo para confirmar cobertura.

**Criterio de adversarial:** query nova que representa tecnica de ataque nao coberta pelas 23 existentes; nao adicionar variantes cosmeticas do mesmo padrao (custo sem ganho de cobertura).

**Ritmo:** reativo — quando vetor novo detectado em producao. Estimativa: 0-3 por mes nos primeiros 6 meses.

### 2.3 RP Info domain — crescimento por intent novos do supermercado

**Quem decide:** pm-senior com base em feedback Decio.  
**Como adicionar:**
1. Decio identifica topico novo que funcionarios estao perguntando (ex.: "como calcular giro de estoque?" — novo intent que o sistema deveria cobrir).
2. pm-senior abre handoff para ml-engineer com sample de 3-5 perguntas representativas.
3. ml-engineer adiciona ao eval-set com expectativa de `response_type=ANSWERED` (o sistema DEVE responder).
4. Se o sistema ainda nao responde: abre retraining-trigger `nova-categoria-intent` (ver `retraining-triggers.md`).

**Criterio de RP Info domain:** topico factual do negocio supermercado cobrivel via dado ERP allowlisted.

**Ritmo:** reativo ao feedback Decio. Estimativa: 0-2 por mes nos primeiros 12 meses.

## 3. Versioning do eval-set

**Schema de versao:** `vMAJOR.MINOR.PATCH`

| Bump | Quando |
|---|---|
| PATCH (v0.2.0 → v0.2.1) | Adicao de 1-3 casos sem mudanca de estrutura; correcao de expectativa errada |
| MINOR (v0.2.0 → v0.3.0) | Nova categoria de caso OR mudanca de expectativa de >= 5 casos |
| MAJOR (v0.2.0 → v1.0.0) | Redesign completo do eval-set (ex.: Fase 2 B2B com populacao diferente) |

**Onde vive:** `eval-sets/` (path ja existente no projeto).  
**Formato:** YAML por caso com `id`, `categoria`, `input`, `expected_response_type`, `expected_intent`, `adicionado_em`, `adicionado_por`.

**Backward compatibility:** toda versao nova deve rodar sobre o qa_orchestrator champion vigente sem regredir os golden existentes (golden nao pode falhar em nova versao do eval-set sem investigacao formal).

## 4. Frequencia de revisao do eval-set completo

| Fase | Frequencia | Gatilho de revisao antecipada |
|---|---|---|
| Meses 1-3 (baselining) | Trimestral | Qualquer golden que falhe em producao |
| Meses 4-12 | Adaptativa (baseada em drift) | Drift de intent distribution >15% em 7 dias (ver `drift-design.md`) |
| Apos 12 meses | Semestral minima | Revisao do ADR-0005 (90 dias — 2026-08-22) + cada revisao de 90 dias |

**Definicao de revisao completa:** rodar o eval-set com prompt vigente + anotar novos falsos positivos/negativos + propor adicoes/remocoes + gerar relatorio para pm-senior.

## 5. Criterio de remocao de caso do eval-set

Um caso pode ser removido quando:
1. O caso e **duplicata funcional** de outro (mesma tecnica, mesma expectativa, mesmo dominio).
2. O **dominio ficou obsoleto** (ex.: intent removido do sistema por decisao Direcao).
3. A **expectativa mudou** por decisao explicita de negocio (nao por regressao do modelo).

Remocao exige registro no changelog do eval-set com `removido_em`, `removido_por`, `motivo`.

## 6. Bloqueio Fase 2 reafirmado

O eval-set v0.2.0 e seus descendentes sao desenhados para **Fase 1** (uso proprio Decio, populacao = funcionarios da rede de supermercados RP Info). A Fase 2 (B2B, clientes externos) tem populacao de usuarios diferente, escopo de perguntas diferente e requisitos LGPD diferentes — exige novo parecer LGPD + ADR + 7 pre-requisitos juridicos (F-FUT-5/BL-013) antes de qualquer promessas de cobertura.

## 7. Cross-links

- `drift-design.md` — como a distribuicao do eval-set de producao alimenta o sinal de drift
- `retraining-triggers.md` — quando uma variacao no eval-set dispara retraining
- `canary-design.md` — como o eval-set e usado como gate pre-promocao no canary
- `case-study/aprendizados/2026-05_ml-engineering-qa-orchestrator-decio.md` — explicacao em linguagem Direcao
- S1-SPK-05 format reference: `spikes/S1-SPK-05-acuracia-estoque-margem/README.md`
