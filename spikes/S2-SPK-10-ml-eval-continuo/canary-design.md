---
tipo: spike
spike_id: S2-SPK-10-ml-eval-continuo
dimensao: d
titulo: Canary Deployment Design
cand: S2-C10
sprint: 002
skill_autora: ml-engineer-senior
data: 2026-05-22
bloqueio_fase_2: F-FUT-5/BL-013
ap2_llm_critical_preservado: true
referencias:
  - equipe/tech-lead-senior/adrs/0005-llm-provider.md
  - equipe/ai-engineer-senior/guarda-em-camadas-V5.md
  - spikes/S2-SPK-10-ml-eval-continuo/retraining-triggers.md
  - spikes/S2-SPK-10-ml-eval-continuo/drift-design.md
---

# Dimensao (d) — Canary Deployment Design

> **Spike T** — entrega plano + design; sem codigo de producao (CG-08).
> Design vale para **Fase 1** (uso proprio Decio). Fase 2 B2B exige novo parecer LGPD + ADR (F-FUT-5/BL-013).
>
> **AP-2 LLM CRITICAL PRESERVADO:** este design proibe explicitamente qualquer forma de promocao silenciosa de versao de prompt. Toda mudanca de prompt_version do champion para o challenger exige gate-eval aprovado + sinal explicito de promocao + aprovacao Direcao (CG-08).

## 1. Contexto: por que canary deployment para o qa_orchestrator

O qa_orchestrator nao e um modelo ML classico com pesos — e um pipeline LLM com versoes de prompt, configuracoes e intent classifier. Uma nova versao (ex.: v0.3.0) pode ter comportamento melhor em alguns casos e pior em outros. O canary deployment permite **testar a nova versao em fracao do trafego real** antes de promover para 100% — detectando regressoes antes que todos os usuarios sejam afetados.

**Invariante central (AP-2 LLM CRITICAL):** a transicao entre versoes de prompt NUNCA e silenciosa. Cada resposta do qa_orchestrator registra `prompt_version` no AuditEvent — o usuario e a Direcao podem sempre saber qual versao respondeu qual query. Um path de promocao silenciosa (ex.: "se o challenger tiver mais confianca, usar ele automaticamente") viola AP-2 LLM CRITICAL e e expressamente proibido por ADR-0005 D2.

## 2. Champion-vs-Challenger: definicao de papeis

**Champion:** qa_orchestrator v0.2.0 com prompt v0.2 (estado pos S2-C07, aceite Gate 2 2026-05-22).
- O champion e o que esta em producao hoje.
- Metrica de referencia: golden 2/2 PASS + cost_per_call_p95 <= $0,005 + latency_p95 <= 1500ms + cache_hit_rate >= 70%.

**Challenger:** qa_orchestrator v0.3.0 com prompt v0.3+ (Sprint 003+, quando desenvolvido).
- O challenger e a nova versao proposta.
- Deve passar o gate-eval completo antes de qualquer fracao de trafego.
- Nao existe challenger hoje — este design e para quando Sprint 003+ propuser uma nova versao.

**Regra fundamental:** o challenger substitui o champion APENAS apos:
1. Gate-eval pre-promocao PASS (30/30 casos eval-set vigente).
2. Aprovacao CG-08: carimbo Direcao explicito para promover nova versao de prompt.
3. Canary rollout completo sem rollback acionado.

## 3. Gate-eval pre-promocao (obrigatorio, AP-2 LLM CRITICAL)

Antes de qualquer fracao de trafego real chegar ao challenger:

**Gate 1 — Eval-set completo:**
- Rodar o eval-set vigente (v0.2.0 ou superior) contra o challenger.
- Threshold: 30/30 casos PASS (incluindo os 2 golden sem excecao).
- Se qualquer golden falhar: challenger reprovado — nao avancar para canary.
- Se qualquer adversarial falhar: investigar se e regressao ou caso desatualizado.
- Resultado registrado em handoff ml-engineer-senior → pm-senior com ID do eval-set e data.

**Gate 2 — Aprovacao Direcao (CG-08):**
- pm-senior apresenta resultado do Gate 1 para Direcao.
- Decio carimbos a promocao explicitamente (mesmo mecanismo que a aprovacao de ADRs).
- Sem carimbo Direcao = canary nao inicia.

**Gate 3 — Revisao TL:**
- tech-lead-senior revisa o diff da nova versao de prompt (o que mudou de v0.2 para v0.3).
- Verifica que AP-2 LLM CRITICAL esta preservado na implementacao.
- Verifica que audit metadado (`prompt_version=v0.3`) esta sendo registrado no AuditEvent.

Somente apos todos os 3 gates aprovados: iniciar canary rollout.

## 4. Canary Rollout — fases

### Fase 0: Pre-canary (gate-eval)

**Fracao de trafego:** 0% (challenger nao recebe trafego real).  
**Duracao:** ate gates 1+2+3 aprovados (sem SLA fixo — depende do gate).  
**Sinais monitorados:** resultado do eval-set (PASS/FAIL por caso).  
**Criterio de avanco:** 30/30 PASS + aprovacao Direcao + aprovacao TL.  
**Criterio de rollback:** N/A (challenger nao esta em trafego ainda).

### Fase 1: Canary 10%

**Fracao de trafego:** 10% das queries → challenger (v0.3.0); 90% → champion (v0.2.0).  
**Duracao minima:** 48 horas com populacao minima de 30 queries no challenger (sem populacao minima nao avancar para Fase 2).  
**Sinais monitorados:** as mesmas metricas de drift-design.md §3 mas comparando challenger vs champion:
- golden regression no challenger (qualquer falha = rollback imediato)
- cost_per_call_p95 challenger vs champion (tolerancia: challenger pode ser ate 10% mais caro sem rollback)
- latency_p95 challenger vs champion (tolerancia: challenger pode ser ate 20% mais lento sem rollback)
- cache_hit_rate challenger vs champion (tolerancia: challenger pode ter ate 10pp a menos sem rollback)
- error_rate challenger vs champion (tolerancia: 0% — qualquer `response_type=ERROR` acima do champion = rollback)

**Criterio de avanco para Fase 2:**
- 48h sem rollback ativado
- Populacao >= 30 queries no challenger
- Nenhuma metrica critica degradada vs champion

**Criterio de rollback:** qualquer golden falha OU error_rate acima do champion OU custo >20% acima do champion em janela 48h.

**Sinal explicito de promocao:** o roteador de requisicoes registra `prompt_version=v0.3` no AuditEvent para cada query que vai para o challenger. Nenhuma query passa de v0.2 para v0.3 sem esse registro. Sem sinal = violacao AP-2 LLM CRITICAL.

### Fase 2: Canary 50%

**Fracao de trafego:** 50% challenger / 50% champion.  
**Duracao minima:** 48 horas com populacao minima de 100 queries no challenger.  
**Sinais monitorados:** idem Fase 1 + comparacao estatistica mais robusta (maior N).  
**Criterio de avanco para Fase 3:** idem Fase 1 + sem degradacao de satisfacao Decio (qualitativo — feedback via pm-senior).  
**Criterio de rollback:** idem Fase 1.

### Fase 3: Promocao completa (100%)

**Fracao de trafego:** 100% challenger / 0% champion.  
**Champion anterior:** mantido em standby por 7 dias (possibilidade de rollback manual se regressao lenta aparecer).  
**Criterio de conclusao:** 7 dias sem rollback acionado → champion anterior pode ser arquivado.  
**Registro:** handoff ml-engineer-senior → pm-senior declarando promocao completa + metricas pos-promocao + novo champion registrado em contexto-projeto §1.9.

## 5. Rollback automatico — regras

**Gatilho de rollback automatico (qualquer fase):**
1. `response_type=ERROR` no challenger acima da taxa do champion em janela 1h.
2. Qualquer golden falha no challenger.
3. `cost_per_call_p95` do challenger >20% acima do champion em janela 48h.
4. `latency_p95` do challenger >2000ms em janela 48h.
5. `cache_hit_rate` do challenger <40% em janela 48h.

**O que rollback faz:** reverter toda fracao de trafego para o champion (100% v0.2.0). Nenhuma query vai para o challenger ate investigacao concluida e nova aprovacao de canary.

**Rollback nao e fracasso:** rollback e o mecanismo de seguranca esperado. Um challenger que precisa de rollback volta para o ciclo de desenvolvimento antes de nova tentativa de canary.

**Notificacao de rollback:** alerta imediato para pm-senior + Direcao com metrica especifica que ativou o rollback.

## 6. Ausencia de fallback automatico (AP-2 LLM CRITICAL)

**Explicitamente proibido:**
- Nao ha roteamento condicional silencioso: "se o challenger tiver score de confianca > X, usar challenger" — essa logica seria um fallback implicito nao auditavel.
- Nao ha auto-upgrade baseado em heuristica: "se a query for muito complexa, usar challenger (Sonnet)" — esse padrao viola AP-2.
- Nao ha "teste A/B silencioso": queries nao podem ir para versoes diferentes sem que o `prompt_version` no AuditEvent reflita explicitamente a versao que respondeu.

O unico roteamento permitido e: **configuracao declarativa de fracao canary** (ex.: "10% das queries vao para v0.3") com sinal explicito no AuditEvent por query. Esse eh o mesmo principio do escalation opt-in Sonnet de ADR-0005 D2 aplicado a versoes de prompt.

### 6.1 Criterios de aceite obrigatorios para implementacao canary real (F-FUT-6, Sprint 003+)

Quando Sprint 003+ implementar o canary deployment como codigo de producao, os seguintes testes de regressao sao **criterio de aceite obrigatorio** para a cand de implementacao — nao opcional:

- **Teste CodePath canary:** assert que o roteador canary so seleciona challenger por configuracao declarativa explicita (ex.: `canary_fraction=0.10`), nunca por heuristica de confianca ou score do modelo.
- **Teste prompt_version no AuditEvent:** assert que cada query roteada para o challenger registra `prompt_version=v0.3` (ou versao equivalente) no AuditEvent. Nenhuma query challenger pode ter `prompt_version=v0.2` (versao do champion).
- **Padrao de referencia:** `test_sonnet_provider_factory_repr_does_not_leak_api_key` da cand S2-C07 — mesmo principio: assert comportamental sobre o que o CodePath NUNCA faz (fallback silencioso), nao apenas sobre o que faz.

Esses 3 testes devem ser incluidos no Gate-3 TL (§3 deste documento) como condicao de aprovacao da cand de implementacao canary. **Sem esses testes: Gate-3 nao aprova.**

**Registro formal:** F-FUT-6 (canary deployment real, Sprint 003+) deve listar esses 3 testes como criterios de aceite no pack da cand.

## 7. Comparacao com padrao de escalation Sonnet (ADR-0005 D2)

O canary deployment de versao de prompt segue o mesmo principio do escalation opt-in Sonnet:

| Aspecto | Escalation Sonnet (ADR-0005 D2) | Canary prompt (este design) |
|---|---|---|
| Como troca | Sinal explicito `escalate=sonnet` OU gate-eval OU decisao admin | Fracao canary configurada + aprovacao Direcao |
| O que registra | `model=sonnet-4-5` no AuditEvent | `prompt_version=v0.3` no AuditEvent |
| Fallback silencioso | PROIBIDO (AP-2 LLM CRITICAL) | PROIBIDO (AP-2 LLM CRITICAL) |
| Auto-upgrade | PROIBIDO | PROIBIDO |
| Rollback | `insufficient_data` → champion imediato | 100% trafego → champion imediato |

A implementacao do canary deployment (quando Sprint 003+ chegar) deve seguir o mesmo padrao da `SonnetProviderFactory` de S2-C07: sinal explicito, sem fallback silencioso, audit por chamada.

## 8. Bloqueio Fase 2 reafirmado

O canary deployment desenhado aqui e para Fase 1 (uso proprio Decio, fracao de trafego = sub-conjunto das queries do proprio Decio e funcionarios). Para Fase 2 (B2B, clientes externos), o canary envolve populacao de usuarios diferentes, requer DPA Anthropic Enterprise para qualquer versao nova de prompt que processe dados de clientes externos, e exige novo parecer LGPD (F-FUT-5/BL-013 ativo). O design aqui nao pode ser extrapolado para Fase 2 sem esse trabalho.

## 9. Cross-links

- `retraining-triggers.md` — os 4 triggers que iniciam o processo que culmina em um canary
- `drift-design.md` — as metricas usadas como criterio de rollback automatico
- `plano.md` — o eval-set que serve de gate-eval pre-promocao
- `case-study/aprendizados/2026-05_ml-engineering-qa-orchestrator-decio.md` — explicacao acessivel para Direcao
- ADR-0005 D2: padrao de escalation opt-in Sonnet como referencia de AP-2 LLM CRITICAL
