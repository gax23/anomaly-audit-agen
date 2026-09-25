"""Tests de integración para los endpoints de la API FastAPI."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """Cliente HTTP asíncrono para la API de test."""
    import os
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-32chars!!")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("MODEL_ARTIFACTS_PATH", "./test_artifacts")
    os.environ.setdefault("API_KEY_SECRET", "test-api-key-12345")

    from api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_headers() -> dict:
    """Headers con API Key para autenticación en tests."""
    return {"X-API-Key": "test-api-key-12345"}


class TestHealthEndpoints:
    """Tests para endpoints de health check."""

    @pytest.mark.asyncio
    async def test_root_returns_200(self, client: AsyncClient) -> None:
        """GET / debe retornar 200 con información del servicio."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """GET /health debe retornar 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self, client: AsyncClient) -> None:
        """La documentación OpenAPI debe estar disponible."""
        response = await client.get("/api/openapi.json")
        assert response.status_code == 200


class TestAuthenticationEndpoints:
    """Tests para autenticación."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient) -> None:
        """Sin autenticación se debe retornar 401."""
        response = await client.get("/api/v1/anomalies")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_api_key_returns_200(self, client: AsyncClient, api_headers: dict) -> None:
        """Con API Key válida se debe poder acceder a endpoints protegidos."""
        response = await client.get("/api/v1/anomalies", headers=api_headers)
        # 200 o cualquier código válido (no 401/403)
        assert response.status_code != 401
        assert response.status_code != 403


class TestModelStatusEndpoint:
    """Tests para el endpoint de estado del modelo."""

    @pytest.mark.asyncio
    async def test_model_status_returns_structure(
        self, client: AsyncClient, api_headers: dict
    ) -> None:
        """GET /api/v1/model/status debe retornar estructura correcta."""
        response = await client.get("/api/v1/model/status", headers=api_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "model_version" in data
        assert "is_training" in data


class TestReportPreviewEndpoint:
    """Tests para el endpoint de preview de reportes."""

    @pytest.mark.asyncio
    async def test_report_preview_returns_summary(
        self, client: AsyncClient, api_headers: dict
    ) -> None:
        """GET /api/v1/reports/preview debe retornar estructura del reporte."""
        response = await client.get(
            "/api/v1/reports/preview",
            params={"date_from": "2024-01-01", "date_to": "2024-03-31"},
            headers=api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_report_invalid_dates_returns_400(
        self, client: AsyncClient, api_headers: dict
    ) -> None:
        """Fechas invertidas deben retornar 400."""
        response = await client.get(
            "/api/v1/reports/generate",
            params={"date_from": "2024-12-31", "date_to": "2024-01-01"},
            headers=api_headers,
        )
        assert response.status_code == 400
