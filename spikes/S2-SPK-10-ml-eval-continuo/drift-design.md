---
tipo: spike
spike_id: S2-SPK-10-ml-eval-continuo
dimensao: b
titulo: Drift Detection Metodologico para o qa_orchestrator
cand: S2-C10
sprint: 002
skill_autora: ml-engineer-senior
data: 2026-05-22
bloqueio_fase_2: F-FUT-5/BL-013
referencias:
  - equipe/tech-lead-senior/adrs/0005-llm-provider.md
  - src/backend/chatbot_rpinfo/domain/entities/audit_event.py
  - equipe/ai-engineer-senior/guarda-em-camadas-V5.md
  - equipe/pm-senior/prompt-packs/sprint-002/pack-G.md
apoio_cross_skill: ai-engineer-senior (19 campos NIVEL-3 AuditEvent)
---

# Dimensao (b) — Drift Detection Metodologico

> **Spike T** — entrega plano + design; sem codigo de producao (CG-08).
> Design vale para **Fase 1** (uso proprio Decio). Fase 2 B2B exige novo parecer LGPD + ADR (F-FUT-5/BL-013).

## 1. Contexto: o que e "drift" no qa_orchestrator

No qa_orchestrator, "drift" significa que o sistema esta respondendo diferente do que no baseline de referencia (pos-LLM real S2-C07) — seja porque as **perguntas mudaram** (data drift) ou porque a **qualidade das respostas mudou** (model drift). O objetivo do drift detection e detectar essas mudancas **antes que o usuario perceba degradacao**, permitindo acionar os retraining triggers de forma proativa.

**Fonte de dados:** os **campos NIVEL-3 do AuditEvent** sao a materia-prima do drift detection. Esses campos ja sao persistidos pelo qa_orchestrator pos-S2-C07 para cada interacao. Nenhum dado adicional precisa ser coletado — o sinal existe; precisa ser monitorado.

**Campos NIVEL-3 do AuditEvent usados para drift detection** (18 campos mapeados abaixo; source-of-truth: `src/backend/chatbot_rpinfo/domain/entities/audit_event.py`):

| Campo | Relevancia para drift |
|---|---|
| `intent` | distribuicao de intents — sinal primario de data drift |
| `response_type` | ANSWERED/FORBIDDEN/ERROR — sinal de model drift (taxa de falha) |
| `provider_used` / `model_used` | confirmar que Haiku 4.5 e o modelo em uso |
| `prompt_version` | confirmar que prompt v0.2 e a versao ativa (champion) |
| `cache_hit` | taxa de cache hit — sinal de model drift (performance ADR-0005) |
| `cost_usd` | custo por chamada — sinal de model drift (budget ADR-0005) |
| `latency_ms_total` | latencia total — sinal de model drift (SLA ADR-0005) |
| `latency_ms_provider_call` | latencia so do provider — isola degradacao de rede vs LLM |
| `pii_detectado_pre_egress` | proporcao de queries com PII — sinal de data drift (mudanca de comportamento usuario) |
| `content_policy_blocked` | taxa de bloqueio — sinal de data drift (novos vetores adversariais) |
| `refusal_evasion_attempted` | taxa de evasao — sinal de data drift (ataques mais sofisticados) |
| `escalation_requested` / `escalation_granted` | taxa de escalation Sonnet — sinal de model drift (Haiku insuficiente) |
| `fallback_active` / `fallback_reason` | taxa de fallback — sinal de provider drift (Anthropic indisponibilidade) |
| `input_tokens_total` / `output_tokens_total` | volume de tokens — sinal de complexidade de query (data drift) |

Os demais campos (`event_id`, `username`, `role`, `occurred_at`, `request_id`, `correlation_id_upstream`) sao de rastreabilidade, nao de drift detection.

## 2. Data Drift — via distribuicao de input

Data drift = as **perguntas que chegam** estao mudando em relacao ao baseline de referencia.

### 2.1 Metrica primaria: distribuicao de intents

**Sinal:** campo `intent` do AuditEvent.  
**Baseline de referencia:** distribuicao de intents nas primeiras 14 dias de uso real pos-S2-C07 (periodo de baselining). Registrar: frequencia relativa por intent (ex.: `vendas=40%`, `estoque=35%`, `prevencao=15%`, `outros=10%`).

**Threshold de alarme:**
- **Amarelo** (alerta, nao bloqueante): qualquer intent com shift absoluto >10pp em janela de 7 dias vs baseline (ex.: `vendas` cai de 40% para 28% = shift de 12pp).
- **Vermelho** (alerta ativo, investigar em 48h): qualquer intent com shift absoluto >20pp OU surgimento de novo intent cobrindo >5% das queries em janela de 7 dias.

**Populacao minima:** janela de calculo exige >= 50 queries para evitar ruido estatistico. Abaixo de 50 queries/7 dias: nao emitir alarme de distribuicao (volume insuficiente); emitir apenas aviso de baixo volume.

**Como calcular:** frequencia relativa de cada valor de `intent` nas queries da janela vs frequencia no baseline. Distancia absoluta por intent (nao KL divergence — simplicidade de implementacao futura).

### 2.2 Metrica secundaria: comprimento de query (proxy de complexidade)

**Sinal:** campo `input_tokens_total` do AuditEvent.  
**Baseline de referencia:** percentil 50 e percentil 95 de `input_tokens_total` nas primeiras 14 dias.

**Threshold de alarme:**
- **Amarelo**: p95 de `input_tokens_total` sobe >50% vs baseline p95 em janela 7 dias.
- **Vermelho**: p95 sobe >100% vs baseline (queries ficando muito mais longas — possivel mudanca de uso).

**Interpretacao:** queries muito mais longas podem indicar tentativas de prompt injection mais sofisticadas ou novo padrao de uso (ex.: usuarios colando tabelas de dados em vez de perguntas curtas).

### 2.3 Metrica terciaria: cobertura PII boundary

**Sinal:** campo `pii_detectado_pre_egress` do AuditEvent.  
**Baseline de referencia:** proporcao de queries com `pii_detectado_pre_egress=True` nas primeiras 14 dias.

**Threshold de alarme:**
- **Amarelo**: proporcao sobe >5pp em janela 7 dias (ex.: de 3% para 8% das queries contem PII detectado pre-egress).
- **Vermelho**: proporcao sobe >15pp (mudanca de comportamento significativa).

**Interpretacao:** aumento de PII pode indicar usuarios enviando dados mais sensiveis — o NIVEL-1 §3.1 da guarda-em-camadas-V5 esta cobrindo, mas o padrao de uso mudou e merece investigacao.

## 3. Model Drift — via qualidade de output vs baseline

Model drift = o **qa_orchestrator esta respondendo pior** que no baseline — seja em qualidade, custo ou latencia.

### 3.1 Metrica primaria: regressao em golden tests

**Sinal:** rodar o eval-set com os 2 casos golden contra o qa_orchestrator champion vigente.  
**Frequencia:** semanal (automatizado via CI) + ad hoc quando `response_type=ERROR` acima do threshold.

**Threshold:**
- **CRITICAL (vermelho imediato):** qualquer golden que falhe (golden 2/2 PASS e o SLA minimo irreduzivel). Um golden que falha ativa imediatamente `retraining-trigger regressao-em-eval` (ver `retraining-triggers.md`).

**Nota:** os golden nao monitoram drift no sentido estatistico — eles sao um teste de regressao binario. Qualquer falha = alerta imediato, nao uma tendencia.

### 3.2 Metrica secundaria: custo por chamada

**Sinal:** campo `cost_usd` do AuditEvent.  
**Baseline de referencia:** p95 de `cost_usd` nas primeiras 14 dias (estimativa: ~$0,003/call com Haiku 4.5 em uso normal).

**Thresholds (ADR-0005 D3):**
- **Amarelo:** `cost_per_call_p95 > $0,005` em janela 7 dias.
- **Vermelho:** `cost_per_call_p95 > $0,008` em janela 7 dias.
- **CRITICAL:** custo total acumulado no mes projetado para ultrapassar USD 30 antes do fim do mes (spending limit ADR-0005 D3).

**Interpretacao:** custo subindo pode indicar queries mais longas chegando (data drift correlacionado), prompt menos eficiente (model drift), ou cache_hit_rate caindo.

### 3.3 Metrica terciaria: latencia

**Sinal:** campo `latency_ms_total` do AuditEvent.  
**Baseline de referencia:** p95 de `latency_ms_total` nas primeiras 14 dias (estimativa: ~1000ms com Haiku 4.5).

**Thresholds (ADR-0005 D1):**
- **Amarelo:** `latency_p95 > 1500ms` em janela 7 dias.
- **Vermelho:** `latency_p95 > 2000ms` em janela 7 dias.
- **CRITICAL:** `latency_p99 > 5000ms` (timeout timeout por experiencia do usuario).

**Interpretacao:** latencia subindo pode indicar degradacao do provider Anthropic (verificar `latency_ms_provider_call` vs `latency_ms_total` para isolar) ou queries mais complexas.

### 3.4 Metrica quaternaria: taxa de cache hit

**Sinal:** campo `cache_hit` do AuditEvent.  
**Baseline de referencia:** proporcao de `cache_hit=True` nas primeiras 14 dias (meta: >=70% per ADR-0005 D4).

**Thresholds (ADR-0005 D4):**
- **Amarelo:** `cache_hit_rate < 60%` em janela 7 dias.
- **Vermelho:** `cache_hit_rate < 40%` em janela 7 dias.

**Interpretacao:** cache_hit_rate caindo indica que o system prompt mudou (nova versao de prompt quebrou o cache) OU a distribuicao de queries ficou muito esparsa (poucas queries repetidas suficientes para warm cache).

## 4. Janela temporal e cadencia de verificacao

| Tipo de drift | Janela de calculo | Cadencia de verificacao | Populacao minima |
|---|---|---|---|
| Intent distribution shift | 7 dias rolling | Diaria (automatizado) | 50 queries/janela |
| Input length shift | 7 dias rolling | Diaria (automatizado) | 50 queries/janela |
| PII boundary coverage | 7 dias rolling | Semanal (relatorio) | 50 queries/janela |
| Golden test regression | Por execucao | Semanal (CI) + ad hoc | N/A (teste binario) |
| Cost per call p95 | 7 dias rolling | Diaria (automatizado) | 50 queries/janela |
| Latency p95 | 7 dias rolling | Diaria (automatizado) | 50 queries/janela |
| Cache hit rate | 7 dias rolling | Diaria (automatizado) | 50 queries/janela |

**Periodo de baselining:** primeiras 14 dias de uso real pos-S2-C07. Durante esse periodo, alertas amarelos sao informativos (sem acao requerida); alertas vermelhos ainda requerem investigacao.

**Modo degradado durante baselining:** se baseline ainda nao estabelecido, emitir alertas com flag `baseline_incompleto: true` — nao acionar pipeline-retraining automaticamente.

## 5. Integracao com os campos NIVEL-3 do AuditEvent

O drift detection **nao requer novos campos** no AuditEvent. Os campos NIVEL-3 ja implementados por S2-C07 cobrem todos os sinais necessarios — 18 campos sao mapeados como sinais de drift na secao 1; os demais campos NIVEL-3 sao de rastreabilidade. Isso confirma que a decisao de design do S2-C07 de expandir o AuditEvent para NIVEL-3 foi correta e previdente.

Apoio cross-skill confirmado: `ai-engineer-senior` e a skill dona da implementacao do `qa_orchestrator` e da guarda-em-camadas-V5. Os campos NIVEL-3 sao territorio do ai-engineer-senior; ml-engineer-senior **consome** esses campos como input de drift detection, sem alterar a entidade AuditEvent.

## 6. Bloqueio Fase 2 reafirmado

O drift detection desenhado aqui monitorar a populacao de Fase 1 (usuarios internos RP Info — Decio + funcionarios da rede). Para Fase 2 (clientes B2B externos), a distribuicao de intents e a linha de base de custo/latencia serao completamente diferentes — exige re-baseline completo + novo parecer LGPD + ADR (F-FUT-5/BL-013 ativo).

## 7. Cross-links

- `plano.md` — o eval-set de producao que alimenta o sinal de golden regression
- `retraining-triggers.md` — os 4 valores que sao acionados quando drift cruza threshold
- `canary-design.md` — as mesmas metricas de drift sao usadas como criterio de rollback canary
- `case-study/aprendizados/2026-05_ml-engineering-qa-orchestrator-decio.md` — explicacao acessivel para Direcao
