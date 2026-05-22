from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from chatbot_rpinfo.domain.entities.access import InternalRole


class InternalUserConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    role: InternalRole
    token_env_var: str = Field(min_length=1, pattern=r"^[A-Z0-9_]+$")


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = Field(default="chatbot-RPinfo", min_length=1)
    environment: str = Field(default="local", min_length=1)
    version: str = Field(default="0.1.0", min_length=1)
    api_prefix: str = Field(default="/api/v1", pattern=r"^/[a-z0-9/_-]+$")
    erp_readonly_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    erp_readonly_max_rows: int = Field(default=100, ge=1, le=1000)

    # --- ADR-0005 LLM provider settings (Sprint 002 S2-C07) ----------------
    # AP-12 universal: NEVER persist secret value in repo. These fields hold
    # LOCATION (env var name) only. The actual key is read from environment
    # at DI bootstrap and forwarded to the Anthropic SDK client.
    llm_provider: str = Field(default="anthropic", min_length=1)
    llm_default_model: str = Field(
        default="claude-haiku-4-5-20251001", min_length=1
    )
    llm_escalation_model: str = Field(
        default="claude-sonnet-4-5-20250929", min_length=1
    )
    llm_max_tokens: int = Field(default=600, ge=1, le=4000)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    llm_monthly_budget_usd: float = Field(default=30.0, gt=0, le=10000)
    llm_cache_target_pct: float = Field(default=70.0, ge=0, le=100)
    llm_phase: int = Field(default=1, ge=1, le=2)
    # `anthropic_api_key_env_var` is the NAME of the env var to read. Default
    # `ANTHROPIC_API_KEY` aligns with Anthropic SDK convention.
    anthropic_api_key_env_var: str = Field(
        default="ANTHROPIC_API_KEY", min_length=1, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    # `use_stub_deterministico` forces the stub provider regardless of
    # ANTHROPIC_API_KEY presence. Used by local dev + pytest suites that do
    # not exercise the real provider. Off by default in production runtime.
    use_stub_deterministico: bool = Field(default=False)

    secret_locations: tuple[str, ...] = Field(
        default=(
            "ERP_TESTE_DATABASE_URL",
            "AI_PROVIDER_API_KEY",
            "ANTHROPIC_API_KEY",
            "INTERNAL_AUTH_DIRECAO_TOKEN",
            "INTERNAL_AUTH_COMERCIAL_TOKEN",
            "INTERNAL_AUTH_PREVENCAO_TOKEN",
            "INTERNAL_AUTH_ADMIN_TECNICO_TOKEN",
        )
    )
    internal_users: tuple[InternalUserConfig, ...] = Field(
        default=(
            InternalUserConfig(
                username="rp-direcao",
                display_name="Direcao RP Info",
                role=InternalRole.DIRECAO,
                token_env_var="INTERNAL_AUTH_DIRECAO_TOKEN",
            ),
            InternalUserConfig(
                username="rp-comercial",
                display_name="Comercial RP Info",
                role=InternalRole.COMERCIAL,
                token_env_var="INTERNAL_AUTH_COMERCIAL_TOKEN",
            ),
            InternalUserConfig(
                username="rp-prevencao",
                display_name="Prevencao RP Info",
                role=InternalRole.PREVENCAO,
                token_env_var="INTERNAL_AUTH_PREVENCAO_TOKEN",
            ),
            InternalUserConfig(
                username="rp-admin-tecnico",
                display_name="Admin Tecnico RP Info",
                role=InternalRole.ADMIN_TECNICO,
                token_env_var="INTERNAL_AUTH_ADMIN_TECNICO_TOKEN",
            ),
        )
    )


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    source = os.environ if environ is None else environ
    return AppSettings(
        app_name=source.get("APP_NAME", "chatbot-RPinfo"),
        environment=source.get("APP_ENV", "local"),
        version=source.get("APP_VERSION", "0.1.0"),
        erp_readonly_timeout_seconds=float(source.get("ERP_READONLY_TIMEOUT_SECONDS", "5.0")),
        erp_readonly_max_rows=int(source.get("ERP_READONLY_MAX_ROWS", "100")),
        use_stub_deterministico=source.get("USE_STUB_DETERMINISTICO", "false").lower()
        in {"1", "true", "yes"},
        llm_monthly_budget_usd=float(source.get("LLM_MONTHLY_BUDGET_USD", "30.0")),
    )
