"""CG-04-OBS-1 (TL §2 parecer S2-C07) - regressao do tipo defensivo.

Antes do fix: `find_all_sensitive_identifiers` retornava `tuple[tuple[str, str],
...]` onde o segundo elemento era PII bruta. Contrato fragil porque qualquer
caller que fizesse `print(hits)` ou `logger.debug(hits)` vazava a PII via
`__repr__` padrao do tuple.

Depois do fix: o tipo retornado e `SensitiveIdentifierHit(@dataclass frozen
slots repr=False)` com `__repr__` customizado emitindo
`matched_value=***REDACTED***`. Defesa-em-profundidade equivalente a
`SonnetProviderFactory` (CO-1 S2-C07).

Este modulo testa:

1. `__repr__` + `__str__` + format() + f-strings NAO vazam `matched_value`.
2. `kind` continua publicavel (visivel em repr/log).
3. Acesso direto `hit.matched_value` continua disponivel para callers
   in-process (e.g. para validacao adicional).
"""

from __future__ import annotations

from chatbot_rpinfo.domain.policies import (
    SensitiveIdentifierHit,
    detect_sensitive_identifier,
    find_all_sensitive_identifiers,
    redact_sensitive_identifiers,
)


def test_sensitive_identifier_hit_repr_does_not_leak_matched_value() -> None:
    """`__repr__` e `__str__` MUST mask `matched_value`.

    Sentinela `LEAK-SENTINEL-DO-NOT-LOG` salt usado para qualquer aparicao
    em log/audit/repo ser imediatamente grep-flaggavel como vazamento.
    """
    sentinel = "999.888.777-66"  # CPF-formatted shape
    hit = SensitiveIdentifierHit(kind="cpf_formatted", matched_value=sentinel)

    assert sentinel not in repr(hit)
    assert sentinel not in str(hit)
    assert sentinel not in f"{hit!r}"
    assert sentinel not in f"{hit}"
    assert sentinel not in format(hit)

    # Categoria continua publicavel (sinal observability).
    assert "cpf_formatted" in repr(hit)
    assert "***REDACTED***" in repr(hit)

    # Acesso in-process ao matched_value continua disponivel para o caller
    # (usado por `redact_sensitive_identifiers` para construir o texto
    # mascarado; nunca persistido pelo orquestrador).
    assert hit.matched_value == sentinel
    assert hit.kind == "cpf_formatted"


def test_detect_sensitive_identifier_retorna_hit_defensivo() -> None:
    """`detect_sensitive_identifier` retorna `SensitiveIdentifierHit | None`.

    Contrato refatorado em CG-04-OBS-1 - antes retornava `tuple[str, str]`.
    """
    sentinel = "123.456.789-00"
    text = f"cliente CPF {sentinel} esta com saldo"

    hit = detect_sensitive_identifier(text)
    assert hit is not None
    assert isinstance(hit, SensitiveIdentifierHit)
    assert hit.kind == "cpf_formatted"
    assert hit.matched_value == sentinel
    # Defesa: print/log NAO vazaria.
    assert sentinel not in repr(hit)


def test_find_all_sensitive_identifiers_retorna_tuple_de_hits_defensivos() -> None:
    """`find_all_sensitive_identifiers` retorna tuple[SensitiveIdentifierHit, ...]."""
    text = "Contato joao@example.com ou CPF 111.222.333-44"

    hits = find_all_sensitive_identifiers(text)
    assert all(isinstance(h, SensitiveIdentifierHit) for h in hits)
    kinds = {h.kind for h in hits}
    assert "email" in kinds
    assert "cpf_formatted" in kinds

    # Defesa: serializar a sequencia inteira (caso caller faca log/print) NAO vaza PII.
    serialized_repr = repr(hits)
    assert "joao@example.com" not in serialized_repr
    assert "111.222.333-44" not in serialized_repr
    assert serialized_repr.count("***REDACTED***") == len(hits)


def test_redact_sensitive_identifiers_retorna_hits_defensivos() -> None:
    """`redact_sensitive_identifiers` retorna `(redacted_text, tuple[Hit, ...])`.

    Texto redacted contem `[REDACTED-{kind}]`; lista de hits e do tipo
    defensivo + serializavel sem vazar PII.
    """
    sentinel_email = "decio@example.com"
    text = f"contato {sentinel_email} entrega atrasada"

    redacted, hits = redact_sensitive_identifiers(text)

    assert sentinel_email not in redacted
    assert "[REDACTED-email]" in redacted
    assert len(hits) == 1
    assert isinstance(hits[0], SensitiveIdentifierHit)
    assert hits[0].kind == "email"
    assert hits[0].matched_value == sentinel_email
    # Defesa: log/print da tupla retornada NAO vazaria.
    assert sentinel_email not in repr(hits)
