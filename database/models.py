"""
Modelos ORM de SQLAlchemy para el Agente de Auditoría Financiera.
Soporta cifrado de columnas sensibles y estructuras indexadas para TimescaleDB.
"""
import base64
from datetime import datetime
import os
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase


class EncryptedString(TypeDecorator):
    """Tipo de datos encriptado para almacenar cadenas sensibles en la base de datos."""

    impl = String(500)
    cache_ok = True

    def __init__(self, key: str = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        raw_key = key or os.getenv("SECRET_KEY", "default-secret-key-minimum-32chars!!")
        self.key = raw_key.encode("utf-8")

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        value_bytes = str(value).encode("utf-8")
        encrypted = bytes([b ^ self.key[i % len(self.key)] for i, b in enumerate(value_bytes)])
        return base64.b64encode(encrypted).decode("utf-8")

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        try:
            encrypted = base64.b64decode(value.encode("utf-8"))
            decrypted = bytes([b ^ self.key[i % len(self.key)] for i, b in enumerate(encrypted)])
            return decrypted.decode("utf-8")
        except Exception:
            return str(value)


class EncryptedNumeric(EncryptedString):
    """Tipo de datos encriptado para valores numéricos/monetarios."""

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        val = super().process_result_value(value, dialect)
        if val is not None:
            try:
                from decimal import Decimal
                return Decimal(val)
            except Exception:
                return val
        return None


class Base(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy."""
    pass


class TransactionModel(Base):
    """Modelo ORM para transacciones financieras."""

    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True)
    # Campos encriptados (datos sensibles)
    amount = Column(EncryptedNumeric(), nullable=False)
    account_debit = Column(EncryptedString(), nullable=False)
    account_credit = Column(EncryptedString(), nullable=False)
    vendor_id = Column(EncryptedString(), nullable=True)

    # Campos no encriptados (para indexar y filtrar)
    date = Column(DateTime, nullable=False, index=True)
    currency = Column(String(3), default="USD")
    description = Column(Text)
    employee_id = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    source_system = Column(String(50), nullable=False)

    # Features de ML (pre-calculadas)
    log_amount = Column(Float)
    hour_of_day = Column(Integer)
    day_of_week = Column(Integer)
    is_weekend = Column(Boolean)
    vendor_risk_score = Column(Float, default=0.5)
    amount_deviation = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_transactions_date_source", "date", "source_system"),
    )


class AnomalyModel(Base):
    """Modelo ORM para anomalías detectadas."""

    __tablename__ = "anomalies"

    id = Column(String(36), primary_key=True)
    transaction_id = Column(String(36), nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    rules_triggered = Column(JSON, default=list)
    ml_score = Column(Float, nullable=True)
    shap_values = Column(JSON, nullable=True)
    narrative = Column(Text, nullable=True)
    shap_plot_path = Column(String(500), nullable=True)
    status = Column(String(30), default="OPEN")  # OPEN, FALSE_POSITIVE, TRUE_POSITIVE
    reviewer_id = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)


class ModelMetricsModel(Base):
    """Modelo ORM para métricas de los modelos ML."""

    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    trained_at = Column(DateTime, default=datetime.utcnow)
    auc_roc = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    train_samples = Column(Integer)
    train_time_seconds = Column(Float)
    is_active = Column(Boolean, default=False)
    artifact_path = Column(String(500))


# Alias para compatibilidad de importaciones
AlertModel = AnomalyModel

