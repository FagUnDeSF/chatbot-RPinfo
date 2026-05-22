"""Pytest bootstrap para o spike S1-SPK-05.

Adiciona o diretorio do spike ao `sys.path` para que `harness` seja
importavel como pacote absoluto. Necessario porque o slug do spike
contem traveSSoes (`S1-SPK-05-acuracia-estoque-margem`), invalidos como
identificador Python; o diretorio pai do `harness/` precisa entrar
explicitamente no path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SPIKE_ROOT = Path(__file__).resolve().parent
if str(_SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SPIKE_ROOT))
