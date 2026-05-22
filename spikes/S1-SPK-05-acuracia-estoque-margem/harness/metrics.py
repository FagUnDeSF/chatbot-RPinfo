"""Regras analiticas do spike S1-SPK-05.

Cada metrica declara fonte (query_name + source + colunas) e premissas
(regra de calculo + janela temporal + filtros + threshold) literais.
Sem premissa declarada, metrica nao entra no resultado.

Veredicto possivel por metrica:
- `validado-por-relatorio-oficial` quando a comparacao bate.
- `divergente-do-relatorio-oficial` quando bate parcialmente.
- `inconclusiva` quando relatorio oficial indisponivel OU dado de entrada
  insuficiente para a regra (ex.: CMV ausente impede calculo de margem).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from chatbot_rpinfo.domain.entities import ErpReadonlyResult, ErpRow

EstoqueFantasmaThresholdDias = int


@dataclass(frozen=True)
class MetricResult:
    """Resultado canonico por metrica."""

    metric_name: str
    fonte: dict[str, str]
    premissas: dict[str, Any]
    veredicto: str
    valor: dict[str, Any] | None
    motivo: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EstoqueFantasmaPremissas:
    regra: str
    janela_temporal: str
    filtros: list[str]
    threshold_dias_sem_venda: EstoqueFantasmaThresholdDias
    as_of_date: str
    nota_acuracia: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MargemPremissas:
    regra: str
    janela_temporal: str
    filtros: list[str]
    as_of_date: str
    motivo_inconclusiva: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_estoque_fantasma(
    sample: ErpReadonlyResult,
    threshold_dias_sem_venda: EstoqueFantasmaThresholdDias,
    as_of_date: str,
) -> MetricResult:
    """Conta SKUs com `stock > 0 AND days_without_sale >= threshold`.

    O threshold default do spike (90 dias) e hipotese tecnica - NAO regra
    oficial - e fica declarado nas premissas. Direcao podera ajustar
    quando relatorio oficial chegar.
    """
    candidatos: list[ErpRow] = [
        row
        for row in sample.rows
        if _coerce_int(row.get("stock")) > 0
        and _coerce_int(row.get("days_without_sale")) >= threshold_dias_sem_venda
    ]
    premissas = EstoqueFantasmaPremissas(
        regra="SKU classificado como fantasma se stock > 0 AND days_without_sale >= threshold",
        janela_temporal=f"snapshot unico em {as_of_date}",
        filtros=["nenhum filtro aplicado a montante; regra opera sobre a amostra inteira"],
        threshold_dias_sem_venda=threshold_dias_sem_venda,
        as_of_date=as_of_date,
        nota_acuracia=(
            "threshold de 90 dias e hipotese tecnica do spike, nao regra oficial; "
            "veredicto final de acuracia depende de comparacao com relatorio oficial"
        ),
    )
    fonte = {
        "query_name": sample.query_name,
        "source": sample.source,
        "colunas_consumidas": "sku, store_id, stock, days_without_sale",
    }
    valor = {
        "n_skus_amostrados": sample.row_count,
        "n_skus_fantasma_candidatos": len(candidatos),
        "skus_fantasma_candidatos": [str(row.get("sku")) for row in candidatos],
    }
    return MetricResult(
        metric_name="estoque_fantasma",
        fonte=fonte,
        premissas=premissas.to_dict(),
        veredicto="inconclusiva",
        valor=valor,
        motivo=(
            "harness calcula candidatos sob hipotese tecnica; veredicto final "
            "(validado/divergente) depende de comparacao com relatorio oficial"
        ),
    )


def compute_margem(
    sample: ErpReadonlyResult,
    as_of_date: str,
    relatorio_oficial_disponivel: bool,
) -> MetricResult:
    """Calcula margem ou marca inconclusiva.

    A allowlist atual do `erp_readonly` retorna apenas `gross_sales` em
    `sales_summary_sample`/`sales_summary_spike_S1_C05`; NAO retorna CMV
    (custo de mercadoria vendida) nem `net_sales`. Sem CMV, a margem nao
    e calculavel. O harness declara isso literalmente e marca a metrica
    como `inconclusiva`.
    """
    motivos: list[str] = []
    rows_sem_cmv = [row for row in sample.rows if "cmv" not in row and "cost" not in row]
    if rows_sem_cmv:
        motivos.append(
            "CMV ausente nas colunas da query allowlisted (somente gross_sales por loja/periodo); "
            "calculo de margem requer cmv ou net_sales"
        )
    if not relatorio_oficial_disponivel:
        motivos.append(
            "relatorio oficial RP Info indisponivel para conferencia; criterio literal admite "
            "entrega apenas-harness com margem inconclusiva"
        )
    premissas = MargemPremissas(
        regra="margem = (gross_sales - cmv) / gross_sales; requer cmv por loja/periodo",
        janela_temporal=f"snapshot unico em {as_of_date}",
        filtros=["nenhum filtro aplicado a montante; regra opera sobre a amostra inteira"],
        as_of_date=as_of_date,
        motivo_inconclusiva=motivos,
    )
    fonte = {
        "query_name": sample.query_name,
        "source": sample.source,
        "colunas_consumidas": "store_id, period, gross_sales",
        "colunas_ausentes_para_calculo": "cmv, net_sales",
    }
    valor = {
        "n_lojas_amostradas": sample.row_count,
        "gross_sales_total": sum(_coerce_float(row.get("gross_sales")) for row in sample.rows),
    }
    return MetricResult(
        metric_name="margem",
        fonte=fonte,
        premissas=premissas.to_dict(),
        veredicto="inconclusiva",
        valor=valor,
        motivo="; ".join(motivos),
    )


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return 0


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
