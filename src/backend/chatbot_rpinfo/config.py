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
    secret_locations: tuple[str, ...] = Field(
        default=(
            "ERP_TESTE_DATABASE_URL",
            "AI_PROVIDER_API_KEY",
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
    )
