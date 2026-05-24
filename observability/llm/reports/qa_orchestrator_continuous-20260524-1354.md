---
tipo: template-relatorio-llm
cadencia: continuous
janela: 15min
app_id: qa_orchestrator
vocab_recomendacao:
  - manter-config
  - acionar-degraded-mode
  - investigar-anomalia
  - escalar-direcao-budget
---

# Relatorio continuous 15min - qa_orchestrator

## Janela

- Inicio: `2026-05-24T13:39:31.007388+00:00`
- Fim: `2026-05-24T13:54:31.007388+00:00`
- Trace contract: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/qa_orchestrator_trace.yaml`
- Thresholds: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/thresholds.yaml`
- Audit source: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/runtime/audit_events.jsonl`

## Metricas

| Metrica | Valor | Baseline / threshold |
|---|---:|---:|
| Chamadas na janela | `0` | n/a |
| Cost per call p50 | `USD 0.00102900` | `USD 0.00102900` |
| Cost 30d | `USD 0` | `USD 30.00` |
| Latencia p95 | `1922ms` | `1922ms` |
| Cache hit rate 7d | `100.00%` | `>= 70% target / <50% critical` |
| Fallback rate 24h | `0.00%` | `<= 5%` |
| Input tokens | `0` | n/a |
| Output tokens | `0` | n/a |

## Thresholds e anomalias

- Nenhuma anomalia detectada nos thresholds versionados.

## Recomendacao

`manter-config`

## Acao

- `manter-config`: manter a configuracao e aguardar proxima janela.
- `investigar-anomalia`: abrir investigacao AI com os trace IDs do periodo.
- `acionar-degraded-mode`: PM coordena degraded mode declarado, sem fallback silencioso.
- `escalar-direcao-budget`: Direcao decide budget, throttling ou pausa da feature.

## Evidencia

- Trace IDs/event IDs: `sem-eventos-na-janela`
- Handoff emitido: `-`
