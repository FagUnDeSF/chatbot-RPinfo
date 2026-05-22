"""Teste reproduzivel do spike S1-SPK-05.

Roda o harness sem relatorio oficial e valida:
- output JSON tem shape esperado (spike_id, cand, timestamp, amostras, metricas);
- amostras carregam hash SHA-256 nao vazio;
- metrica `estoque_fantasma` retorna lista de candidatos (>= 0 sob amostra
  sintetica conhecida);
- metrica `margem` eh `inconclusiva` quando CMV ausente e relatorio
  indisponivel (caminho default do spike).
- arquivo `result.csv` eh gravado com 2 linhas + header.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(_SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SPIKE_ROOT))

from harness.fixture import (  # noqa: E402
    INVENTORY_RISK_SPIKE_QUERY_NAME,
    SALES_SUMMARY_SPIKE_QUERY_NAME,
)
from harness.run_harness import run  # noqa: E402


def test_harness_apenas_harness_margem_inconclusiva(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    rc = run(["--output-dir", str(output_dir), "--threshold-dias-sem-venda", "90"])
    assert rc == 0

    runs = list(output_dir.iterdir())
    assert len(runs) == 1
    run_dir = runs[0]
    result_json = run_dir / "result.json"
    result_csv = run_dir / "result.csv"
    assert result_json.exists()
    assert result_csv.exists()

    payload = json.loads(result_json.read_text(encoding="utf-8"))
    assert payload["spike_id"] == "S1-SPK-05-acuracia-estoque-margem"
    assert payload["cand"] == "S1-C05"
    assert payload["threshold_dias_sem_venda"] == 90
    assert payload["amostras"]["inventory"]["query_name"] == INVENTORY_RISK_SPIKE_QUERY_NAME
    assert payload["amostras"]["sales"]["query_name"] == SALES_SUMMARY_SPIKE_QUERY_NAME
    assert len(payload["amostras"]["inventory"]["sha256"]) == 64
    assert len(payload["amostras"]["sales"]["sha256"]) == 64
    assert payload["relatorio_oficial"]["status"] == "indisponivel"

    metricas = {m["metric_name"]: m for m in payload["metricas"]}
    assert set(metricas) == {"estoque_fantasma", "margem"}

    estoque = metricas["estoque_fantasma"]
    assert estoque["fonte"]["query_name"] == INVENTORY_RISK_SPIKE_QUERY_NAME
    assert estoque["premissas"]["threshold_dias_sem_venda"] == 90
    assert estoque["valor"]["n_skus_amostrados"] >= 1
    assert estoque["valor"]["n_skus_fantasma_candidatos"] >= 0

    margem = metricas["margem"]
    assert margem["veredicto"] == "inconclusiva"
    assert "CMV ausente" in (margem["motivo"] or "")
    assert "relatorio oficial RP Info indisponivel" in (margem["motivo"] or "")

    with result_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["metric_name", "veredicto", "query_name", "source", "motivo"]
    assert len(rows) == 1 + 2  # header + 2 metricas
