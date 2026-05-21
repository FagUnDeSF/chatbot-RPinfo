from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from chatbot_rpinfo.application.services import HealthService
from chatbot_rpinfo.config import AppSettings, load_settings


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def get_health_service(settings: Annotated[AppSettings, Depends(get_settings)]) -> HealthService:
    return HealthService(settings=settings)

