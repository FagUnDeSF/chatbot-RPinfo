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

# Weekly trend LLM - $app_id - $period_label

## Escopo

- Semana: `$period_label`
- Inicio: `$window_start`
- Fim: `$window_end`
- Fonte audit: `$audit_source_path`
- Trace contract: `$trace_contract_path`
- Thresholds: `$thresholds_path`

## Trend operacional

| Dimensao | Valor semanal | Referencia |
|---|---:|---:|
| Chamadas | `$n_calls_window` | semana atual |
| Cost per call p50 | `$cost_per_call_usd_p50` | baseline `$cost_per_call_baseline_usd` |
| Cost acumulado 30d | `$cost_usd_sum_30d` | budget `$budget_30d_usd` |
| Latencia p95 | `${latency_ms_total_p95}ms` | baseline `${latency_ms_baseline_p95}ms` |
| Cache hit rate 7d | `$cache_hit_rate_pct%` | target `>=70%` |
| Fallback rate 24h | `$fallback_rate_pct%` | threshold `<=5%` |
| Input tokens | `$input_tokens_total` | semana atual |
| Output tokens | `$output_tokens_total` | semana atual |

## Anomalias da semana

$anomalies_block

## Recomendacao

`$recommendation`

## Leitura executiva

- Se `recommendation=manter-config`, registrar apenas tendencia e manter cadencia.
- Se `recommendation=investigar-anomalia`, revisar prompts, cache e distribuicao de intents.
- Se `recommendation=acionar-degraded-mode`, confirmar degraded mode declarado com Backend/PM.
- Se `recommendation=escalar-direcao-budget`, anexar este relatorio a aprovacao de Direcao.

## Evidencia

- Trace IDs/event IDs: `$trace_ids`
- Handoff emitido: `$handoff_path`
