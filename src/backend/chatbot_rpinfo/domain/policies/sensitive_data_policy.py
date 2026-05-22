"""Sensitive-data policy helpers (PII boundary V5 NIVEL-1 §3.1 + §3.2).

Public surface:

- `assert_no_sensitive_identifiers(value)` - raise on first match.
- `detect_sensitive_identifier(value)` - first match as `SensitiveIdentifierHit | None`.
- `find_all_sensitive_identifiers(value)` - all matches as
  `tuple[SensitiveIdentifierHit, ...]`.
- `redact_sensitive_identifiers(value)` - `(redacted_text, hits)` with
  `[REDACTED-{kind}]` substituted.
- `SensitiveIdentifierHit` - dataclass-frozen tipo defensivo retornando
  `kind` (categoria publicavel) + `matched_value` (PII bruta com `__repr__`
  mascarado para nao vazar em log/traceback/APM).

CG-04-OBS-1 (TL §2 parecer S2-C07) fechada via introducao do tipo
`SensitiveIdentifierHit` em vez do antigo `tuple[str, str]`:

- Antes: API retornava `tuple[str, str]` onde o segundo elemento era a
  PII bruta - contrato fragil porque qualquer caller podia, por engano,
  chamar `print(hits)` ou `logger.debug(hits)` e vazar a PII via
  `__repr__` padrao do tuple.
- Agora: API retorna `SensitiveIdentifierHit(@dataclass frozen slots
  repr=False)` com `__repr__` customizado mascarando o `matched_value`.
  Mesmo defesa-em-profundidade que a `SonnetProviderFactory` (CO-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CPF_FORMATTED_RE = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_CNPJ_FORMATTED_RE = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
_PHONE_FORMATTED_RE = re.compile(
    r"(?<!\d)(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?9?\d{4}[\s-]\d{4}(?!\d)"
)
_RG_FORMATTED_RE = re.compile(r"(?<!\d)\d{1,2}\.\d{3}\.\d{3}-[\dXx](?![\dXx])")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")

# RG-SP variant (Security carimbou via V5 cross-security ajuste #1; cross-link
# TD-001 da S1-C03). Permite pontos/hifen opcionais. NUNCA aplicar como single
# source: combinar com `_RG_FORMATTED_RE` quando a versao formatada estrita for
# necessaria (por exemplo, validacao de ID emitido sintaticamente correto).
_RG_SP_VARIANT_RE = re.compile(r"(?<!\d)\d{1,2}\.?\d{3}\.?\d{3}-?[\dXx](?![\dXx])")

# Cartao de credito BR 16 digitos (Security carimbou via V5 cross-security
# ajuste #1). Bloqueio explicito antes de envio ao LLM para evitar transferencia
# internacional Art. 33 LGPD com numero de cartao bruto.
_CARD_BR_RE = re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}\s?\d{4}(?!\d)")

# Regra defensiva: runs >=7 digitos consecutivos sao rejeitados como possivel
# PII (CPF/CNPJ/RG/telefone). Decisao PM TD-003 caminho `manter+documentar`
# (formalizada em
# equipe/pm-senior/decisoes/2026-05-22_TD-003-trade-off-cobertura-vs-precisao.md).
# Trade-off aceito: false-positive teorico em SKU/NF/codigo-pedido legitimo
# favorecendo seguranca PII durante prova controlada interna. Plano de revisao:
# reavaliar quando (a) >=3 false-positive observados em uso real em 30 dias OR
# (b) primeira sprint pos-go-live amplo. Detalhes adicionais e justificativa
# completa em SENSITIVE_DATA_POLICY.md co-localizado neste pacote.
_DIGIT_RUN_RE = re.compile(r"\d{7,}")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cpf_formatted", _CPF_FORMATTED_RE),
    ("cnpj_formatted", _CNPJ_FORMATTED_RE),
    ("phone_or_whatsapp_formatted", _PHONE_FORMATTED_RE),
    ("rg_formatted", _RG_FORMATTED_RE),
    ("rg_sp_variant", _RG_SP_VARIANT_RE),
    ("card_br_16_digits", _CARD_BR_RE),
    ("email", _EMAIL_RE),
    ("numeric_identifier_run", _DIGIT_RUN_RE),
)


@dataclass(frozen=True, slots=True, repr=False)
class SensitiveIdentifierHit:
    """Hit defensivo de PII detectada (CG-04-OBS-1 TL §2 parecer S2-C07).

    Estrutura canonica para retorno de `detect_sensitive_identifier` +
    `find_all_sensitive_identifiers` + `redact_sensitive_identifiers`.

    Campos:

    - `kind` - categoria publicavel (cpf_formatted / cnpj_formatted / email
      / etc). Pode ser logada, persistida em audit, exposta em response
      payload. Vocab fechado canonico do `_PATTERNS`.
    - `matched_value` - PII bruta literal capturada pelo regex. NUNCA
      persistir; NUNCA logar; NUNCA expor em response payload. O
      `__repr__` mascarado defende callers que esqueceram dessa regra.

    AP-12-style defense-in-depth (mesmo padrao da `SonnetProviderFactory`
    fechada em CO-1 S2-C07): dataclass com `repr=False` e `__repr__`
    customizado emitindo `matched_value=***REDACTED***`.
    """

    kind: str
    matched_value: str

    def __repr__(self) -> str:
        return f"SensitiveIdentifierHit(kind={self.kind!r}, matched_value=***REDACTED***)"

    def __str__(self) -> str:
        return self.__repr__()


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


def detect_sensitive_identifier(value: str) -> SensitiveIdentifierHit | None:
    """Find the first sensitive-identifier match without raising.

    Used by NIVEL-1 §3.1 PII boundary pre-egress LLM (V5 guarda-em-camadas +
    V5 Security ajuste #1) and by NIVEL-1 §3.2 PII recall mask post-egress
    LLM. Returns `SensitiveIdentifierHit` (CG-04-OBS-1 fechada) ao inves de
    `tuple[str, str]` para defesa-em-profundidade via `__repr__` mascarado.
    """
    for kind, pattern in _PATTERNS:
        match = pattern.search(value)
        if match is not None:
            return SensitiveIdentifierHit(kind=kind, matched_value=match.group(0))
    return None


def find_all_sensitive_identifiers(value: str) -> tuple[SensitiveIdentifierHit, ...]:
    """Find every sensitive-identifier hit without raising.

    Used by NIVEL-1 §3.2 output filter to mask each occurrence with
    `[REDACTED-{kind}]`. Order of results follows the `_PATTERNS` declaration.
    Returns sequence of `SensitiveIdentifierHit` (CG-04-OBS-1 fechada) com
    `matched_value` protegido via `__repr__` mascarado.
    """
    hits: list[SensitiveIdentifierHit] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(value):
            hits.append(SensitiveIdentifierHit(kind=kind, matched_value=match.group(0)))
    return tuple(hits)


def redact_sensitive_identifiers(
    value: str,
) -> tuple[str, tuple[SensitiveIdentifierHit, ...]]:
    """Replace every sensitive-identifier hit with `[REDACTED-{kind}]`.

    Returns `(redacted_text, hits)` where `hits` mirrors
    `find_all_sensitive_identifiers`. CG-04 preserved: no raw value is stored
    by callers; the second tuple records `SensitiveIdentifierHit` whose
    `__repr__` masks the raw substring (CG-04-OBS-1 defense-in-depth). The
    raw `matched_value` field is available to the caller in-process (e.g.
    for further validation) but `repr(hit)` and `str(hit)` are safe.
    """
    redacted = value
    hits: list[SensitiveIdentifierHit] = []
    for kind, pattern in _PATTERNS:

        def _replace(match: re.Match[str], _kind: str = kind) -> str:
            hits.append(
                SensitiveIdentifierHit(kind=_kind, matched_value=match.group(0))
            )
            return f"[REDACTED-{_kind}]"

        redacted = pattern.sub(_replace, redacted)
    return redacted, tuple(hits)
