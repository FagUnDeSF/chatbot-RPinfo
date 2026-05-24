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

# Relatorio continuous 15min - $app_id

## Janela

- Inicio: `$window_start`
- Fim: `$window_end`
- Trace contract: `$trace_contract_path`
- Thresholds: `$thresholds_path`
- Audit source: `$audit_source_path`

## Metricas

| Metrica | Valor | Baseline / threshold |
|---|---:|---:|
| Chamadas na janela | `$n_calls_window` | n/a |
| Cost per call p50 | `$cost_per_call_usd_p50` | `$cost_per_call_baseline_usd` |
| Cost 30d | `$cost_usd_sum_30d` | `$budget_30d_usd` |
| Latencia p95 | `${latency_ms_total_p95}ms` | `${latency_ms_baseline_p95}ms` |
| Cache hit rate 7d | `$cache_hit_rate_pct%` | `>= 70% target / <50% critical` |
| Fallback rate 24h | `$fallback_rate_pct%` | `<= 5%` |
| Input tokens | `$input_tokens_total` | n/a |
| Output tokens | `$output_tokens_total` | n/a |

## Thresholds e anomalias

$anomalies_block

## Recomendacao

`$recommendation`

## Acao

- `manter-config`: manter a configuracao e aguardar proxima janela.
- `investigar-anomalia`: abrir investigacao AI com os trace IDs do periodo.
- `acionar-degraded-mode`: PM coordena degraded mode declarado, sem fallback silencioso.
- `escalar-direcao-budget`: Direcao decide budget, throttling ou pausa da feature.

## Evidencia

- Trace IDs/event IDs: `$trace_ids`
- Handoff emitido: `$handoff_path`
