---
tipo: template-relatorio-llm
cadencia: weekly
janela: 7d
app_id: qa_orchestrator
vocab_recomendacao:
  - manter-config
  - acionar-degraded-mode
  - investigar-anomalia
  - escalar-direcao-budget
---

# Weekly trend LLM - qa_orchestrator - 2026-W22

## Escopo

- Semana: `2026-W22`
- Inicio: `2026-05-19T12:00:00+00:00`
- Fim: `2026-05-26T12:00:00+00:00`
- Fonte audit: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/runtime/audit_events.jsonl`
- Trace contract: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/qa_orchestrator_trace.yaml`
- Thresholds: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/thresholds.yaml`

## Trend operacional

| Dimensao | Valor semanal | Referencia |
|---|---:|---:|
| Chamadas | `0` | semana atual |
| Cost per call p50 | `USD 0.00102900` | baseline `USD 0.00102900` |
| Cost acumulado 30d | `USD 0` | budget `USD 30.00` |
| Latencia p95 | `1922ms` | baseline `1922ms` |
| Cache hit rate 7d | `100.00%` | target `>=70%` |
| Fallback rate 24h | `0.00%` | threshold `<=5%` |
| Input tokens | `0` | semana atual |
| Output tokens | `0` | semana atual |

## Anomalias da semana

- Nenhuma anomalia detectada nos thresholds versionados.

## Recomendacao

`manter-config`

## Leitura executiva

- Se `recommendation=manter-config`, registrar apenas tendencia e manter cadencia.
- Se `recommendation=investigar-anomalia`, revisar prompts, cache e distribuicao de intents.
- Se `recommendation=acionar-degraded-mode`, confirmar degraded mode declarado com Backend/PM.
- Se `recommendation=escalar-direcao-budget`, anexar este relatorio a aprovacao de Direcao.

## Evidencia

- Trace IDs/event IDs: `sem-eventos-na-janela`
- Handoff emitido: `-`
