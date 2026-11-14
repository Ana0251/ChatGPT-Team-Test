"""HTTP smoke tests for the H-03 FastAPI foundation."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_returns_ok() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_application_name_is_configurable() -> None:
    with TestClient(create_app(Settings(app_name="Hesabyar Test API"))) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Hesabyar Test API"


def test_unknown_route_returns_404() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/does-not-exist")

    assert response.status_code == 404
