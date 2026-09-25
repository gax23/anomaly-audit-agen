"""Tests unitarios para el motor de reglas de negocio."""
from datetime import datetime
from decimal import Decimal

import pytest


@pytest.fixture
def engine():
    """Instancia del motor de reglas con configuración de test."""
    from alerts.rules_engine import RulesEngine
    return RulesEngine(
        round_amount_threshold=10_000.0,
        after_hours_amount_threshold=5_000.0,
        velocity_spike_limit=3,
        velocity_window_minutes=60,
        split_transaction_daily_threshold=50_000.0,
        new_vendor_amount_threshold=30_000.0,
    )


@pytest.fixture
def normal_context() -> dict:
    """Contexto histórico normal: proveedor conocido con historial."""
    return {
        "vendor_transaction_count": 50,
        "vendor_daily_total": 5_000.0,
        "vendor_transactions_last_hour": 1,
        "vendor_avg_amount": 3_000.0,
    }


class TestRulesEngine:
    """Tests unitarios para el motor de reglas deterministas."""

    def test_round_amount_triggered(self, engine, normal_context: dict) -> None:
        """ROUND_AMOUNT debe activarse para montos exactamente redondos > umbral."""
        tx = {
            "amount": 15_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "ROUND_AMOUNT" in rules, "Debe activarse ROUND_AMOUNT para $15,000"

    def test_round_amount_not_triggered_below_threshold(self, engine, normal_context: dict) -> None:
        """ROUND_AMOUNT NO debe activarse si el monto redondo está bajo el umbral."""
        tx = {
            "amount": 5_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "ROUND_AMOUNT" not in rules

    def test_round_amount_not_triggered_non_round(self, engine, normal_context: dict) -> None:
        """ROUND_AMOUNT NO debe activarse para montos con decimales."""
        tx = {
            "amount": 15_342.75,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "ROUND_AMOUNT" not in rules

    def test_after_hours_night(self, engine, normal_context: dict) -> None:
        """AFTER_HOURS debe activarse para transacciones nocturnas con monto alto."""
        tx = {
            "amount": 8_000.0,
            "date": datetime(2024, 3, 15, 23, 47),  # 23:47
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "AFTER_HOURS" in rules, "Debe activarse AFTER_HOURS a las 23:47"

    def test_after_hours_weekend(self, engine, normal_context: dict) -> None:
        """AFTER_HOURS debe activarse en fin de semana con monto alto."""
        # datetime(2024, 3, 16) es sábado
        tx = {
            "amount": 7_000.0,
            "date": datetime(2024, 3, 16, 14, 0),  # Sábado al mediodía
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "AFTER_HOURS" in rules, "Debe activarse AFTER_HOURS en sábado"

    def test_after_hours_not_triggered_business_hours(self, engine, normal_context: dict) -> None:
        """AFTER_HOURS NO debe activarse en horario laboral normal."""
        tx = {
            "amount": 8_000.0,
            "date": datetime(2024, 3, 15, 10, 30),  # Viernes 10:30
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "AFTER_HOURS" not in rules

    def test_velocity_spike(self, engine, normal_context: dict) -> None:
        """VELOCITY_SPIKE debe activarse cuando hay demasiadas transacciones en 1h."""
        ctx = {**normal_context, "vendor_transactions_last_hour": 5}  # > límite de 3
        tx = {
            "amount": 1_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, ctx)
        assert "VELOCITY_SPIKE" in rules

    def test_velocity_spike_not_triggered(self, engine, normal_context: dict) -> None:
        """VELOCITY_SPIKE NO debe activarse si la velocidad está dentro del límite."""
        tx = {
            "amount": 1_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert "VELOCITY_SPIKE" not in rules

    def test_split_transaction(self, engine, normal_context: dict) -> None:
        """SPLIT_TRANSACTION debe activarse cuando la suma diaria supera el umbral."""
        ctx = {**normal_context, "vendor_daily_total": 55_000.0}
        tx = {
            "amount": 5_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, ctx)
        assert "SPLIT_TRANSACTION" in rules

    def test_new_vendor_large(self, engine, normal_context: dict) -> None:
        """NEW_VENDOR_LARGE debe activarse para pagos grandes a proveedores nuevos."""
        ctx = {**normal_context, "vendor_transaction_count": 0}  # Proveedor nuevo
        tx = {
            "amount": 35_000.0,
            "date": datetime(2024, 3, 15, 10, 0),
            "vendor_id": "VNEW001",
        }
        rules = engine.evaluate(tx, ctx)
        assert "NEW_VENDOR_LARGE" in rules

    def test_no_rules_for_normal_transaction(self, engine, normal_context: dict) -> None:
        """Una transacción completamente normal no debe activar ninguna regla."""
        tx = {
            "amount": 2_500.75,
            "date": datetime(2024, 3, 15, 10, 30),
            "vendor_id": "V001",
        }
        rules = engine.evaluate(tx, normal_context)
        assert len(rules) == 0, f"No deberían activarse reglas: {rules}"

    def test_multiple_rules_can_trigger_simultaneously(self, engine) -> None:
        """Múltiples reglas pueden activarse para una sola transacción."""
        ctx = {
            "vendor_transaction_count": 0,
            "vendor_daily_total": 55_000.0,
            "vendor_transactions_last_hour": 6,
        }
        tx = {
            "amount": 20_000.0,  # Redondo + nuevo proveedor + velocidad
            "date": datetime(2024, 3, 16, 23, 0),  # Sábado de noche
            "vendor_id": "VNEW002",
        }
        rules = engine.evaluate(tx, ctx)
        assert len(rules) >= 2, f"Deben activarse múltiples reglas, solo se activaron: {rules}"
