from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from chatbot_rpinfo.application.services import (
    ContentPolicyBlockedError,
    ForcedProviderDeniedError,
    PiiBoundaryError,
    QaOrchestratorService,
)
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.presentation.dependencies import (
    get_current_principal,
    get_qa_orchestrator_service,
)
from chatbot_rpinfo.presentation.dtos import QaAskRequest, QaAskResponse

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post(
    "/ask",
    response_model=QaAskResponse,
    summary="Pergunta-resposta controlado sobre dado ERP read-only",
)
def ask(  # noqa: PLR0913 - canonical signature aligned with NIVEL-3 V5 §5.1
    payload: QaAskRequest,
    response: Response,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[QaOrchestratorService, Depends(get_qa_orchestrator_service)],
    escalate: Annotated[
        str | None,
        Header(alias="X-LLM-Escalate", min_length=1, max_length=32),
    ] = None,
    force_provider: Annotated[
        str | None,
        Header(alias="X-Force-Provider", min_length=1, max_length=64),
    ] = None,
    correlation_id_upstream: Annotated[
        str | None,
        Header(alias="X-Correlation-Id", min_length=1, max_length=128),
    ] = None,
) -> QaAskResponse:
    try:
        answer = service.ask(
            principal=principal,
            question=payload.question,
            idempotency_key=idempotency_key,
            escalate_header=escalate,
            force_provider_header=force_provider,
            correlation_id_upstream=correlation_id_upstream,
        )
    except ContentPolicyBlockedError as exc:
        # NIVEL-2 bloqueio: HTTP 422 com reason enumerado (V5 §4.1 / §4.2).
        # Sem mascarar como negativa honesta - usuario VE que foi bloqueado
        # por content policy (defesa em profundidade + auditabilidade).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "reason": "content_policy_blocked",
                "category": exc.match.category.value,
                "pattern_id": exc.match.pattern_id,
            },
        ) from exc
    except PiiBoundaryError as exc:
        # NIVEL-1 §3.1 bloqueio: HTTP 422 com reason enumerado. Mensagem
        # ao operador para reformular sem o identificador (V5 §3.1).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "reason": "pii_detectado_pre_egress",
                "kind": exc.kind,
                "message": (
                    "Pergunta contem identificador pessoal "
                    "(CPF/CNPJ/email/telefone/RG/cartao). Reformule sem o "
                    "identificador - o intent estrutural e suficiente "
                    "para a consulta."
                ),
            },
        ) from exc
    except ForcedProviderDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "forced_provider_role_denied"},
        ) from exc

    # NIVEL-4 / NIVEL-0 anti-fallback-silencioso element (c): propagate the
    # fallback signal via HTTP header so callers can react without parsing
    # the JSON body. NEVER mascarar como Haiku (AP-2 LLM CRITICAL).
    if answer.fallback_active and answer.provider == "stub-deterministico":
        response.headers["X-LLM-Fallback"] = "stub-deterministico"
    if answer.escalation_requested and not answer.escalation_granted:
        response.headers["X-LLM-Escalation-Denied"] = "gate_eval_missing"
    if answer.escalation_granted:
        response.headers["X-LLM-Escalation"] = "sonnet"

    return QaAskResponse.from_domain(answer)
