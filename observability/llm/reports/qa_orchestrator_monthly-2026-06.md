---
tipo: template-relatorio-llm
cadencia: monthly
janela: 30d
app_id: qa_orchestrator
vocab_recomendacao:
  - manter-config
  - acionar-degraded-mode
  - investigar-anomalia
  - escalar-direcao-budget
---

# Monthly deep dive LLM - qa_orchestrator - 2026-06

## Escopo

- Mes: `2026-06`
- Inicio: `2026-05-02T11:00:00+00:00`
- Fim: `2026-06-01T11:00:00+00:00`
- Budget mensal: `USD 30.00`
- Fonte audit: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/runtime/audit_events.jsonl`
- Trace contract: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/qa_orchestrator_trace.yaml`
- Thresholds: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/thresholds.yaml`

## Consumo e desempenho

| Dimensao | Valor | Leitura |
|---|---:|---|
| Chamadas no mes | `0` | volume operacional |
| Cost 30d | `USD 0` | budget hard USD 30 |
| Cost per call p50 | `USD 0.00102900` | baseline `USD 0.00102900` |
| Latencia p95 | `1922ms` | baseline `1922ms` |
| Cache hit rate 7d | `100.00%` | economia de prompt caching |
| Fallback rate 24h | `0.00%` | AP-2 LLM critical se >5% |
| Input tokens | `0` | custo de entrada |
| Output tokens | `0` | custo de saida |

## Anomalias e riscos

- Nenhuma anomalia detectada nos thresholds versionados.

## Recomendacao

`manter-config`

## Decisao de budget

- `manter-config`: manter USD 30 e revisitar no proximo ciclo mensal.
- `investigar-anomalia`: revisar cache strategy, compressao de prompt e intents dominantes.
- `acionar-degraded-mode`: confirmar que o modo degradado e declarado, rastreavel e reversivel.
- `escalar-direcao-budget`: Direcao decide aumentar budget, aplicar throttling ou pausar feature.

## Evidencia

- Trace IDs/event IDs: `sem-eventos-na-janela`
- Handoff emitido: `-`
