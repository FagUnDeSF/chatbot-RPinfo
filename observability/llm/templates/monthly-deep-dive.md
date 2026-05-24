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

# Monthly deep dive LLM - $app_id - $period_label

## Escopo

- Mes: `$period_label`
- Inicio: `$window_start`
- Fim: `$window_end`
- Budget mensal: `$budget_30d_usd`
- Fonte audit: `$audit_source_path`
- Trace contract: `$trace_contract_path`
- Thresholds: `$thresholds_path`

## Consumo e desempenho

| Dimensao | Valor | Leitura |
|---|---:|---|
| Chamadas no mes | `$n_calls_window` | volume operacional |
| Cost 30d | `$cost_usd_sum_30d` | budget hard USD 30 |
| Cost per call p50 | `$cost_per_call_usd_p50` | baseline `$cost_per_call_baseline_usd` |
| Latencia p95 | `${latency_ms_total_p95}ms` | baseline `${latency_ms_baseline_p95}ms` |
| Cache hit rate 7d | `$cache_hit_rate_pct%` | economia de prompt caching |
| Fallback rate 24h | `$fallback_rate_pct%` | AP-2 LLM critical se >5% |
| Input tokens | `$input_tokens_total` | custo de entrada |
| Output tokens | `$output_tokens_total` | custo de saida |

## Anomalias e riscos

$anomalies_block

## Recomendacao

`$recommendation`

## Decisao de budget

- `manter-config`: manter USD 30 e revisitar no proximo ciclo mensal.
- `investigar-anomalia`: revisar cache strategy, compressao de prompt e intents dominantes.
- `acionar-degraded-mode`: confirmar que o modo degradado e declarado, rastreavel e reversivel.
- `escalar-direcao-budget`: Direcao decide aumentar budget, aplicar throttling ou pausar feature.

## Evidencia

- Trace IDs/event IDs: `$trace_ids`
- Handoff emitido: `$handoff_path`
