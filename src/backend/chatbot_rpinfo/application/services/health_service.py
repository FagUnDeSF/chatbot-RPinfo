from __future__ import annotations

from chatbot_rpinfo.config import AppSettings
from chatbot_rpinfo.domain.entities import HealthStatus


class HealthService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def get_status(self) -> HealthStatus:
        return HealthStatus(
            status="ok",
            service=self._settings.app_name,
            environment=self._settings.environment,
            version=self._settings.version,
        )

