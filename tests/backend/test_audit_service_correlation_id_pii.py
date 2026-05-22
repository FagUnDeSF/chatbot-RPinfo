"""CG-04-OBS-2 (TL §2 parecer S2-C07) - defense-in-depth.

Validar que `AuditService.record_query_event` aplica
`assert_no_sensitive_identifiers` ao campo `correlation_id_upstream`
ANTES de persistir o evento.

Vetor protegido: cliente malicioso injeta CPF/CNPJ/email/etc no header HTTP
`X-Correlation-Id` (propagado upstream) -> sem validacao, o valor bruto
chegaria ao `AuditEvent.correlation_id_upstream` em disco, violando CG-04
(PII bruta nao persistida).

Comportamento esperado pos-fix: `SensitiveDataInTextError` levantado antes
de qualquer escrita no repository. `request_id` (UUID v4 deterministicamente
seguro gerado pelo controller) NAO precisa validacao - apenas
`correlation_id_upstream`.
"""

from __future__ import annotations

import pytest

from chatbot_rpinfo.application.services.audit_service import AuditService
from chatbot_rpinfo.domain.entities import (
    AuditResponseType,
    AuditSource,
    AuthenticatedPrincipal,
    InternalRole,
    InternalUser,
)
from chatbot_rpinfo.domain.policies import SensitiveDataInTextError
from chatbot_rpinfo.infrastructure.repositories import InMemoryAuditEventRepository


def _principal() -> AuthenticatedPrincipal:
    user = InternalUser(
        username="rp-direcao",
        display_name="Direcao RP Info",
        role=InternalRole.DIRECAO,
        token_env_var="INTERNAL_AUTH_DIRECAO_TOKEN",
    )
    return AuthenticatedPrincipal(user=user)


@pytest.fixture
def audit_service() -> AuditService:
    return AuditService(audit_event_repository=InMemoryAuditEventRepository())


@pytest.mark.parametrize(
    ("idempotency_key", "correlation_id_upstream"),
    [
        ("corr-cpf-fmt", "cpf-000.000.000-00-trace"),
        ("corr-cnpj-fmt", "trace-00.000.000/0000-00-leg"),
        ("corr-phone", "(11) 99999-9999"),
        ("corr-email", "contato joao@empresa.com.br"),
        ("corr-rg-sp", "rg-12.345.678-X"),
        ("corr-card-16", "4532 1234 5678 9012"),
        ("corr-digit-run", "trace1234567"),
    ],
)
def test_correlation_id_upstream_com_pii_bruta_e_rejeitado(
    audit_service: AuditService,
    idempotency_key: str,
    correlation_id_upstream: str,
) -> None:
    """`correlation_id_upstream` com padrao PII bruto -> bloqueio antes da gravacao.

    Cobertura para os 8 padroes canonicos de `_PATTERNS` em
    `domain/policies/sensitive_data_policy.py` (CPF fmt + CNPJ fmt + telefone
    + RG fmt + RG-SP variant + email + cartao BR 16 digitos + digit-run >=7).
    """
    with pytest.raises(SensitiveDataInTextError):
        audit_service.record_query_event(
            principal=_principal(),
            intent="qa_orchestrator:inventory_risk",
            source=AuditSource.QA_ORCHESTRATOR,
            response_type=AuditResponseType.ANSWERED,
            insufficient_data=False,
            idempotency_key=idempotency_key,
            correlation_id_upstream=correlation_id_upstream,
        )

    # Defense-in-depth: nada foi persistido no repositorio (bloqueio cedo).
    assert audit_service.list_events() == ()


def test_correlation_id_upstream_limpo_e_persistido(
    audit_service: AuditService,
) -> None:
    """`correlation_id_upstream` sem PII -> persiste normalmente.

    Caminho feliz: UUID/trace_id deterministicamente gerado upstream sem
    PII bruta passa pela validacao e o `AuditEvent` carrega o campo intacto.
    """
    clean_corr_id = "a3f1b9c4-d8e2-4a6f-b1c5-9f7e2a3b4c5d"  # UUID-like

    event = audit_service.record_query_event(
        principal=_principal(),
        intent="qa_orchestrator:inventory_risk",
        source=AuditSource.QA_ORCHESTRATOR,
        response_type=AuditResponseType.ANSWERED,
        insufficient_data=False,
        idempotency_key="corr-clean-001",
        correlation_id_upstream=clean_corr_id,
    )

    assert event.correlation_id_upstream == clean_corr_id


def test_correlation_id_upstream_none_e_aceito(audit_service: AuditService) -> None:
    """`correlation_id_upstream=None` -> bypass da validacao + campo fica None.

    Cliente que nao envia X-Correlation-Id e cenario legitimo (default na
    maioria dos requests). Validacao so dispara quando o header esta presente.
    """
    event = audit_service.record_query_event(
        principal=_principal(),
        intent="qa_orchestrator:sales_summary",
        source=AuditSource.QA_ORCHESTRATOR,
        response_type=AuditResponseType.ANSWERED,
        insufficient_data=False,
        idempotency_key="corr-none-001",
        correlation_id_upstream=None,
    )

    assert event.correlation_id_upstream is None
