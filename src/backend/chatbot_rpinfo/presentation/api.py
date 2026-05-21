from __future__ import annotations

from fastapi import FastAPI

from chatbot_rpinfo.config import AppSettings, load_settings
from chatbot_rpinfo.presentation.controllers.health_controller import router as health_router
from chatbot_rpinfo.presentation.dependencies import get_settings


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{resolved_settings.api_prefix}/openapi.json",
    )
    app.dependency_overrides[get_settings] = lambda: resolved_settings
    app.include_router(health_router, prefix=resolved_settings.api_prefix)
    return app
