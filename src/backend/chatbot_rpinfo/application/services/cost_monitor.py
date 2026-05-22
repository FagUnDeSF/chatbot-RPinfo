"""S2-C08 observabilidade LLM - cost monitor + threshold evaluation.

Engine canonica que consome metricas agregadas em janela (cost/latency/cache/
fallback) + thresholds versionados em `observability/llm/thresholds.yaml` e
produz uma decisao de alerta seguindo o vocab fechado canonico:

  - 5 tipos de anomalia: `cost-spike` / `cost-absoluto-budget-violado` /
    `latency-p95-degradacao` / `cache-hit-rate-baixo` / `fallback-rate-alto`.
  - 4 recomendacoes: `manter-config` / `acionar-degraded-mode` /
    `investigar-anomalia` / `escalar-direcao-budget`.

Cross-link:
  - ADR-0005 LLM provider (Haiku 4.5 + Sonnet 4.5 opt-in + USD 30/mes).
  - Metodo `ai-engineer-senior > monitorar-custo-llm` (escritorio V3).
  - V5 NIVEL-4 anti-fallback-silencioso (AP-2 LLM CRITICAL) - `fallback-rate-
    alto` NUNCA dispara fallback adicional; apenas recomenda
    `acionar-degraded-mode` ao operador.
  - AP-12 universal preservado - thresholds.yaml versionado NAO contem
    api_key/secrets; apenas configuracao numerica.

CG-08 absoluta: este modulo nao liga alertas em producao real. Apenas avalia
metricas e retorna `AlertDecision`. Emissao de handoff fica em `alert_emitter`
e sua invocacao em runtime de producao depende de cron + ADR especifico
(Sprint 003+).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class AnomalyType(StrEnum):
    COST_SPIKE = "cost-spike"
    COST_ABSOLUTO_BUDGET_VIOLADO = "cost-absoluto-budget-violado"
    LATENCY_P95_DEGRADACAO = "latency-p95-degradacao"
    CACHE_HIT_RATE_BAIXO = "cache-hit-rate-baixo"
    FALLBACK_RATE_ALTO = "fallback-rate-alto"


class Recommendation(StrEnum):
    MANTER_CONFIG = "manter-config"
    ACIONAR_DEGRADED_MODE = "acionar-degraded-mode"
    INVESTIGAR_ANOMALIA = "investigar-anomalia"
    ESCALAR_DIRECAO_BUDGET = "escalar-direcao-budget"


class Severity(StrEnum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Urgency(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class SuggestedDeadline(StrEnum):
    IMEDIATO = "imediato"
    H_24 = "24h"
    SEMANA_1 = "1-semana"


@dataclass(frozen=True, slots=True)
class CostMetricsWindow:
    """Metricas agregadas em janela de avaliacao (continuous/weekly/monthly).

    Fonte canonica: agregacao de `AuditEvent` fields (V5 NIVEL-3 §5.1). Em
    runtime de producao, agregadas via Langfuse/LangSmith/in-process repo.
    Em testes unitarios, injetadas diretamente como fixtures.
    """

    cost_per_call_usd_p50: Decimal
    cost_per_call_baseline_usd: Decimal
    cost_usd_sum_30d: Decimal
    latency_ms_total_p95: int
    latency_ms_baseline_p95: int
    cache_hit_rate_pct: float
    fallback_rate_pct: float
    n_calls_total: int


@dataclass(frozen=True, slots=True)
class AnomalyDetected:
    """Uma anomalia individual detectada por um threshold violado.

    Cada threshold violado gera 1 `AnomalyDetected`. O `CostMonitor` consolida
    multiplas anomalias em um unico `AlertDecision` (a recomendacao final
    sobe pela severity mais critica).
    """

    tipo: AnomalyType
    severity: Severity
    metric_real: str   # valor literal com unidade (ex: "$0.0123/call" ou "1850ms")
    metric_baseline: str
    delta_descritivo: str  # ex: "+24.5%" ou "2.1x baseline"
    threshold_violado: str  # ex: ">= 20% above baseline"
    recomendacao_default: Recommendation


@dataclass(frozen=True, slots=True)
class AlertDecision:
    """Decisao final do CostMonitor para uma janela de avaliacao.

    Quando `recommendation == MANTER_CONFIG`, NAO ha anomalias detectadas e
    `alert_emitter` NAO emite handoff (regra "manter-config NAO emite por
    design" - variant `monitorar-custo-llm-alerta.yaml` linha 21).
    """

    recommendation: Recommendation
    anomalies: tuple[AnomalyDetected, ...]
    urgency: Urgency
    suggested_deadline: SuggestedDeadline
    impacto_financeiro_estimado_usd: Decimal

    @property
    def emit_handoff(self) -> bool:
        """True quando handoff `monitorar-custo-llm-alerta` deve ser emitido.

        Regra: `manter-config` NAO emite por design. Qualquer outra
        recomendacao emite handoff UNIDIRECIONAL para PM + Direcao.
        """
        return self.recommendation is not Recommendation.MANTER_CONFIG


@dataclass(slots=True)
class _ThresholdSpec:
    """Especificacao interna de um threshold lido de thresholds.yaml."""

    metric_path: str
    severity_when_violated: Severity
    recommendation_default: Recommendation
    descricao: str
    raw_config: dict[str, Any] = field(default_factory=dict)


class CostMonitor:
    """Engine que avalia metricas vs thresholds e produz AlertDecision.

    Construir via `CostMonitor.from_yaml(path)` para carregar configuracao
    versionada. Em testes unitarios, instanciar via construtor direto com
    `app_settings_budget_usd` + `baseline_ms` injetados.

    AP-2 LLM CRITICAL inegociavel: ao detectar `fallback-rate-alto`, este
    monitor APENAS recomenda `acionar-degraded-mode` ao operador externo.
    Em nenhum caminho deste monitor o fallback eh ativado automaticamente -
    a decisao fica com o operador/Direcao via canal terminal de handoff.
    """

    def __init__(
        self,
        *,
        budget_mensal_usd: Decimal,
        cost_spike_pct_above_baseline: float,
        cost_spike_z_score_minimo: float,
        latency_p95_baseline_ms: int,
        latency_p95_multiplo_para_alerta: float,
        cache_hit_rate_threshold_pct: float,
        fallback_rate_threshold_pct: float,
    ) -> None:
        self._budget_mensal_usd = budget_mensal_usd
        self._cost_spike_pct = cost_spike_pct_above_baseline
        self._cost_spike_z = cost_spike_z_score_minimo
        self._latency_baseline_ms = latency_p95_baseline_ms
        self._latency_multiplo = latency_p95_multiplo_para_alerta
        self._cache_threshold_pct = cache_hit_rate_threshold_pct
        self._fallback_threshold_pct = fallback_rate_threshold_pct

    @classmethod
    def from_yaml(cls, thresholds_path: Path | str) -> CostMonitor:
        """Carrega configuracao a partir de `observability/llm/thresholds.yaml`.

        Le APENAS o arquivo de configuracao. AP-12 universal preservado - o
        arquivo NAO contem api_key/secrets; apenas configuracao numerica.
        """
        path = Path(thresholds_path)
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        thresholds: dict[str, dict[str, Any]] = raw["thresholds"]

        cost_spike = thresholds["cost-spike"]
        cost_abs = thresholds["cost-absoluto-budget-violado"]
        latency = thresholds["latency-p95-degradacao"]
        cache = thresholds["cache-hit-rate-baixo"]
        fallback = thresholds["fallback-rate-alto"]

        return cls(
            budget_mensal_usd=Decimal(str(cost_abs["valor_usd"])),
            cost_spike_pct_above_baseline=float(cost_spike["valor_pct_above_baseline"]),
            cost_spike_z_score_minimo=float(cost_spike["z_score_minimo"]),
            latency_p95_baseline_ms=int(latency["baseline_ms_referencia"]),
            latency_p95_multiplo_para_alerta=float(latency["valor_multiplo_baseline"]),
            cache_hit_rate_threshold_pct=float(cache["valor_pct"]),
            fallback_rate_threshold_pct=float(fallback["valor_pct"]),
        )

    def evaluate(self, metrics: CostMetricsWindow) -> AlertDecision:
        """Avalia metricas vs 5 thresholds e retorna AlertDecision consolidada.

        Algoritmo:
          1. Para cada threshold, verifica se violado -> AnomalyDetected.
          2. Se nenhuma anomalia -> MANTER_CONFIG (NAO emite handoff).
          3. Se >= 1 anomalia, sobe recomendacao pela mais critica:
             - CRITICAL fallback-rate-alto OR cost-absoluto -> `acionar-degraded-mode`
               OR `escalar-direcao-budget` respectivamente.
             - CRITICAL cache-hit-rate -> `investigar-anomalia`.
             - WARNING (qualquer) -> `investigar-anomalia`.
          4. Mapeia urgency + deadline conforme tabela em thresholds.yaml.
        """
        anomalies: list[AnomalyDetected] = []

        if self._is_cost_spike(metrics):
            anomalies.append(self._build_cost_spike(metrics))
        if self._is_cost_absoluto_violado(metrics):
            anomalies.append(self._build_cost_absoluto(metrics))
        if self._is_latency_degradacao(metrics):
            anomalies.append(self._build_latency_degradacao(metrics))
        if self._is_cache_hit_baixo(metrics):
            anomalies.append(self._build_cache_baixo(metrics))
        if self._is_fallback_rate_alto(metrics):
            anomalies.append(self._build_fallback_alto(metrics))

        if not anomalies:
            return AlertDecision(
                recommendation=Recommendation.MANTER_CONFIG,
                anomalies=(),
                urgency=Urgency.BAIXA,
                suggested_deadline=SuggestedDeadline.SEMANA_1,
                impacto_financeiro_estimado_usd=Decimal("0"),
            )

        recommendation = self._consolidate_recommendation(anomalies)
        urgency, deadline = self._derive_urgency(anomalies, recommendation)
        impacto = self._estimate_impacto_financeiro(metrics, anomalies)

        return AlertDecision(
            recommendation=recommendation,
            anomalies=tuple(anomalies),
            urgency=urgency,
            suggested_deadline=deadline,
            impacto_financeiro_estimado_usd=impacto,
        )

    # --- Threshold checks ---------------------------------------------------

    def _is_cost_spike(self, metrics: CostMetricsWindow) -> bool:
        if metrics.cost_per_call_baseline_usd == 0:
            return False
        delta_pct = float(
            (metrics.cost_per_call_usd_p50 - metrics.cost_per_call_baseline_usd)
            / metrics.cost_per_call_baseline_usd
        ) * 100.0
        return delta_pct >= self._cost_spike_pct

    def _is_cost_absoluto_violado(self, metrics: CostMetricsWindow) -> bool:
        return metrics.cost_usd_sum_30d > self._budget_mensal_usd

    def _is_latency_degradacao(self, metrics: CostMetricsWindow) -> bool:
        if metrics.latency_ms_baseline_p95 <= 0:
            return False
        return (
            metrics.latency_ms_total_p95
            > metrics.latency_ms_baseline_p95 * self._latency_multiplo
        )

    def _is_cache_hit_baixo(self, metrics: CostMetricsWindow) -> bool:
        return metrics.cache_hit_rate_pct < self._cache_threshold_pct

    def _is_fallback_rate_alto(self, metrics: CostMetricsWindow) -> bool:
        return metrics.fallback_rate_pct > self._fallback_threshold_pct

    # --- AnomalyDetected builders -------------------------------------------

    def _build_cost_spike(self, metrics: CostMetricsWindow) -> AnomalyDetected:
        delta_pct = float(
            (metrics.cost_per_call_usd_p50 - metrics.cost_per_call_baseline_usd)
            / metrics.cost_per_call_baseline_usd
        ) * 100.0
        return AnomalyDetected(
            tipo=AnomalyType.COST_SPIKE,
            severity=Severity.WARNING,
            metric_real=f"${metrics.cost_per_call_usd_p50}/call",
            metric_baseline=f"${metrics.cost_per_call_baseline_usd}/call",
            delta_descritivo=f"{delta_pct:+.1f}%",
            threshold_violado=f">= {self._cost_spike_pct}% above baseline",
            recomendacao_default=Recommendation.INVESTIGAR_ANOMALIA,
        )

    def _build_cost_absoluto(self, metrics: CostMetricsWindow) -> AnomalyDetected:
        excesso = metrics.cost_usd_sum_30d - self._budget_mensal_usd
        return AnomalyDetected(
            tipo=AnomalyType.COST_ABSOLUTO_BUDGET_VIOLADO,
            severity=Severity.CRITICAL,
            metric_real=f"${metrics.cost_usd_sum_30d} (30d sum)",
            metric_baseline=f"${self._budget_mensal_usd} (budget USD 30/mes)",
            delta_descritivo=f"+${excesso} excesso",
            threshold_violado=f"> ${self._budget_mensal_usd}",
            recomendacao_default=Recommendation.ESCALAR_DIRECAO_BUDGET,
        )

    def _build_latency_degradacao(self, metrics: CostMetricsWindow) -> AnomalyDetected:
        multiplo = metrics.latency_ms_total_p95 / max(metrics.latency_ms_baseline_p95, 1)
        return AnomalyDetected(
            tipo=AnomalyType.LATENCY_P95_DEGRADACAO,
            severity=Severity.WARNING,
            metric_real=f"{metrics.latency_ms_total_p95}ms (p95)",
            metric_baseline=f"{metrics.latency_ms_baseline_p95}ms (p95 baseline)",
            delta_descritivo=f"{multiplo:.2f}x baseline",
            threshold_violado=f"> {self._latency_multiplo}x baseline",
            recomendacao_default=Recommendation.INVESTIGAR_ANOMALIA,
        )

    def _build_cache_baixo(self, metrics: CostMetricsWindow) -> AnomalyDetected:
        return AnomalyDetected(
            tipo=AnomalyType.CACHE_HIT_RATE_BAIXO,
            severity=Severity.CRITICAL,
            metric_real=f"{metrics.cache_hit_rate_pct:.1f}% (rolling 7d)",
            metric_baseline=">= 70% target (ADR-0005 D4)",
            delta_descritivo=f"{metrics.cache_hit_rate_pct - 70.0:+.1f}pp vs target",
            threshold_violado=f"< {self._cache_threshold_pct}%",
            recomendacao_default=Recommendation.INVESTIGAR_ANOMALIA,
        )

    def _build_fallback_alto(self, metrics: CostMetricsWindow) -> AnomalyDetected:
        # AP-2 LLM CRITICAL especifico (V5 NIVEL-4): alerta sobre alta taxa
        # NUNCA dispara fallback adicional; apenas notifica operador para
        # acionar degraded mode controlado.
        return AnomalyDetected(
            tipo=AnomalyType.FALLBACK_RATE_ALTO,
            severity=Severity.CRITICAL,
            metric_real=f"{metrics.fallback_rate_pct:.1f}% (rolling 24h)",
            metric_baseline=f"<= {self._fallback_threshold_pct}% (target)",
            delta_descritivo=(
                f"{metrics.fallback_rate_pct - self._fallback_threshold_pct:+.1f}pp "
                "acima do threshold"
            ),
            threshold_violado=f"> {self._fallback_threshold_pct}%",
            recomendacao_default=Recommendation.ACIONAR_DEGRADED_MODE,
        )

    # --- Consolidation ------------------------------------------------------

    @staticmethod
    def _consolidate_recommendation(
        anomalies: list[AnomalyDetected],
    ) -> Recommendation:
        """Consolida multiplas anomalias em 1 recomendacao final.

        Prioridade (alta -> baixa):
          1. `escalar-direcao-budget` (cost-absoluto-budget-violado).
          2. `acionar-degraded-mode` (fallback-rate-alto CRITICAL).
          3. `investigar-anomalia` (qualquer outra anomalia).
        """
        for anom in anomalies:
            if anom.tipo is AnomalyType.COST_ABSOLUTO_BUDGET_VIOLADO:
                return Recommendation.ESCALAR_DIRECAO_BUDGET
        for anom in anomalies:
            if anom.tipo is AnomalyType.FALLBACK_RATE_ALTO:
                return Recommendation.ACIONAR_DEGRADED_MODE
        return Recommendation.INVESTIGAR_ANOMALIA

    @staticmethod
    def _derive_urgency(
        anomalies: list[AnomalyDetected],
        recommendation: Recommendation,
    ) -> tuple[Urgency, SuggestedDeadline]:
        if recommendation is Recommendation.ESCALAR_DIRECAO_BUDGET:
            return Urgency.ALTA, SuggestedDeadline.IMEDIATO
        if recommendation is Recommendation.ACIONAR_DEGRADED_MODE:
            return Urgency.ALTA, SuggestedDeadline.IMEDIATO
        # investigar-anomalia: CRITICAL -> media/24h; WARNING -> baixa/1-semana.
        any_critical = any(a.severity is Severity.CRITICAL for a in anomalies)
        if any_critical:
            return Urgency.MEDIA, SuggestedDeadline.H_24
        return Urgency.BAIXA, SuggestedDeadline.SEMANA_1

    def _estimate_impacto_financeiro(
        self,
        metrics: CostMetricsWindow,
        anomalies: list[AnomalyDetected],
    ) -> Decimal:
        """Estimativa conservadora de impacto se nada for feito (30d projecao).

        Calculo simples:
          - cost-absoluto violado: excesso ja medido.
          - cost-spike: extrapolacao do delta mensal vs baseline.
          - outros: 0 (impacto qualitativo, nao financeiro direto).
        """
        impacto = Decimal("0")
        for anom in anomalies:
            if anom.tipo is AnomalyType.COST_ABSOLUTO_BUDGET_VIOLADO:
                impacto += metrics.cost_usd_sum_30d - self._budget_mensal_usd
            elif anom.tipo is AnomalyType.COST_SPIKE:
                # Projecao mensal do delta (cost_per_call * n_calls_estimados/mes).
                # Conservador: usa n_calls_total como proxy para 30d.
                delta_por_call = (
                    metrics.cost_per_call_usd_p50 - metrics.cost_per_call_baseline_usd
                )
                impacto += delta_por_call * Decimal(str(metrics.n_calls_total))
        return impacto.quantize(Decimal("0.00000001"))


__all__ = [
    "AlertDecision",
    "AnomalyDetected",
    "AnomalyType",
    "CostMetricsWindow",
    "CostMonitor",
    "Recommendation",
    "Severity",
    "SuggestedDeadline",
    "Urgency",
]
