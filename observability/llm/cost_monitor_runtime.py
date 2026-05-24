"""Runtime externo para `monitorar-custo-llm`.

Este arquivo fica fora de `src/**` por contrato da S3-C04. Ele agrega eventos
de audit exportados em JSONL, chama `CostMonitor.from_yaml(...).evaluate(...)`
e renderiza o relatorio da cadencia. Handoff real so e emitido quando a
decisao final for diferente de `manter-config`.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from string import Template
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_BACKEND = PROJECT_ROOT / "src" / "backend"
if str(SRC_BACKEND) not in sys.path:
    sys.path.insert(0, str(SRC_BACKEND))

from chatbot_rpinfo.application.services.alert_emitter import AlertEmitter  # noqa: E402
from chatbot_rpinfo.application.services.cost_monitor import (
    AlertDecision,
    CostMetricsWindow,
    CostMonitor,
    Recommendation,
)  # noqa: E402

APP_ID = "qa_orchestrator"
DEFAULT_COST_BASELINE_USD = Decimal("0.00102900")
DEFAULT_LATENCY_BASELINE_MS = 1922
BUDGET_30D_USD = Decimal("30.00")


@dataclass(frozen=True, slots=True)
class AuditMetricEvent:
    event_id: str
    occurred_at: datetime
    cost_usd: Decimal
    latency_ms_total: int
    cache_hit: bool
    fallback_active: bool
    input_tokens_total: int
    output_tokens_total: int


@dataclass(frozen=True, slots=True)
class WindowSlices:
    primary: tuple[AuditMetricEvent, ...]
    last_24h: tuple[AuditMetricEvent, ...]
    last_7d: tuple[AuditMetricEvent, ...]
    last_30d: tuple[AuditMetricEvent, ...]


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("occurred_at ausente ou nao-string")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _as_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    raise TypeError(f"valor inteiro invalido: {value!r}")


def _as_bool(value: object) -> bool:
    return bool(value)


def load_events(audit_jsonl: Path, *, app_id: str) -> tuple[AuditMetricEvent, ...]:
    if not audit_jsonl.exists():
        raise FileNotFoundError(
            f"audit_jsonl inexistente: {audit_jsonl}. "
            "Configure OBS_LLM_AUDIT_JSONL ou passe --audit-jsonl."
        )

    events: list[AuditMetricEvent] = []
    with audit_jsonl.open(encoding="utf-8-sig") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            raw: dict[str, Any] = json.loads(stripped)
            source = str(raw.get("source", ""))
            intent = str(raw.get("intent", ""))
            if app_id not in {source, intent} and f"{app_id}:" not in intent:
                continue
            events.append(
                AuditMetricEvent(
                    event_id=str(raw.get("event_id", f"line-{line_no}")),
                    occurred_at=_parse_timestamp(raw.get("occurred_at")),
                    cost_usd=_as_decimal(raw.get("cost_usd")),
                    latency_ms_total=_as_int(raw.get("latency_ms_total")),
                    cache_hit=_as_bool(raw.get("cache_hit")),
                    fallback_active=_as_bool(raw.get("fallback_active")),
                    input_tokens_total=_as_int(raw.get("input_tokens_total")),
                    output_tokens_total=_as_int(raw.get("output_tokens_total")),
                )
            )
    return tuple(sorted(events, key=lambda event: event.occurred_at))


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def _median_decimal(values: list[Decimal], *, default: Decimal) -> Decimal:
    if not values:
        return default
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2")


def _slice(
    events: tuple[AuditMetricEvent, ...],
    *,
    end: datetime,
    delta: timedelta,
) -> tuple[AuditMetricEvent, ...]:
    start = end - delta
    return tuple(event for event in events if start <= event.occurred_at <= end)


def build_slices(
    events: tuple[AuditMetricEvent, ...],
    *,
    cadencia: str,
    end: datetime,
) -> WindowSlices:
    primary_delta = {
        "continuous": timedelta(minutes=15),
        "weekly": timedelta(days=7),
        "monthly": timedelta(days=30),
    }[cadencia]
    return WindowSlices(
        primary=_slice(events, end=end, delta=primary_delta),
        last_24h=_slice(events, end=end, delta=timedelta(hours=24)),
        last_7d=_slice(events, end=end, delta=timedelta(days=7)),
        last_30d=_slice(events, end=end, delta=timedelta(days=30)),
    )


def build_metrics(
    slices: WindowSlices,
    *,
    cost_baseline_usd: Decimal,
    latency_baseline_ms: int,
) -> CostMetricsWindow:
    cache_denominator = len(slices.last_7d)
    fallback_denominator = len(slices.last_24h)
    cache_hit_rate = (
        100.0 * sum(1 for event in slices.last_7d if event.cache_hit) / cache_denominator
        if cache_denominator
        else 100.0
    )
    fallback_rate = (
        100.0 * sum(1 for event in slices.last_24h if event.fallback_active) / fallback_denominator
        if fallback_denominator
        else 0.0
    )

    return CostMetricsWindow(
        cost_per_call_usd_p50=_median_decimal(
            [event.cost_usd for event in slices.primary],
            default=cost_baseline_usd,
        ),
        cost_per_call_baseline_usd=cost_baseline_usd,
        cost_usd_sum_30d=sum(
            (event.cost_usd for event in slices.last_30d),
            Decimal("0"),
        ),
        latency_ms_total_p95=_percentile(
            [event.latency_ms_total for event in slices.primary],
            0.95,
        )
        or latency_baseline_ms,
        latency_ms_baseline_p95=latency_baseline_ms,
        cache_hit_rate_pct=cache_hit_rate,
        fallback_rate_pct=fallback_rate,
        n_calls_total=len(slices.last_30d),
    )


def _anomalies_block(decision: AlertDecision) -> str:
    if not decision.anomalies:
        return "- Nenhuma anomalia detectada nos thresholds versionados."
    lines = []
    for anomaly in decision.anomalies:
        lines.append(
            f"- Tipo: {anomaly.tipo.value}; Real: {anomaly.metric_real}; "
            f"Baseline: {anomaly.metric_baseline}; Delta: {anomaly.delta_descritivo}; "
            f"Threshold: {anomaly.threshold_violado}; "
            f"Recomendacao default: {anomaly.recomendacao_default.value}"
        )
    return "\n".join(lines)


def _period_label(cadencia: str, end: datetime) -> str:
    if cadencia == "weekly":
        year, week, _ = end.isocalendar()
        return f"{year}-W{week:02d}"
    if cadencia == "monthly":
        return end.strftime("%Y-%m")
    return end.strftime("%Y%m%d-%H%M")


def _template_path(cadencia: str) -> Path:
    return PROJECT_ROOT / "observability" / "llm" / "templates" / {
        "continuous": "continuous-15min.md",
        "weekly": "weekly-trend.md",
        "monthly": "monthly-deep-dive.md",
    }[cadencia]


def render_report(
    *,
    cadencia: str,
    end: datetime,
    slices: WindowSlices,
    metrics: CostMetricsWindow,
    decision: AlertDecision,
    audit_source_path: Path,
    thresholds_path: Path,
    trace_contract_path: Path,
    handoff_path: Path | None,
    output_dir: Path,
    app_id: str,
) -> Path:
    period_label = _period_label(cadencia, end)
    window_start = {
        "continuous": end - timedelta(minutes=15),
        "weekly": end - timedelta(days=7),
        "monthly": end - timedelta(days=30),
    }[cadencia]
    template = Template(_template_path(cadencia).read_text(encoding="utf-8"))
    substitutions = {
        "app_id": app_id,
        "period_label": period_label,
        "window_start": window_start.isoformat(),
        "window_end": end.isoformat(),
        "trace_contract_path": trace_contract_path.as_posix(),
        "thresholds_path": thresholds_path.as_posix(),
        "audit_source_path": audit_source_path.as_posix(),
        "n_calls_window": str(len(slices.primary)),
        "cost_per_call_usd_p50": f"USD {metrics.cost_per_call_usd_p50}",
        "cost_per_call_baseline_usd": f"USD {metrics.cost_per_call_baseline_usd}",
        "cost_usd_sum_30d": f"USD {metrics.cost_usd_sum_30d}",
        "budget_30d_usd": f"USD {BUDGET_30D_USD}",
        "latency_ms_total_p95": str(metrics.latency_ms_total_p95),
        "latency_ms_baseline_p95": str(metrics.latency_ms_baseline_p95),
        "cache_hit_rate_pct": f"{metrics.cache_hit_rate_pct:.2f}",
        "fallback_rate_pct": f"{metrics.fallback_rate_pct:.2f}",
        "input_tokens_total": str(sum(event.input_tokens_total for event in slices.primary)),
        "output_tokens_total": str(sum(event.output_tokens_total for event in slices.primary)),
        "anomalies_block": _anomalies_block(decision),
        "recommendation": decision.recommendation.value,
        "trace_ids": (
            ", ".join(event.event_id for event in slices.primary) or "sem-eventos-na-janela"
        ),
        "handoff_path": handoff_path.as_posix() if handoff_path else "-",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{app_id}_{cadencia}-{period_label}.md"
    report_path.write_text(template.safe_substitute(substitutions), encoding="utf-8")
    return report_path


def _load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"Contrato invalido: {path}")
    return raw


def run(args: argparse.Namespace) -> int:
    end = args.window_end or datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    else:
        end = end.astimezone(UTC)

    thresholds_path = Path(args.thresholds)
    trace_contract_path = Path(args.trace_contract)
    _load_contract(thresholds_path)
    _load_contract(trace_contract_path)

    events = load_events(Path(args.audit_jsonl), app_id=args.app_id)
    slices = build_slices(events, cadencia=args.cadencia, end=end)
    metrics = build_metrics(
        slices,
        cost_baseline_usd=Decimal(str(args.cost_baseline_usd)),
        latency_baseline_ms=args.latency_baseline_ms,
    )
    decision = CostMonitor.from_yaml(thresholds_path).evaluate(metrics)

    emitter = AlertEmitter(
        projeto_path=args.project_path,
        projeto="chatbot-RPinfo",
        sprint="003",
        emit_in_production=decision.recommendation is not Recommendation.MANTER_CONFIG,
    )
    handoff_path = emitter.emit(
        decision,
        app_id=args.app_id,
        cadencia=args.cadencia,
        timestamp=end,
    )

    report_path = render_report(
        cadencia=args.cadencia,
        end=end,
        slices=slices,
        metrics=metrics,
        decision=decision,
        audit_source_path=Path(args.audit_jsonl),
        thresholds_path=thresholds_path,
        trace_contract_path=trace_contract_path,
        handoff_path=handoff_path,
        output_dir=Path(args.output_dir),
        app_id=args.app_id,
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "app_id": args.app_id,
                "cadencia": args.cadencia,
                "recommendation": decision.recommendation.value,
                "emit_in_production": decision.recommendation
                is not Recommendation.MANTER_CONFIG,
                "handoff_path": str(handoff_path) if handoff_path else None,
                "report_path": str(report_path),
            },
            ensure_ascii=True,
        )
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa monitorar-custo-llm fora de src/**.")
    parser.add_argument("--cadencia", choices=["continuous", "weekly", "monthly"], required=True)
    parser.add_argument("--app-id", default=APP_ID)
    parser.add_argument(
        "--audit-jsonl",
        default=os.environ.get(
            "OBS_LLM_AUDIT_JSONL",
            str(PROJECT_ROOT / "observability" / "llm" / "runtime" / "audit_events.jsonl"),
        ),
    )
    parser.add_argument("--project-path", default=str(PROJECT_ROOT))
    parser.add_argument(
        "--thresholds",
        default=str(PROJECT_ROOT / "observability" / "llm" / "thresholds.yaml"),
    )
    parser.add_argument(
        "--trace-contract",
        default=str(PROJECT_ROOT / "observability" / "llm" / "qa_orchestrator_trace.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "observability" / "llm" / "reports"),
    )
    parser.add_argument("--cost-baseline-usd", default=str(DEFAULT_COST_BASELINE_USD))
    parser.add_argument("--latency-baseline-ms", type=int, default=DEFAULT_LATENCY_BASELINE_MS)
    parser.add_argument("--window-end", type=_parse_timestamp, default=None)
    return parser.parse_args(argv)


def main() -> int:
    return run(parse_args(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
