from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from chatbot_rpinfo.application.services import HealthService
from chatbot_rpinfo.presentation.dependencies import get_health_service
from chatbot_rpinfo.presentation.dtos.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
def healthcheck(service: Annotated[HealthService, Depends(get_health_service)]) -> HealthResponse:
    return HealthResponse.from_domain(service.get_status())

