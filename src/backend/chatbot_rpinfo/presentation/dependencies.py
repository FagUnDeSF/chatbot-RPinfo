from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status

from chatbot_rpinfo.application.services import (
    MODEL_HAIKU_4_5,
    AnthropicLlmProvider,
    AuditService,
    AuthenticationError,
    DeterministicKeywordIntentClassifier,
    ErpReadonlyService,
    HealthService,
    InMemoryGateEvalCache,
    IntentClassifier,
    InternalAuthService,
    LlmProvider,
    LlmRouter,
    QaOrchestratorService,
    SonnetProviderFactory,
    StubDeterministicLlmProvider,
)
from chatbot_rpinfo.config import AppSettings, load_settings
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.domain.repositories import (
    AuditEventRepository,
    ErpReadonlyRepository,
    InternalUserRepository,
)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def get_health_service(settings: Annotated[AppSettings, Depends(get_settings)]) -> HealthService:
    return HealthService(settings=settings)


def get_internal_user_repository(request: Request) -> InternalUserRepository:
    return cast(InternalUserRepository, request.app.state.internal_user_repository)


def get_audit_event_repository(request: Request) -> AuditEventRepository:
    return cast(AuditEventRepository, request.app.state.audit_event_repository)


def get_erp_readonly_repository(request: Request) -> ErpReadonlyRepository:
    return cast(ErpReadonlyRepository, request.app.state.erp_readonly_repository)


def get_token_source(request: Request) -> Mapping[str, str]:
    return cast(Mapping[str, str], request.app.state.token_source)


def get_internal_auth_service(
    user_repository: Annotated[InternalUserRepository, Depends(get_internal_user_repository)],
    token_source: Annotated[Mapping[str, str], Depends(get_token_source)],
) -> InternalAuthService:
    return InternalAuthService(user_repository=user_repository, token_source=token_source)


def get_audit_service(
    audit_event_repository: Annotated[AuditEventRepository, Depends(get_audit_event_repository)],
) -> AuditService:
    return AuditService(audit_event_repository=audit_event_repository)


def get_erp_readonly_service(
    settings: Annotated[AppSettings, Depends(get_settings)],
    erp_repository: Annotated[ErpReadonlyRepository, Depends(get_erp_readonly_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> ErpReadonlyService:
    return ErpReadonlyService(
        settings=settings,
        repository=erp_repository,
        audit_service=audit_service,
    )


@lru_cache(maxsize=1)
def get_intent_classifier() -> IntentClassifier:
    return DeterministicKeywordIntentClassifier()


@lru_cache(maxsize=1)
def _build_llm_router() -> LlmRouter:
    """Bootstrap the LlmRouter with the providers chosen by environment.

    Selection rule:
      - `USE_STUB_DETERMINISTICO=true` OR `ANTHROPIC_API_KEY` absent -> stub
        is wired as the Haiku "slot" (router still enforces NIVEL-4 invariant;
        Sonnet escalation is unavailable). This is the dev/test default.
      - `ANTHROPIC_API_KEY` present -> Anthropic Haiku 4.5 in the slot;
        SonnetProviderFactory wired so router can escalate when gate-eval
        passes.

    AP-12 universal: this function reads the key value from os.environ and
    forwards it ONLY to AnthropicLlmProvider/SonnetProviderFactory. Never
    logged, never stored, never returned.
    """
    settings = get_settings()
    api_key = os.environ.get(settings.anthropic_api_key_env_var)
    if settings.use_stub_deterministico or not api_key:
        stub = StubDeterministicLlmProvider()
        return LlmRouter(
            haiku_provider=stub,
            sonnet_provider_factory=None,
            stub_provider=stub,
            gate_eval_cache=InMemoryGateEvalCache(),
        )

    haiku = AnthropicLlmProvider(
        api_key=api_key,
        model=settings.llm_default_model or MODEL_HAIKU_4_5,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )
    sonnet_factory = SonnetProviderFactory(api_key=api_key)
    return LlmRouter(
        haiku_provider=haiku,
        sonnet_provider_factory=sonnet_factory,
        stub_provider=StubDeterministicLlmProvider(),
        gate_eval_cache=InMemoryGateEvalCache(),
    )


def get_llm_router() -> LlmRouter:
    # Tests may override `app.state.llm_router` with a custom router (e.g.
    # mock providers + pre-populated gate-eval cache).
    return _build_llm_router()


def get_llm_provider() -> LlmProvider:
    """Kept for backward compatibility (S001 callers).

    New code should depend on `get_llm_router` and consume the chosen provider
    via `RouterDecision`. This shim exposes the stub for tests that mock the
    legacy LlmProvider seam.
    """
    return StubDeterministicLlmProvider()


def get_qa_orchestrator_service(
    intent_classifier: Annotated[IntentClassifier, Depends(get_intent_classifier)],
    erp_service: Annotated[ErpReadonlyService, Depends(get_erp_readonly_service)],
    llm_router: Annotated[LlmRouter, Depends(get_llm_router)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> QaOrchestratorService:
    return QaOrchestratorService(
        intent_classifier=intent_classifier,
        erp_readonly_service=erp_service,
        llm_router=llm_router,
        audit_service=audit_service,
    )


def get_current_principal(
    username: Annotated[str, Header(alias="X-Internal-Username", min_length=3, max_length=64)],
    token: Annotated[str, Header(alias="X-Internal-Token", min_length=1, max_length=256)],
    service: Annotated[InternalAuthService, Depends(get_internal_auth_service)],
) -> AuthenticatedPrincipal:
    try:
        return service.authenticate(username=username, token=token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_internal_credentials",
        ) from exc
