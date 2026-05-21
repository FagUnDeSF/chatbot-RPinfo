from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chatbot_rpinfo.config import load_settings
from chatbot_rpinfo.presentation.api import create_app


@pytest.fixture()
def client() -> TestClient:
    token_source = {
        "INTERNAL_AUTH_DIRECAO_TOKEN": "test-direcao-token",
        "INTERNAL_AUTH_COMERCIAL_TOKEN": "test-comercial-token",
        "INTERNAL_AUTH_PREVENCAO_TOKEN": "test-prevencao-token",
        "INTERNAL_AUTH_ADMIN_TECNICO_TOKEN": "test-admin-token",
    }
    app = create_app(
        load_settings(
            {
                "APP_NAME": "chatbot-RPinfo",
                "APP_ENV": "test",
                "APP_VERSION": "0.1.0",
            }
        ),
        token_source=token_source,
    )
    return TestClient(app)
