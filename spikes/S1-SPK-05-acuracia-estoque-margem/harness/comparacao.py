"""Comparacao opcional contra relatorio oficial RP Info.

Quando a Direcao disponibilizar relatorio oficial para a janela do spike,
o harness aceita um arquivo CSV/JSON via parametro e gera diff por loja.
Sem relatorio, o harness retorna `RelatorioOficialIndisponivel` e o
runner marca margem/estoque-fantasma como `inconclusiva`.

Contrato do relatorio oficial (esperado quando existir):
- CSV/JSON contendo, no minimo: `store_id`, `period`, `gross_sales_oficial`,
  `cmv_oficial`, `n_skus_fantasma_oficial`.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RelatorioOficial:
    path: str
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class RelatorioOficialIndisponivel:
    motivo: str


def load_relatorio_oficial(path: str | None) -> RelatorioOficial | RelatorioOficialIndisponivel:
    if path is None:
        return RelatorioOficialIndisponivel(
            motivo="path nao fornecido (parametro --relatorio-oficial-path ausente)"
        )
    p = Path(path)
    if not p.exists():
        return RelatorioOficialIndisponivel(motivo=f"arquivo nao encontrado em {path}")
    suffix = p.suffix.lower()
    if suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return RelatorioOficialIndisponivel(
                motivo=f"formato invalido em {path}: esperado lista JSON de registros"
            )
        return RelatorioOficial(path=str(p), rows=tuple(data))
    if suffix == ".csv":
        with p.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = tuple(dict(row) for row in reader)
        return RelatorioOficial(path=str(p), rows=rows)
    return RelatorioOficialIndisponivel(
        motivo=f"extensao nao suportada em {path}: use .csv ou .json"
    )
