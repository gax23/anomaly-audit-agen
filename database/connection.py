"""
Gestión de conexiones a la base de datos.
Provee dos motores: síncrono (Alembic) y asíncrono (FastAPI).
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from config.settings import settings


# ─── Motor síncrono ───────────────────────────────────────────────────────────
# Solo para Alembic y scripts de migración. Alembic no soporta async.
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ─── Motor asíncrono ──────────────────────────────────────────────────────────
# Para todos los endpoints de FastAPI. Usa asyncpg internamente.
# La URL se construye en settings.database_url_async — nunca con .replace() aquí.
async_engine = create_async_engine(
    settings.database_url_async,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ─── Dependency de FastAPI ────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provee una sesión de base de datos por request.
    El commit es responsabilidad de cada operación de escritura.
    Este dependency solo garantiza el rollback ante excepciones.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ─── Lifecycle ────────────────────────────────────────────────────────────────
async def close_db_connections() -> None:
    """
    Cierra el pool de conexiones async.
    Llamar en el evento shutdown del lifespan de FastAPI:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            await close_db_connections()
    """
    await async_engine.dispose()