"""S2-C08 - testes canonicos por threshold + alerta sintetico end-to-end.

Cobertura conforme criterio literal sprint-002 §4.S2-C08:

- 1 teste unitario por threshold canonico (5 testes - 1 por anomaly type).
- 1 teste end-to-end de alerta sintetico via canal handoff.
- 1 teste defensive `manter-config` NAO gera handoff em disco (regra "NAO
  emitido por design" do variant linha 21).

Cross-link:
- ADR-0005 LLM provider (USD 30/mes budget; cache >= 70%; latency p95 <1500ms).
- V5 NIVEL-4 anti-fallback-silencioso (AP-2 LLM CRITICAL) - fallback-rate-alto
  recomenda `acionar-degraded-mode`, NUNCA dispara fallback adicional.
- Variant `tools/contracts/handoff/monitorar-custo-llm-alerta.yaml` (escritorio).
- thresholds.yaml versionado em `observability/llm/thresholds.yaml`.

CG-08 absoluta preservada nos testes: `AlertEmitter(emit_in_production=False)`
escreve handoffs em `handoffs/synthetic/` para nao confundir com producao.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from chatbot_rpinfo.application.services.alert_emitter import AlertEmitter
from chatbot_rpinfo.application.services.cost_monitor import (
    AnomalyType,
    CostMetricsWindow,
    CostMonitor,
    Recommendation,
    Severity,
    SuggestedDeadline,
    Urgency,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_YAML = PROJECT_ROOT / "observability" / "llm" / "thresholds.yaml"


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def monitor() -> CostMonitor:
    """CostMonitor carregado do arquivo versionado canonico."""
    return CostMonitor.from_yaml(THRESHOLDS_YAML)


def _healthy_baseline() -> CostMetricsWindow:
    """Baseline 'saudavel' - todas as metricas dentro dos thresholds.

    Usado como ponto de partida; cada teste muda 1 dimensao para isolar
    o threshold avaliado.
    """
    return CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),  # baseline real S2-C07
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("5.00"),  # bem abaixo do USD 30 budget
        latency_ms_total_p95=1922,  # baseline real S2-C07
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,  # acima do target ADR-0005 D4 (>=70%)
        fallback_rate_pct=0.5,  # bem abaixo do threshold 5%
        n_calls_total=1000,
    )


# --- Threshold 1: cost-spike ------------------------------------------------


def test_cost_spike_threshold_dispara_quando_cost_por_call_excede_20pct_baseline(
    monitor: CostMonitor,
) -> None:
    """`cost-spike`: cost per call >= 20% acima do baseline diario."""
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00130000"),  # +26% vs baseline 0.001029
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("8.00"),
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,
        fallback_rate_pct=0.5,
        n_calls_total=1000,
    )

    decision = monitor.evaluate(metrics)

    assert len(decision.anomalies) == 1
    assert decision.anomalies[0].tipo is AnomalyType.COST_SPIKE
    assert decision.anomalies[0].severity is Severity.WARNING
    assert decision.recommendation is Recommendation.INVESTIGAR_ANOMALIA
    assert decision.emit_handoff is True


# --- Threshold 2: cost-absoluto-budget-violado ------------------------------


def test_cost_absoluto_violado_dispara_quando_cost_sum_30d_excede_budget(
    monitor: CostMonitor,
) -> None:
    """`cost-absoluto-budget-violado`: cost sum 30d > USD 30 (ADR-0005 D3)."""
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("32.50"),  # acima do USD 30 budget
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,
        fallback_rate_pct=0.5,
        n_calls_total=30000,
    )

    decision = monitor.evaluate(metrics)

    assert any(
        a.tipo is AnomalyType.COST_ABSOLUTO_BUDGET_VIOLADO for a in decision.anomalies
    )
    assert decision.recommendation is Recommendation.ESCALAR_DIRECAO_BUDGET
    assert decision.urgency is Urgency.ALTA
    assert decision.suggested_deadline is SuggestedDeadline.IMEDIATO
    assert decision.impacto_financeiro_estimado_usd == Decimal("2.50000000")
    assert decision.emit_handoff is True


# --- Threshold 3: latency-p95-degradacao ------------------------------------


def test_latency_p95_degradacao_dispara_quando_p95_excede_2x_baseline(
    monitor: CostMonitor,
) -> None:
    """`latency-p95-degradacao`: p95 atual > 2x baseline."""
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("5.00"),
        latency_ms_total_p95=4500,  # > 2x baseline 1922
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,
        fallback_rate_pct=0.5,
        n_calls_total=1000,
    )

    decision = monitor.evaluate(metrics)

    assert any(
        a.tipo is AnomalyType.LATENCY_P95_DEGRADACAO for a in decision.anomalies
    )
    assert decision.recommendation is Recommendation.INVESTIGAR_ANOMALIA
    assert decision.emit_handoff is True


# --- Threshold 4: cache-hit-rate-baixo --------------------------------------


def test_cache_hit_rate_baixo_dispara_quando_inferior_a_50pct(
    monitor: CostMonitor,
) -> None:
    """`cache-hit-rate-baixo`: cache hit rate rolling 7d < 50%."""
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("5.00"),
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=42.0,  # abaixo do threshold 50%
        fallback_rate_pct=0.5,
        n_calls_total=1000,
    )

    decision = monitor.evaluate(metrics)

    cache_anoms = [a for a in decision.anomalies if a.tipo is AnomalyType.CACHE_HIT_RATE_BAIXO]
    assert len(cache_anoms) == 1
    assert cache_anoms[0].severity is Severity.CRITICAL
    assert decision.recommendation is Recommendation.INVESTIGAR_ANOMALIA
    assert decision.urgency is Urgency.MEDIA
    assert decision.suggested_deadline is SuggestedDeadline.H_24
    assert decision.emit_handoff is True


# --- Threshold 5: fallback-rate-alto (AP-2 LLM CRITICAL) -------------------


def test_fallback_rate_alto_dispara_acionar_degraded_mode_sem_swap_silencioso(
    monitor: CostMonitor,
) -> None:
    """`fallback-rate-alto`: fallback rate > 5% em 24h.

    AP-2 LLM CRITICAL especifico (V5 NIVEL-4 anti-fallback-silencioso):
    alerta NUNCA dispara fallback adicional. Apenas recomenda
    `acionar-degraded-mode` para o operador externo decidir.
    """
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("5.00"),
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,
        fallback_rate_pct=8.5,  # acima do threshold 5%
        n_calls_total=1000,
    )

    decision = monitor.evaluate(metrics)

    fallback_anoms = [
        a for a in decision.anomalies if a.tipo is AnomalyType.FALLBACK_RATE_ALTO
    ]
    assert len(fallback_anoms) == 1
    assert fallback_anoms[0].severity is Severity.CRITICAL
    assert decision.recommendation is Recommendation.ACIONAR_DEGRADED_MODE
    assert decision.urgency is Urgency.ALTA
    assert decision.suggested_deadline is SuggestedDeadline.IMEDIATO
    assert decision.emit_handoff is True
    # Auditoria: assert que a anomalia individual carrega o `recomendacao_default`
    # mapeado para `acionar-degraded-mode` (NAO escala para Sonnet/outro modelo).
    assert (
        fallback_anoms[0].recomendacao_default is Recommendation.ACIONAR_DEGRADED_MODE
    )


# --- Baseline saudavel -> manter-config NAO emite handoff ------------------


def test_baseline_saudavel_recomenda_manter_config_e_nao_emite_handoff(
    monitor: CostMonitor, tmp_path: Path
) -> None:
    """Regra variant linha 21: `manter-config` NUNCA gera handoff em disco.

    Comportamento canonico defense-in-depth: AlertEmitter.emit retorna None
    e nenhum arquivo eh escrito em disco quando recomendacao == manter-config.
    """
    metrics = _healthy_baseline()

    decision = monitor.evaluate(metrics)

    assert decision.recommendation is Recommendation.MANTER_CONFIG
    assert decision.anomalies == ()
    assert decision.emit_handoff is False

    emitter = AlertEmitter(projeto_path=tmp_path, emit_in_production=False)
    result = emitter.emit(decision, app_id="qa_orchestrator")

    assert result is None
    # Assert defense-in-depth: nada foi escrito no disco.
    synthetic_dir = tmp_path / "handoffs" / "synthetic"
    if synthetic_dir.exists():
        assert list(synthetic_dir.iterdir()) == []


# --- End-to-end alerta sintetico via canal handoff -------------------------


def test_alerta_sintetico_end_to_end_gera_handoff_no_canal_correto(
    monitor: CostMonitor, tmp_path: Path
) -> None:
    """End-to-end: metricas com 2 anomalias (cost-absoluto + cache-baixo)
    -> AlertEmitter renderiza handoff completo em disco no path canonico.

    Cobre o caminho real do `monitorar-custo-llm-alerta` UNIDIRECIONAL +
    valida que CG-08 esta ativa (handoff vai para sub-pasta `synthetic/`
    quando `emit_in_production=False`).
    """
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("31.50"),  # estoura budget
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=45.0,  # cache baixo
        fallback_rate_pct=0.5,
        n_calls_total=30000,
    )

    decision = monitor.evaluate(metrics)
    assert decision.emit_handoff is True
    # Consolidacao: cost-absoluto-budget-violado prevalece -> escalar-direcao.
    assert decision.recommendation is Recommendation.ESCALAR_DIRECAO_BUDGET
    assert len(decision.anomalies) == 2
    assert {a.tipo for a in decision.anomalies} == {
        AnomalyType.COST_ABSOLUTO_BUDGET_VIOLADO,
        AnomalyType.CACHE_HIT_RATE_BAIXO,
    }

    emitter = AlertEmitter(projeto_path=tmp_path, emit_in_production=False)
    handoff_path = emitter.emit(
        decision, app_id="qa_orchestrator", cadencia="continuous"
    )

    assert handoff_path is not None
    assert handoff_path.exists()
    # Caminho sintetico (CG-08): NAO vai para handoffs/ raiz em modo nao-producao.
    assert "handoffs/synthetic" in handoff_path.as_posix()
    assert "monitorar-custo-llm-alerta-qa_orchestrator-" in handoff_path.name

    body = handoff_path.read_text(encoding="utf-8")
    # Frontmatter canonical.
    assert "tipo: handoff" in body
    assert "origem: ai-engineer-senior" in body
    assert "destino: pm-senior+direcao" in body
    assert "unidirecional: true" in body
    assert "padrao_alerta: true" in body
    assert "trigger_origem: monitorar-custo-llm" in body
    # Vocab fechado preservado.
    assert "recommendation: escalar-direcao-budget" in body
    assert "urgency: alta" in body
    assert "suggested_deadline: imediato" in body
    # Audit format #11 nas magnitude lines.
    assert "Tipo: cost-absoluto-budget-violado, App: qa_orchestrator" in body
    assert "Tipo: cache-hit-rate-baixo, App: qa_orchestrator" in body
    # SINTETICO marker porque emit_in_production=False (defense-in-depth CG-08).
    assert "SINTETICO/TESTE - CG-08" in body


# --- Defense-in-depth: producao real precisaria de flag explicita ----------


def test_emit_in_production_true_grava_no_canal_real_e_nao_marca_sintetico(
    monitor: CostMonitor, tmp_path: Path
) -> None:
    """Quando `emit_in_production=True` (futuro pos-ADR), handoff vai para
    `handoffs/` raiz sem marker SINTETICO.

    Este teste valida que o caminho real existe e o controle de path muda
    conforme a flag. NAO ativa cron em runtime (CG-08 sigue ativa em S2-C08).
    """
    metrics = CostMetricsWindow(
        cost_per_call_usd_p50=Decimal("0.00102900"),
        cost_per_call_baseline_usd=Decimal("0.00102900"),
        cost_usd_sum_30d=Decimal("31.50"),
        latency_ms_total_p95=1922,
        latency_ms_baseline_p95=1922,
        cache_hit_rate_pct=72.0,
        fallback_rate_pct=0.5,
        n_calls_total=30000,
    )
    decision = monitor.evaluate(metrics)

    emitter = AlertEmitter(projeto_path=tmp_path, emit_in_production=True)
    handoff_path = emitter.emit(decision, app_id="qa_orchestrator")

    assert handoff_path is not None
    assert "synthetic" not in handoff_path.as_posix()
    body = handoff_path.read_text(encoding="utf-8")
    assert "SINTETICO/TESTE" not in body
    assert "emit_in_production: True" in body
