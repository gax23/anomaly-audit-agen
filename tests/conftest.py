"""Configuración global de pytest: fixtures compartidas y hooks."""
import os
import pytest


def pytest_configure(config) -> None:
    """Configuración inicial de pytest: establece variables de entorno de test."""
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-32chars!!")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_audit.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("MODEL_ARTIFACTS_PATH", "./test_artifacts")
    os.environ.setdefault("API_KEY_SECRET", "test-api-key-12345")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session", autouse=True)
def setup_test_directories() -> None:
    """Crea directorios necesarios para los tests."""
    import pathlib
    pathlib.Path("./test_artifacts").mkdir(exist_ok=True)
    pathlib.Path("./reports/output").mkdir(parents=True, exist_ok=True)
    pathlib.Path("./static/plots").mkdir(parents=True, exist_ok=True)


@pytest.fixture
def sample_feature_matrix():
    """Matriz de features de muestra para tests de modelos ML."""
    import numpy as np
    np.random.seed(42)
    return np.random.randn(100, 9).astype(np.float32)


@pytest.fixture
def sample_anomaly_dict() -> dict:
    """Diccionario de anomalía de muestra para tests."""
    from datetime import datetime
    return {
        "id": "ANOMALY-TEST-001",
        "transaction_id": "TXN-TEST-001",
        "detected_at": datetime(2024, 1, 15, 23, 47),
        "anomaly_score": 0.87,
        "severity": "HIGH",
        "rules_triggered": ["AFTER_HOURS", "ROUND_AMOUNT"],
        "ml_score": 0.82,
        "narrative": "⚠️ ANOMALÍA DETECTADA",
        "status": "OPEN",
    }
