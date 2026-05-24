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

# Relatorio continuous 15min - qa_orchestrator_sintetico

## Janela

- Inicio: `2026-05-24T13:35:00+00:00`
- Fim: `2026-05-24T13:50:00+00:00`
- Trace contract: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/qa_orchestrator_trace.yaml`
- Thresholds: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/thresholds.yaml`
- Audit source: `C:/ProjetoRP/chatbot-RPinfo/observability/llm/runtime/audit_events.jsonl`

## Metricas

| Metrica | Valor | Baseline / threshold |
|---|---:|---:|
| Chamadas na janela | `1` | n/a |
| Cost per call p50 | `USD 0.00250000` | `USD 0.00102900` |
| Cost 30d | `USD 0.00250000` | `USD 30.00` |
| Latencia p95 | `4100ms` | `1922ms` |
| Cache hit rate 7d | `0.00%` | `>= 70% target / <50% critical` |
| Fallback rate 24h | `0.00%` | `<= 5%` |
| Input tokens | `800` | n/a |
| Output tokens | `220` | n/a |

## Thresholds e anomalias

- Tipo: cost-spike; Real: $0.00250000/call; Baseline: $0.00102900/call; Delta: +143.0%; Threshold: >= 20.0% above baseline; Recomendacao default: investigar-anomalia
- Tipo: latency-p95-degradacao; Real: 4100ms (p95); Baseline: 1922ms (p95 baseline); Delta: 2.13x baseline; Threshold: > 2.0x baseline; Recomendacao default: investigar-anomalia
- Tipo: cache-hit-rate-baixo; Real: 0.0% (rolling 7d); Baseline: >= 70% target (ADR-0005 D4); Delta: -70.0pp vs target; Threshold: < 50.0%; Recomendacao default: investigar-anomalia

## Recomendacao

`investigar-anomalia`

## Acao

- `manter-config`: manter a configuracao e aguardar proxima janela.
- `investigar-anomalia`: abrir investigacao AI com os trace IDs do periodo.
- `acionar-degraded-mode`: PM coordena degraded mode declarado, sem fallback silencioso.
- `escalar-direcao-budget`: Direcao decide budget, throttling ou pausa da feature.

## Evidencia

- Trace IDs/event IDs: `s3-c04-synthetic-20260524T134900Z`
- Handoff emitido: `C:/ProjetoRP/chatbot-RPinfo/handoffs/2026-05-24_ai-engineer-senior_para_pm-senior+direcao_monitorar-custo-llm-alerta-qa_orchestrator_sintetico-20260524T135000.md`
