"""
Configuración global de la aplicación usando Pydantic BaseSettings.
Todas las variables se cargan desde variables de entorno o archivo .env.
"""
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración centralizada del Agente de Detección de Anomalías.
    Las variables de entorno tienen prioridad sobre los valores por defecto.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # ─── Base de datos ────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+psycopg2://audit_user:secure_password@timescaledb:5432/audit_db"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ─── Seguridad ────────────────────────────────────────────────────────────
    secret_key: str = Field(default="cambia-esto-por-una-clave-segura-de-32-caracteres!!")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    api_key_header: str = Field(default="X-API-Key")
    api_key_secret: Optional[str] = Field(default=None)

    # ─── Modelos ML ───────────────────────────────────────────────────────────
    model_artifacts_path: str = Field(default="./artifacts")
    anomaly_threshold_percentile: float = Field(default=95.0)
    incremental_buffer_size: int = Field(default=500)

    # ─── Conector SAP Business One ───────────────────────────────────────────
    sap_b1_service_layer_url: Optional[str] = None
    sap_b1_username: Optional[str] = None
    sap_b1_password: Optional[str] = None
    sap_b1_company_db: Optional[str] = None

    # ─── Conector QuickBooks Online ───────────────────────────────────────────
    quickbooks_client_id: Optional[str] = None
    quickbooks_client_secret: Optional[str] = None
    quickbooks_redirect_uri: Optional[str] = None
    quickbooks_refresh_token: Optional[str] = None
    quickbooks_realm_id: Optional[str] = None

    # ─── Conector Odoo ────────────────────────────────────────────────────────
    odoo_url: Optional[str] = None
    odoo_database: Optional[str] = None
    odoo_username: Optional[str] = None
    odoo_api_key: Optional[str] = None

    # ─── Notificaciones ───────────────────────────────────────────────────────
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    alert_email_from: str = Field(default="alertas@tuempresa.com")
    alert_email_to: str = Field(default="auditor@tuempresa.com")
    webhook_url: Optional[str] = None

    # ─── General ──────────────────────────────────────────────────────────────
    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")
    default_currency: str = Field(default="USD")
    timezone: str = Field(default="America/Mexico_City")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que la clave secreta tenga al menos 32 caracteres."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Valida el formato básico de la URL de la base de datos."""
        valid_prefixes = (
            "postgresql://", "postgresql+psycopg2://",
            "postgresql+asyncpg://", "sqlite://", "sqlite+aiosqlite://",
        )
        if not v.startswith(valid_prefixes):
            raise ValueError(f"DATABASE_URL debe comenzar con uno de: {valid_prefixes}")
        return v

    @property
    def database_url_async(self) -> str:
        """
        URL para asyncpg, derivada de database_url de forma segura.
        Maneja los tres formatos comunes de URL de PostgreSQL:
          - postgresql+psycopg2://...  (SQLAlchemy explícito)
          - postgresql://...           (estándar)
          - postgres://...             (formato Heroku/Railway/Render)
        """
        url = self.database_url
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+asyncpg://"):
            return url  # ya es async, no tocar
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        # fallback: devuelve la URL original y deja que asyncpg falle con
        # un mensaje claro en lugar de un error críptico de SQLAlchemy
        return url

    @property
    def is_production(self) -> bool:
        """Verifica si el entorno actual es de producción."""
        return self.environment.lower() == "production"

    @property
    def redis_decoded_url(self) -> str:
        """Retorna la URL de Redis decodificada (alias para compatibilidad)."""
        return self.redis_url


# Instancia singleton: importar con `from config.settings import settings`
settings = Settings()