# Premissas literais por metrica - spike S1-SPK-05

Reproduzido literalmente do bloco `premissas` retornado pelo harness em
`outputs/<timestamp>/result.json`. Reafirmado aqui para audit-trail
permanente do spike, independente do output de run.

## estoque_fantasma

```yaml
regra: "SKU classificado como fantasma se stock > 0 AND days_without_sale >= threshold"
janela_temporal: "snapshot unico em 2026-05-21"
filtros:
  - "nenhum filtro aplicado a montante; regra opera sobre a amostra inteira"
threshold_dias_sem_venda: 90
as_of_date: "2026-05-21"
nota_acuracia: "threshold de 90 dias e hipotese tecnica do spike, nao regra oficial; veredicto final de acuracia depende de comparacao com relatorio oficial"
fonte:
  query_name: "inventory_risk_spike_S1_C05"
  source: "erp_readonly.fixture.spike_S1_C05.inventory"
  colunas_consumidas: "sku, store_id, stock, days_without_sale"
```

Veredicto do run default (sem relatorio oficial): `inconclusiva`.

## margem

```yaml
regra: "margem = (gross_sales - cmv) / gross_sales; requer cmv por loja/periodo"
janela_temporal: "snapshot unico em 2026-05-21"
filtros:
  - "nenhum filtro aplicado a montante; regra opera sobre a amostra inteira"
as_of_date: "2026-05-21"
motivo_inconclusiva:
  - "CMV ausente nas colunas da query allowlisted (somente gross_sales por loja/periodo); calculo de margem requer cmv ou net_sales"
  - "relatorio oficial RP Info indisponivel para conferencia; criterio literal admite entrega apenas-harness com margem inconclusiva"
fonte:
  query_name: "sales_summary_spike_S1_C05"
  source: "erp_readonly.fixture.spike_S1_C05.sales"
  colunas_consumidas: "store_id, period, gross_sales"
  colunas_ausentes_para_calculo: "cmv, net_sales"
```

Veredicto do run default (sem relatorio oficial): `inconclusiva`.

## Decisao explicita sobre relatorio oficial

`relatorio_oficial: indisponivel` na aprovacao Direcao da Sprint 001
(carimbo 2026-05-20 traz apenas "aprovado", sem referencia a relatorio).
Pack-E §"Dependencias" linha 87 e sprint-doc linha 167 confirmam o
relatorio como dependencia condicional pendente. Criterio literal
(sprint-doc linha 166) admite a via `apenas-harness-margem-inconclusiva`.
