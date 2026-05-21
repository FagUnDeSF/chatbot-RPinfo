from __future__ import annotations

from fastapi.testclient import TestClient

from chatbot_rpinfo.config import load_settings
from chatbot_rpinfo.presentation.api import create_app


def test_healthcheck_returns_service_status() -> None:
    app = create_app(
        load_settings(
            {
                "APP_NAME": "chatbot-RPinfo",
                "APP_ENV": "test",
                "APP_VERSION": "0.1.0",
            }
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "chatbot-RPinfo",
        "environment": "test",
        "version": "0.1.0",
    }


def test_settings_expose_secret_locations_without_loading_values() -> None:
    settings = load_settings(
        {
            "APP_NAME": "chatbot-RPinfo",
            "APP_ENV": "test",
            "APP_VERSION": "0.1.0",
            "ERP_TESTE_DATABASE_URL": "not-read-by-bootstrap",
        }
    )

    assert settings.secret_locations == ("ERP_TESTE_DATABASE_URL", "AI_PROVIDER_API_KEY")
    assert "not-read-by-bootstrap" not in settings.model_dump_json()

