---
tipo: spike
spike_id: S2-SPK-10-ml-eval-continuo
dimensao: c
titulo: Retraining Triggers — Vocabulario Fechado
cand: S2-C10
sprint: 002
skill_autora: ml-engineer-senior
data: 2026-05-22
bloqueio_fase_2: F-FUT-5/BL-013
vocabulario_fechado:
  - drift-threshold
  - nova-categoria-intent
  - regressao-em-eval
  - decisao-direcao
referencias:
  - spikes/S2-SPK-10-ml-eval-continuo/drift-design.md
  - equipe/tech-lead-senior/adrs/0005-llm-provider.md
  - equipe/pm-senior/sprints/sprint-002.md
---

# Dimensao (c) — Retraining Triggers (Vocabulario Fechado)

> **Spike T** — entrega plano + design; sem codigo de producao (CG-08).
> Design vale para **Fase 1** (uso proprio Decio). Fase 2 B2B exige novo parecer LGPD + ADR (F-FUT-5/BL-013).

## 1. Definicao de "retraining" no contexto do qa_orchestrator

No qa_orchestrator, "retraining" nao significa re-treinar um modelo ML classico com novos dados (nao ha pesos a ajustar). Significa **revisar e promover uma nova versao do qa_orchestrator** — tipicamente uma nova versao de prompt, de intent classifier, de eval-set, ou de configuracao do pipeline. O vocabulario de triggers e padronizado para que qualquer skill (pm-senior, ml-engineer-senior, ai-engineer-senior, Direcao) use os mesmos 4 valores ao registrar, comunicar e acionar uma revisao.

**Por que vocabulario fechado:** vocabulario aberto gera ambiguidade nos handoffs (ex.: "o sistema esta ruim" nao e acionavel; "drift-threshold cruzado em latency_p95 7-day rolling" e acionavel e rastreavel). Os 4 valores sao exaustivos para Fase 1 — qualquer situacao que exija revisao do qa_orchestrator cabe em um (ou mais) desses 4.

## 2. Os 4 valores canonicos

---

### T-01 — `drift-threshold`

**Definicao:** data drift OU model drift cruzou um threshold definido em `drift-design.md` e o sinal persistiu por pelo menos 2 janelas de verificacao consecutivas (evitar falso alarme por pico isolado).

**Criterio de ativacao:**

| Sinal de drift | Threshold de ativacao |
|---|---|
| Intent distribution shift | >20pp em intent individual em 2 janelas de 7 dias consecutivas |
| Input length p95 | >100% acima do baseline p95 em 2 janelas de 7 dias consecutivas |
| PII boundary coverage | >15pp acima do baseline em 2 janelas de 7 dias consecutivas |
| cost_per_call_p95 | >$0,008 em 2 janelas de 7 dias consecutivas |
| latency_p95 | >2000ms em 2 janelas de 7 dias consecutivas |
| cache_hit_rate | <40% em 2 janelas de 7 dias consecutivas |

**Observacao:** um unico pico isolado acima do threshold amarelo nao ativa `drift-threshold`. Dois picos consecutivos (vermelho persistente) ativam.

**Responsavel por detectar:** ml-engineer-senior (monitoring automatizado baseado nos campos NIVEL-3 do AuditEvent).

**Responsavel por decidir acao:** pm-senior (recebe alerta; decide se inicia revisao de prompt ou abre spike de investigacao).

**Acao subsequente:**
1. ml-engineer emite handoff `monitorar-drift-alerta` para pm-senior + devops com metrica especifica, threshold cruzado e janela.
2. pm-senior avalia se e necessario abrir nova cand de revisao (ex.: cand de ajuste de prompt S3-CXX).
3. Se nova versao de prompt proposta: gate-eval pre-promocao obrigatorio via `canary-design.md`.

**Nao ativa automaticamente:** pipeline-retraining automatizado requer aprovacao pm-senior. Nao ha auto-retraining em Fase 1.

---

### T-02 — `nova-categoria-intent`

**Definicao:** o intent classifier (NIVEL-0 §2.2 do sistema pos-S2-C07) nao cobre uma classe nova de query que representa >5% do volume de interacoes em janela de 7 dias.

**Criterio de ativacao:** query nova que:
- Retorna `response_type=FORBIDDEN` por `intent=nao_reconhecido` (nao por violacao de politica)
- Representa topico factual do negocio supermercado que o sistema deveria poder responder
- Acumula >5% das queries na janela de 7 dias (relevancia suficiente para justificar expansao)

**Exemplos de nova categoria:**
- Usuarios comecam a perguntar sobre CMV (custo de mercadoria vendida) — intent nao coberto na versao atual
- Usuarios comecam a perguntar sobre margens por fornecedor — intent nao coberto
- Usuarios perguntam sobre sazonalidade de vendas — intent nao coberto

**Responsavel por detectar:** pm-senior (a partir de feedback direto de Decio) OU ml-engineer-senior (via analise de queries com `response_type=FORBIDDEN`).

**Responsavel por decidir acao:** Direcao (Decio) — e Decio quem decide se o sistema deve cobrir o topico novo; nao e decisao tecnica unilateral.

**Acao subsequente:**
1. pm-senior abre handoff para Direcao com amostras das queries nao-cobertas.
2. Direcao decide: (a) expandir cobertura → abre nova cand de expansao de intent, OU (b) manter restricao → registra decisao em memory/SHARED.md como comportamento intencional.
3. Se expansao aprovada: ml-engineer atualiza intent classifier + adiciona casos RP Info ao eval-set + gate-eval pre-producao.

**Nao ativa automaticamente:** expansao de dominio exige decisao Direcao (CG-08 aplicavel — mudanca de escopo do produto).

---

### T-03 — `regressao-em-eval`

**Definicao:** o eval-set rodado sobre o qa_orchestrator champion vigente falhou >=1 caso golden em qualquer execucao periodica ou ad hoc.

**Criterio de ativacao:** golden 2/2 PASS e o SLA irreduzivel. Qualquer falha de golden em qualquer execucao = ativacao imediata (sem esperar 2 janelas consecutivas — diferente do drift-threshold).

**Exemplos de ativacao:**
- Mudanca de configuracao do Anthropic API que altera comportamento do Haiku 4.5
- Nova versao de prompt v0.2.1 implantada com bug que quebra uma pergunta golden
- Mudanca no dado ERP que invalida a resposta esperada de um golden

**Responsavel por detectar:** ml-engineer-senior (execucao automatizada do eval-set via CI semanal + ad hoc pre/pos qualquer mudanca de configuracao).

**Responsavel por decidir acao:** ml-engineer-senior (tecnico — acao imediata requerida).

**Acao subsequente (por ordem de prioridade):**
1. **Imediato:** verificar se o qa_orchestrator champion vigente ainda esta respondendo corretamente ao golden na producao (via log do AuditEvent com `prompt_version=v0.2`).
2. Se producao tambem falha: emitir alerta critico para pm-senior + Direcao.
3. Se apenas no eval-set (producao OK): investigar se a expectativa do golden esta desatualizada vs comportamento novo do sistema.
4. Corrigir (rollback de mudanca recente OU atualizar expectativa do golden se mudanca foi intencional).
5. Re-rodar eval-set completo para confirmar 2/2 PASS.
6. Registrar root cause em handoff ml-engineer → pm-senior.

**Nao ha tolerancia:** golden nao pode ficar falhando enquanto investigacao acontece. Se a investigacao levar >4h: escalar para pm-senior + Direcao imediatamente.

---

### T-04 — `decisao-direcao`

**Definicao:** Direcao (Decio Fagundes) decide iniciar uma revisao do qa_orchestrator por motivo estrategico, independente de drift detectado ou regressao tecnica.

**Exemplos de ativacao:**
- Revisao obrigatoria do ADR-0005 a cada 90 dias (proxima: 2026-08-22)
- Nova regulamentacao ou mudanca de politica interna que exige ajuste de comportamento
- Expansao da rede de lojas com novos tipos de query (ex.: loja de formato diferente)
- Decisao de promover prompt v0.3 por razao estrategica antes de qualquer drift detectado
- Decisao de aumentar ou reduzir budget LLM (impacta ADR-0005 D3)

**Criterio de ativacao:** decisao declarada por Decio, tipicamente via pm-senior (sessao de review ou feedback direto).

**Responsavel por detectar:** pm-senior (monitora calendario de revisoes + acompanha feedback Direcao).

**Responsavel por decidir acao:** Direcao (motivo estrategico) + ml-engineer-senior (execucao tecnica).

**Acao subsequente:**
1. pm-senior documenta a decisao de Direcao em `memory/SHARED.md` ou handoff formal.
2. ml-engineer abre spike de revisao com escopo declarado pela Direcao.
3. **Gate-eval pre-promocao obrigatorio mesmo com decisao-direcao** (AP-2 LLM CRITICAL preservado): a Direcao pode decidir INICIAR uma revisao, mas a PROMOCAO de nova versao exige gate-eval aprovado. Sem gate-eval = CG-08 violado.
4. Canary deployment conforme `canary-design.md` antes de promocao completa.

**Por que gate-eval e obrigatorio mesmo com decisao-direcao:** AP-2 LLM CRITICAL proibe promocao silenciosa de prompt v0.X → v0.X+1 sem gate-eval explicito. A Direcao tem autoridade para INICIAR o processo e para APROVAR a promocao pos-gate; a Direcao nao pode bypassar o gate tecnicamente (esse seria o risco de regressao silenciosa que AP-2 protege contra).

---

## 3. Tabela resumida do vocabulario fechado

| Valor | Quem detecta | Quem decide | Auto-aciona retraining? | Gate-eval obrigatorio? |
|---|---|---|---|---|
| `drift-threshold` | ml-engineer (automatizado) | pm-senior | NAO — pm-senior decide | SIM (pre-promocao) |
| `nova-categoria-intent` | pm-senior ou ml-engineer | Direcao | NAO — Direcao decide | SIM (pre-producao) |
| `regressao-em-eval` | ml-engineer (CI automatizado) | ml-engineer (imediato) | NAO — acao de correcao | SIM (pos-correcao) |
| `decisao-direcao` | pm-senior (calendario) | Direcao | NAO — pm-senior orquestra | SIM (AP-2 LLM CRITICAL) |

**Invariante:** NENHUM dos 4 triggers auto-aciona retraining sem aprovacao humana em Fase 1. O trigger e um sinal de inicio de investigacao e processo — a decisao de promover uma nova versao sempre passa por gate-eval + aprovacao pm-senior ou Direcao (conforme CG-08).

## 4. Registro de triggers

Todo trigger ativado deve ser registrado em handoff ml-engineer-senior → pm-senior com:
- `trigger_valor`: um dos 4 valores do vocabulario fechado
- `trigger_data`: data de ativacao
- `trigger_sinal`: metrica especifica que ativou (ex.: `latency_p95=2100ms em janela 2026-05-28 a 2026-06-03`)
- `trigger_responsavel`: quem detectou
- `acao_imediata`: o que foi feito imediatamente
- `acao_proposta`: o que se propoe como proximo passo

## 5. Bloqueio Fase 2 reafirmado

Os 4 retraining triggers acima sao desenhados para Fase 1 (populacao interna RP Info, uso proprio Decio). Para Fase 2 (B2B), os criterios de drift serao diferentes (populacao maior, intents mais variados, requisitos LGPD de escopo diferente) — exige novo design de triggers + novo parecer LGPD + ADR (F-FUT-5/BL-013 ativo).

## 6. Mapeamento cross-vocab

Este mapeamento documenta a relacao entre o vocabulario fechado de retraining-triggers e os vocabularios fechados de outros processos do escritorio. Guidance operacional para quando o primeiro trigger se materializar (Sprint 003+).

### 6.1 Vereditos de processos do escritorio vs triggers

| Processo | Vocabulario fechado | Relacao com retraining-triggers |
|---|---|---|
| **Parecer-cand PM** | `autoriza` / `autoriza_com_ajuste` / `rejeita` / `alternativa` | `decisao-direcao` (T-04): quando PM emite `autoriza` para revisao de prompt, isso materializa T-04; `rejeita` arquiva o trigger sem acao |
| **Gate-2-aceite PM** | `aprovado` / `aprovado-com-ressalva` / `recusado` | Gate pre-promocao obrigatorio para todos os 4 triggers: sem `aprovado` do Gate-2, nenhum trigger avanca para producao (CG-08) |
| **Code-review TL** | `aprovar` / `aprovar-com-condicoes` / `mudancas-solicitadas` / `bloqueado` | Gate-3 obrigatorio pre-canary (`canary-design.md` §3): TL deve emitir `aprovar` ou `aprovar-com-condicoes` antes de qualquer fracao de trafego |
| **Gate-qa-cand QA** | `APROVADO` / `APROVADO COM RESSALVA` / `RECUSADO` / `PIVOT` | Se cand de revisao de prompt existir: gate-qa antes do gate-eval pre-promocao; `RECUSADO` bloqueia canary |

### 6.2 Vocabulario S2-C08 (monitoring alerts) vs triggers

O sistema de monitoring S2-C08 emite alertas com os seguintes vocabularios fechados. O mapeamento abaixo descreve como alertas S2-C08 podem ativar retraining-triggers.

| Tipo de alerta S2-C08 | Recomendacao S2-C08 | Pode acionar retraining-trigger | Trigger ativado |
|---|---|---|---|
| `cost-spike` | `investigar-anomalia` | Sim, se persistente (2 janelas consecutivas) | `drift-threshold` (T-01): cost_per_call_p95 > $0,008 |
| `cost-absoluto-budget-violado` | `escalar-direcao-budget` | Sim, via decisao Direcao | `decisao-direcao` (T-04): revisao de budget + ADR-0005 |
| `latency-p95-degradacao` | `investigar-anomalia` | Sim, se persistente (2 janelas consecutivas) | `drift-threshold` (T-01): latency_p95 > 2000ms |
| `cache-hit-rate-baixo` | `investigar-anomalia` | Sim, se persistente (2 janelas consecutivas) | `drift-threshold` (T-01): cache_hit_rate < 40% |
| `fallback-rate-alto` | `acionar-degraded-mode` | Condicional — ver §6.3 | Ver §6.3 |

**Nota:** `manter-config` como recomendacao S2-C08 indica que nenhum threshold foi cruzado — nenhum retraining-trigger e ativado nesse caso.

### 6.3 Mapeamento operacional: fallback-rate-alto → possivel regressao-em-eval

O alerta `fallback-rate-alto` com recomendacao `acionar-degraded-mode` (S2-C08) tem um caminho condicional para retraining-trigger:

1. `fallback-rate-alto` indica indisponibilidade frequente do provider Anthropic → `acionar-degraded-mode` e acao S2-C08 imediata, gerida por ai-engineer-senior/devops (nao e trigger de retraining direto).
2. Se, durante ou apos o modo degradado, o eval golden for re-rodado e um golden falhar → esse evento ativa `regressao-em-eval` (T-03), independentemente da causa raiz.
3. O `fallback-rate-alto` **em si nao e** um retraining-trigger — e um sinal de infraestrutura. Pode **co-ocorrer** com regressao de qualidade se o modo degradado alterar o comportamento do qa_orchestrator.

**Guidance operacional:** quando `fallback-rate-alto` for resolvido com `acionar-degraded-mode`, ml-engineer-senior deve re-rodar o eval-set assim que o sistema retornar ao modo normal. Se golden falhar nessa re-rodada: ativar `regressao-em-eval` (T-03) conforme §T-03 deste documento.

**Cross-link:** `drift-design.md` §3.1 (golden test regression) + `canary-design.md` §5 (rollback triggers).

## 7. Cross-links

- `drift-design.md` — define os thresholds usados pelo trigger `drift-threshold`
- `plano.md` — o eval-set que alimenta o trigger `regressao-em-eval` e `nova-categoria-intent`
- `canary-design.md` — o processo de promocao que todos os 4 triggers devem seguir antes de produzir nova versao
- `case-study/aprendizados/2026-05_ml-engineering-qa-orchestrator-decio.md` — explicacao acessivel para Direcao
- `equipe/pm-senior/`: vereditos de parecer-cand (`autoriza|autoriza_com_ajuste|rejeita|alternativa`) e gate-2-aceite (`aprovado|aprovado-com-ressalva|recusado`) — ver §6.1
- `equipe/tech-lead-senior/code-reviews/`: vereditos code-review (`aprovar|aprovar-com-condicoes|mudancas-solicitadas|bloqueado`) — ver §6.1
- S2-C08 vocabulario de alertas (`cost-spike|cost-absoluto-budget-violado|latency-p95-degradacao|cache-hit-rate-baixo|fallback-rate-alto`) e recomendacoes (`manter-config|acionar-degraded-mode|investigar-anomalia|escalar-direcao-budget`) — ver §6.2
