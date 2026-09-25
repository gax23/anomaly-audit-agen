"""
Middleware de la API: rate limiting, logging de requests con ID de correlación,
y manejo global de excepciones.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Instancia global de rate limiter (1 por proceso)
limiter = Limiter(key_func=get_remote_address)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que añade ID de correlación y registra cada request/response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar ID de correlación único por request
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()

        # Logging del request (sin datos sensibles del body)
        logger.bind(correlation_id=correlation_id).info(
            f"→ {request.method} {request.url.path} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.bind(correlation_id=correlation_id).error(
                f"Error no manejado: {type(exc).__name__}"
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor"},
                headers={"X-Correlation-ID": correlation_id},
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.bind(correlation_id=correlation_id).info(
            f"← {response.status_code} | {elapsed_ms:.1f}ms"
        )

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade headers de seguridad estándar a todas las respuestas."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
