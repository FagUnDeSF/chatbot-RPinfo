"""S2-C08 - emit handoff `monitorar-custo-llm-alerta` UNIDIRECIONAL.

Renderiza o handoff conforme variant + template canonicos do escritorio V3:

- Variant: `tools/contracts/handoff/monitorar-custo-llm-alerta.yaml` (escritorio).
- Template: `tools/templates/handoff-monitorar-custo-llm-alerta.tpl` (escritorio).

Padrao UNIDIRECIONAL (1o padrao `-alerta` no manifest handoff V3 - Onda 6
fatia 3 inv 188). Sem variant `-resposta` formal - decisao Direcao registrada
em path canonico de handoff terminal.

Regra absoluta (variant linha 21): `recomendacao == manter-config` NUNCA emite
handoff. `AlertEmitter.emit` retorna `None` neste caso. Para qualquer outra
recomendacao, retorna o `Path` do handoff escrito.

CG-08 ativa: a invocacao deste modulo em runtime de producao depende de cron
+ ADR especifico autorizar (Sprint 003+). S2-C08 entrega APENAS configuracao
+ testes; cron NAO esta wired.

AP-12 universal preservado: este modulo nao toca api_key/secrets. Recebe
metadado estrutural via `AlertDecision` (V5 NIVEL-3 §5.1) e renderiza
handoff em disco com apenas valores numericos + categorias.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from chatbot_rpinfo.application.services.cost_monitor import (
    AlertDecision,
    AnomalyDetected,
    Recommendation,
)


def _format_tipo_anomalia(anomalies: tuple[AnomalyDetected, ...]) -> str:
    return "\n".join(f"- `{anom.tipo.value}`" for anom in anomalies)


def _format_magnitude(anomalies: tuple[AnomalyDetected, ...], app_id: str) -> str:
    """Audit format #11: `Tipo: X, App: Y, Real: V, Baseline: B, Delta: D, Impact: I, Fix: F`."""
    lines: list[str] = []
    for anom in anomalies:
        lines.append(
            f"- Tipo: {anom.tipo.value}, App: {app_id}, "
            f"Real: {anom.metric_real}, Baseline: {anom.metric_baseline}, "
            f"Delta: {anom.delta_descritivo}, Impact: {anom.severity.value}, "
            f"Fix: {anom.recomendacao_default.value}"
        )
    return "\n".join(lines)


def _format_threshold_violado(anomalies: tuple[AnomalyDetected, ...]) -> str:
    lines: list[str] = []
    for anom in anomalies:
        lines.append(
            f"- {anom.tipo.value}: threshold `{anom.threshold_violado}`, "
            f"detectado `{anom.metric_real}`, status: {anom.severity.value}"
        )
    return "\n".join(lines)


def _format_impacto(decision: AlertDecision, projection_window: str) -> str:
    return (
        f"- Cenario: continuar como esta (sem acao operacional).\n"
        f"- Custo extra estimado ({projection_window}): "
        f"USD {decision.impacto_financeiro_estimado_usd}\n"
        f"- Risco adicional: qualitativo - depende do tipo de anomalia "
        f"(degradacao silenciosa OR bill surprise OR SLA breach)."
    )


class AlertEmitter:
    """Renderiza handoff `monitorar-custo-llm-alerta` em disco.

    Caminho do handoff: `<projeto_path>/handoffs/<YYYY-MM-DD>_ai-engineer-
    senior_para_pm-senior+direcao_monitorar-custo-llm-alerta-<app_id>-
    <timestamp>.md`.

    UNIDIRECIONAL: nao gera variant `-resposta`. PM absorve via status-
    processo; Direcao recebe via canal terminal.
    """

    def __init__(
        self,
        *,
        projeto_path: Path | str,
        projeto: str = "chatbot-RPinfo",
        sprint: str = "002",
        emit_in_production: bool = False,
    ) -> None:
        # `emit_in_production=False` por design (CG-08): em S2-C08 e tests, o
        # handoff e renderizado para path de teste OU descartado. Em runtime
        # de producao real (Sprint 003+ pos-ADR autorizando), Direcao passa
        # `emit_in_production=True` e o handoff vai para `handoffs/` raiz.
        self._projeto_path = Path(projeto_path)
        self._projeto = projeto
        self._sprint = sprint
        self._emit_in_production = emit_in_production

    def emit(
        self,
        decision: AlertDecision,
        *,
        app_id: str = "qa_orchestrator",
        cadencia: str = "continuous",
        projection_window: str = "30d projetados",
        timestamp: datetime | None = None,
    ) -> Path | None:
        """Renderiza handoff em disco se a recomendacao exige notificacao.

        Returns:
            Path do handoff escrito quando `decision.emit_handoff is True`.
            `None` quando `recommendation == manter-config` (regra variant
            linha 21 + design rule).
        """
        if not decision.emit_handoff:
            return None

        ts = timestamp or datetime.now(UTC)
        date_str = ts.strftime("%Y-%m-%d")
        full_ts = ts.strftime("%Y%m%dT%H%M%S")

        handoff_dir = self._projeto_path / "handoffs"
        if self._emit_in_production:
            handoff_dir.mkdir(parents=True, exist_ok=True)
        else:
            # CG-08: em dev/teste, escreve para sub-pasta `synthetic/` que
            # nao e consumida pelos consumidores de producao do PM/Direcao.
            handoff_dir = handoff_dir / "synthetic"
            handoff_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{date_str}_ai-engineer-senior_para_pm-senior+direcao_"
            f"monitorar-custo-llm-alerta-{app_id}-{full_ts}.md"
        )
        handoff_path = handoff_dir / filename

        body = self._render(
            decision=decision,
            app_id=app_id,
            cadencia=cadencia,
            projection_window=projection_window,
            timestamp=ts,
        )
        handoff_path.write_text(body, encoding="utf-8")
        return handoff_path

    def _render(
        self,
        *,
        decision: AlertDecision,
        app_id: str,
        cadencia: str,
        projection_window: str,
        timestamp: datetime,
    ) -> str:
        if self._emit_in_production:
            synthetic_marker = ""
        else:
            synthetic_marker = (
                "\n> **SINTETICO/TESTE - CG-08:** este handoff foi gerado "
                "em modo nao-producao.\n"
            )
        return (
            f"---\n"
            f"tipo: handoff\n"
            f"direcao: envio\n"
            f"origem: ai-engineer-senior\n"
            f"destino: pm-senior+direcao\n"
            f"sprint: {self._sprint}\n"
            f"trigger_origem: monitorar-custo-llm\n"
            f"data: {timestamp.strftime('%Y-%m-%d')}\n"
            f"projeto: {self._projeto}\n"
            f"status: emitido\n"
            f"unidirecional: true\n"
            f"padrao_alerta: true\n"
            f"cadencia: {cadencia}\n"
            f"app_id: {app_id}\n"
            f"recommendation: {decision.recommendation.value}\n"
            f"urgency: {decision.urgency.value}\n"
            f"suggested_deadline: {decision.suggested_deadline.value}\n"
            f"emit_in_production: {self._emit_in_production}\n"
            f"---\n"
            f"\n"
            f"# Handoff AI-Engineer-Senior -> PM-Senior + Direcao - "
            f"Alerta custo LLM (monitorar-custo-llm-alerta) [UNIDIRECIONAL]\n"
            f"{synthetic_marker}\n"
            f"> **1o padrao `-alerta` UNIDIRECIONAL no manifest handoff V3** "
            f"(Onda 6 fatia 3). PM absorve via status-processo para tracking; "
            f"Direcao recebe via canal terminal e decide acao via canal "
            f"Direcao. Sem variant -resposta formal.\n"
            f"\n"
            f"## Tipo(s) de anomalia detectada\n"
            f"\n"
            f"{_format_tipo_anomalia(decision.anomalies)}\n"
            f"\n"
            f"## Magnitude vs baseline (Audit format)\n"
            f"\n"
            f"{_format_magnitude(decision.anomalies, app_id)}\n"
            f"\n"
            f"## Threshold violado\n"
            f"\n"
            f"{_format_threshold_violado(decision.anomalies)}\n"
            f"\n"
            f"## Recomendacao\n"
            f"\n"
            f"{decision.recommendation.value}\n"
            f"\n"
            f"## Urgencia\n"
            f"\n"
            f"{decision.urgency.value}\n"
            f"\n"
            f"## Prazo sugerido\n"
            f"\n"
            f"{decision.suggested_deadline.value}\n"
            f"\n"
            f"## Impacto financeiro estimado\n"
            f"\n"
            f"{_format_impacto(decision, projection_window)}\n"
            f"\n"
            f"## Acao esperada PM\n"
            f"\n"
            f"- `recomendacao=acionar-degraded-mode` -> PM coordena com "
            f"backend-senior para ativar degraded mode (rate limit + cache "
            f"aggressive + model fallback declarado em §10 Fallback Matrix).\n"
            f"- `recomendacao=investigar-anomalia` -> PM coordena "
            f"investigacao com AI; gravar findings em §5 OUT-005.\n"
            f"- `recomendacao=escalar-direcao-budget` -> PM informa Direcao "
            f"via status-processo; aguarda decisao Direcao.\n"
            f"\n"
            f"## Acao esperada Direcao\n"
            f"\n"
            f"- Receber alerta via canal terminal de handoff.\n"
            f"- Decidir acao via aprovacao formal em "
            f"`equipe/00-direcao/aprovacoes/`:\n"
            f"  - `throttling-configurado` (rate limit por user reduzido + "
            f"cache TTL aumentado).\n"
            f"  - `budget-aumentado` (revisar §1.8 contexto-projeto + "
            f"autorizar cost cap maior).\n"
            f"  - `pause-feature` (desabilitar feature do produto que esta "
            f"gerando spike OR app inteiro).\n"
            f"\n"
            f"## Nota: UNIDIRECIONAL - sem variant -resposta\n"
            f"\n"
            f"Decisao Direcao 2026-05-21: padrao -alerta UNIDIRECIONAL "
            f"(mirror monitorar-drift-alerta do ml-engineer). Espera-se "
            f"decisao Direcao via canal proprio, nao via handoff formal. "
            f"Reduz ceremony para alertas informacionais.\n"
        )


__all__ = ["AlertEmitter", "Recommendation"]
