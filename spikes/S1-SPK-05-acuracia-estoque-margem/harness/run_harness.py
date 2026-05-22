"""Runner reproduzivel do spike S1-SPK-05.

Comando reproduzivel:
    python -m spikes.S1_SPK_05_acuracia_estoque_margem.harness.run_harness \
        --output-dir spikes/S1-SPK-05-acuracia-estoque-margem/outputs \
        [--relatorio-oficial-path <path>] \
        [--threshold-dias-sem-venda 90]

Fluxo:
1. Constroi `InMemoryErpReadonlyRepository` com fixture estendida do spike.
2. Instancia `ErpReadonlyService` com `AuditService` em-memoria (preserva a
   fronteira read-only canonica + idempotency_key + allowlist + limit).
3. Executa queries `inventory_risk_spike_S1_C05` e
   `sales_summary_spike_S1_C05` via service (mesma rota de validacao).
4. Aplica regras analiticas com premissas declaradas.
5. Tenta carregar relatorio oficial; marca margem como inconclusiva se ausente.
6. Grava `result.json` + `result.csv` em `outputs/<timestamp>/` com:
   - timestamp UTC ISO-8601;
   - hash SHA-256 da amostra serializada canonicamente;
   - premissas literais por metrica;
   - veredicto por metrica;
   - fonte (query_name + source + colunas) por metrica;
   - decisao explicita sobre relatorio oficial.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(_SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SPIKE_ROOT))

from chatbot_rpinfo.application.services.audit_service import AuditService  # noqa: E402
from chatbot_rpinfo.application.services.erp_readonly_service import (  # noqa: E402
    ErpReadonlyService,
)
from chatbot_rpinfo.config import AppSettings  # noqa: E402
from chatbot_rpinfo.domain.entities import (  # noqa: E402
    AuthenticatedPrincipal,
    ErpReadonlyQuery,
    ErpReadonlyResult,
    InternalRole,
    InternalUser,
)
from chatbot_rpinfo.infrastructure.repositories.in_memory_audit_event_repository import (  # noqa: E402
    InMemoryAuditEventRepository,
)
from harness.comparacao import (  # noqa: E402
    RelatorioOficial,
    RelatorioOficialIndisponivel,
    load_relatorio_oficial,
)
from harness.fixture import (  # noqa: E402
    INVENTORY_RISK_SPIKE_QUERY_NAME,
    SALES_SUMMARY_SPIKE_QUERY_NAME,
    SPIKE_AS_OF_DATE,
    build_spike_repository,
)
from harness.metrics import (  # noqa: E402
    MetricResult,
    compute_estoque_fantasma,
    compute_margem,
)

SPIKE_ID = "S1-SPK-05-acuracia-estoque-margem"
SPIKE_CAND = "S1-C05"

_PRINCIPAL = AuthenticatedPrincipal(
    user=InternalUser(
        username="rp-admin-tecnico",
        display_name="Admin Tecnico RP Info",
        role=InternalRole.ADMIN_TECNICO,
        token_env_var="INTERNAL_AUTH_ADMIN_TECNICO_TOKEN",
    )
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Harness reproduzivel do spike {SPIKE_ID}",
    )
    parser.add_argument(
        "--output-dir",
        default="spikes/S1-SPK-05-acuracia-estoque-margem/outputs",
        help="diretorio onde gravar os artefatos do run",
    )
    parser.add_argument(
        "--relatorio-oficial-path",
        default=None,
        help="path opcional para relatorio oficial RP Info (.csv ou .json)",
    )
    parser.add_argument(
        "--threshold-dias-sem-venda",
        type=int,
        default=90,
        help="hipotese tecnica do spike: dias sem venda para classificar SKU fantasma",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    settings = AppSettings()
    repository = build_spike_repository(
        timeout_seconds=settings.erp_readonly_timeout_seconds,
        max_rows=settings.erp_readonly_max_rows,
    )
    audit_service = AuditService(InMemoryAuditEventRepository())
    erp_service = ErpReadonlyService(
        settings=settings,
        repository=repository,
        audit_service=audit_service,
    )

    inventory_result = _execute(
        erp_service,
        INVENTORY_RISK_SPIKE_QUERY_NAME,
        limit=settings.erp_readonly_max_rows,
    )
    sales_result = _execute(
        erp_service,
        SALES_SUMMARY_SPIKE_QUERY_NAME,
        limit=settings.erp_readonly_max_rows,
    )

    relatorio = load_relatorio_oficial(args.relatorio_oficial_path)
    relatorio_disponivel = isinstance(relatorio, RelatorioOficial)

    estoque_fantasma = compute_estoque_fantasma(
        sample=inventory_result,
        threshold_dias_sem_venda=args.threshold_dias_sem_venda,
        as_of_date=SPIKE_AS_OF_DATE,
    )
    margem = compute_margem(
        sample=sales_result,
        as_of_date=SPIKE_AS_OF_DATE,
        relatorio_oficial_disponivel=relatorio_disponivel,
    )

    output = _build_output(
        spike_id=SPIKE_ID,
        cand=SPIKE_CAND,
        inventory_result=inventory_result,
        sales_result=sales_result,
        relatorio=relatorio,
        metrics=(estoque_fantasma, margem),
        threshold_dias_sem_venda=args.threshold_dias_sem_venda,
    )
    output_dir = _persist(Path(args.output_dir), output, metrics=(estoque_fantasma, margem))
    print(f"output: {output_dir}")
    return 0


def _execute(service: ErpReadonlyService, query_name: str, limit: int) -> ErpReadonlyResult:
    query = ErpReadonlyQuery(name=query_name, parameters={}, limit=limit)
    idempotency_key = f"spike-{SPIKE_ID}-{query_name}-{uuid4()}"
    return service.execute(principal=_PRINCIPAL, query=query, idempotency_key=idempotency_key)


def _build_output(
    spike_id: str,
    cand: str,
    inventory_result: ErpReadonlyResult,
    sales_result: ErpReadonlyResult,
    relatorio: RelatorioOficial | RelatorioOficialIndisponivel,
    metrics: tuple[MetricResult, ...],
    threshold_dias_sem_venda: int,
) -> dict[str, Any]:
    inventory_hash = _sha256_canonical(inventory_result)
    sales_hash = _sha256_canonical(sales_result)
    relatorio_block: dict[str, Any]
    if isinstance(relatorio, RelatorioOficial):
        relatorio_block = {
            "status": "disponivel",
            "path": relatorio.path,
            "n_rows": len(relatorio.rows),
        }
    else:
        relatorio_block = {"status": "indisponivel", "motivo": relatorio.motivo}
    return {
        "spike_id": spike_id,
        "cand": cand,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "threshold_dias_sem_venda": threshold_dias_sem_venda,
        "amostras": {
            "inventory": {
                "query_name": inventory_result.query_name,
                "source": inventory_result.source,
                "n_rows": inventory_result.row_count,
                "read_only": inventory_result.read_only,
                "sha256": inventory_hash,
            },
            "sales": {
                "query_name": sales_result.query_name,
                "source": sales_result.source,
                "n_rows": sales_result.row_count,
                "read_only": sales_result.read_only,
                "sha256": sales_hash,
            },
        },
        "relatorio_oficial": relatorio_block,
        "metricas": [m.to_dict() for m in metrics],
    }


def _persist(
    base_dir: Path, output: dict[str, Any], metrics: tuple[MetricResult, ...]
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with (run_dir / "result.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric_name", "veredicto", "query_name", "source", "motivo"])
        for metric in metrics:
            writer.writerow(
                [
                    metric.metric_name,
                    metric.veredicto,
                    metric.fonte.get("query_name", ""),
                    metric.fonte.get("source", ""),
                    (metric.motivo or "").replace("\n", " ").strip(),
                ]
            )
    return run_dir


def _sha256_canonical(result: ErpReadonlyResult) -> str:
    payload = {
        "query_name": result.query_name,
        "source": result.source,
        "read_only": result.read_only,
        "rows": [dict(sorted(row.items())) for row in result.rows],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


if __name__ == "__main__":
    sys.exit(run())
