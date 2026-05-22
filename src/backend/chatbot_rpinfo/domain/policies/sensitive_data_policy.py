from __future__ import annotations

import re

_CPF_FORMATTED_RE = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_CNPJ_FORMATTED_RE = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
_PHONE_FORMATTED_RE = re.compile(
    r"(?<!\d)(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?9?\d{4}[\s-]\d{4}(?!\d)"
)
_RG_FORMATTED_RE = re.compile(r"(?<!\d)\d{1,2}\.\d{3}\.\d{3}-[\dXx](?![\dXx])")
_DIGIT_RUN_RE = re.compile(r"\d{7,}")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cpf_formatted", _CPF_FORMATTED_RE),
    ("cnpj_formatted", _CNPJ_FORMATTED_RE),
    ("phone_or_whatsapp_formatted", _PHONE_FORMATTED_RE),
    ("rg_formatted", _RG_FORMATTED_RE),
    ("numeric_identifier_run", _DIGIT_RUN_RE),
)


class SensitiveDataInTextError(ValueError):
    """Raised when a free-text field carries an identifier flagged as sensitive payload.

    The criterio literal de S1-C03 exige metadados de auditoria sem segredo nem
    payload sensivel bruto; a politica recusa CPF/CNPJ/telefone/identificadores
    numericos antes de gravar evento de auditoria ou ecoar na resposta.
    """

    def __init__(self, kind: str) -> None:
        super().__init__(f"sensitive_identifier_detected:{kind}")
        self.kind = kind


def assert_no_sensitive_identifiers(value: str) -> str:
    for kind, pattern in _PATTERNS:
        if pattern.search(value):
            raise SensitiveDataInTextError(kind)
    return value
