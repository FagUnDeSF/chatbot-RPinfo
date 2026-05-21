from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = Field(default="chatbot-RPinfo", min_length=1)
    environment: str = Field(default="local", min_length=1)
    version: str = Field(default="0.1.0", min_length=1)
    api_prefix: str = Field(default="/api/v1", pattern=r"^/[a-z0-9/_-]+$")
    secret_locations: tuple[str, ...] = Field(
        default=("ERP_TESTE_DATABASE_URL", "AI_PROVIDER_API_KEY")
    )


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    source = os.environ if environ is None else environ
    return AppSettings(
        app_name=source.get("APP_NAME", "chatbot-RPinfo"),
        environment=source.get("APP_ENV", "local"),
        version=source.get("APP_VERSION", "0.1.0"),
    )

