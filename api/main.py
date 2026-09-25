"""
Aplicación principal FastAPI del Agente de Detección de Anomalías para Auditoría Financiera.
Configura middlewares, routers, lifespan y documentación OpenAPI.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pathlib import Path

from api.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware, limiter
from api.routes import transactions, anomalies, models, reports
from config.logging_config import setup_logging
from config.settings import settings
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación: inicialización y limpieza."""
    # Startup
    setup_logging()
    logger.info("🚀 Iniciando Agente de Detección de Anomalías...")

    # Crear directorios necesarios
    Path(settings.model_artifacts_path).mkdir(parents=True, exist_ok=True)
    Path("reports/output").mkdir(parents=True, exist_ok=True)
    Path("static/plots").mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ Entorno: {settings.environment} | DB: configurada | Redis: configurado")

    yield

    # Shutdown
    logger.info("🛑 Cerrando Agente de Detección de Anomalías...")


# Instancia principal de la aplicación
app = FastAPI(
    title="Agente de Detección de Anomalías para Auditoría Financiera",
    description=(
        "Sistema de monitoreo continuo de transacciones para PYMES. "
        "Detecta fraudes, errores y anomalías con IA explicable. "
        "Despliegue local — sin dependencias de APIs externas de IA."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiter (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares (orden importa: primero se aplica el último añadido)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit dashboard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "X-API-Key", "Content-Type", "X-Correlation-ID"],
)

# Archivos estáticos (plots SHAP, etc.)
try:
    Path("static/plots").mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass

# Registrar routers con prefijo v1
API_PREFIX = "/api/v1"
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(anomalies.router, prefix=API_PREFIX)
app.include_router(models.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


@app.get("/", tags=["Health"])
async def root() -> dict:
    """Health check raíz."""
    return {
        "service": "Agente de Detección de Anomalías",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "environment": settings.environment,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check detallado para Docker y balanceadores de carga."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "checks": {
            "api": "ok",
            "artifacts_path": Path(settings.model_artifacts_path).exists(),
        },
    }
