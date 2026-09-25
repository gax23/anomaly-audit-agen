"""Tests unitarios para el normalizador de transacciones."""
from datetime import datetime
from decimal import Decimal

import pytest


@pytest.fixture
def normalizer():
    """Instancia del TransactionNormalizer."""
    from ingestion.normalizer import TransactionNormalizer
    return TransactionNormalizer()


@pytest.fixture
def sample_transaction():
    """Transacción de muestra para normalización."""
    from ingestion.schema import Transaction
    return Transaction(
        id="TXN-001",
        date=datetime(2024, 6, 15, 14, 30, 0),  # Sábado 14:30
        amount=Decimal("5500.00"),
        currency="USD",
        account_debit="5100-Gastos Operativos",
        account_credit="2100-Cuentas por Pagar",
        description="Pago a proveedor",
        vendor_id="V001",
        department="Finanzas",
        source_system="csv",
    )


@pytest.fixture
def historical_context() -> dict:
    """Contexto histórico de ejemplo en el formato que usa TransactionNormalizer."""
    return {
        "vendor_stats": {
            "V001": {
                "count": 50,
                "avg": 3000.0,
                "m2": 49_000_000.0,
                "var": 1_000_000.0,  # std = 1000
            }
        },
        "vendor_anomalies": {"V001": 1},
        "total_anomalies": 50,
    }


class TestTransactionNormalizer:
    """Tests para TransactionNormalizer."""

    def test_log_amount_calculation(self, normalizer, sample_transaction, historical_context) -> None:
        """log_amount debe ser log(amount + 1)."""
        import math
        result = normalizer.normalize(sample_transaction, historical_context)
        expected = math.log1p(5500.0)
        assert abs(result.log_amount - expected) < 1e-6, (
            f"log_amount esperado {expected:.4f}, obtenido {result.log_amount:.4f}"
        )

    def test_hour_of_day_extraction(self, normalizer, sample_transaction, historical_context) -> None:
        """hour_of_day debe extraerse correctamente de la fecha."""
        result = normalizer.normalize(sample_transaction, historical_context)
        assert result.hour_of_day == 14, f"Esperado 14, obtenido {result.hour_of_day}"

    def test_day_of_week_extraction(self, normalizer, sample_transaction, historical_context) -> None:
        """day_of_week: 2024-06-15 es sábado (day=5 en Python)."""
        result = normalizer.normalize(sample_transaction, historical_context)
        assert result.day_of_week == 5, f"Esperado 5 (sábado), obtenido {result.day_of_week}"

    def test_is_weekend_saturday(self, normalizer, sample_transaction, historical_context) -> None:
        """is_weekend debe ser True para sábados."""
        result = normalizer.normalize(sample_transaction, historical_context)
        assert result.is_weekend is True, "Sábado debe ser fin de semana"

    def test_is_weekend_monday(self, normalizer, historical_context) -> None:
        """is_weekend debe ser False para días laborables."""
        from ingestion.schema import Transaction
        tx = Transaction(
            date=datetime(2024, 6, 17, 10, 0),  # Lunes
            amount=Decimal("1000.00"),
            account_debit="5100",
            account_credit="2100",
            description="Test",
            source_system="csv",
        )
        result = normalizer.normalize(tx, historical_context)
        assert result.is_weekend is False, "Lunes no debe ser fin de semana"

    def test_account_encoded_deterministic(self, normalizer, sample_transaction, historical_context) -> None:
        """account_encoded debe ser determinista para la misma cuenta."""
        r1 = normalizer.normalize(sample_transaction, historical_context)
        r2 = normalizer.normalize(sample_transaction, historical_context)
        assert r1.account_encoded == r2.account_encoded, "account_encoded debe ser determinista"

    def test_account_encoded_range(self, normalizer, sample_transaction, historical_context) -> None:
        """account_encoded debe estar en el rango [0, 1]."""
        result = normalizer.normalize(sample_transaction, historical_context)
        assert 0.0 <= result.account_encoded <= 1.0, (
            f"account_encoded fuera de rango: {result.account_encoded}"
        )

    def test_amount_deviation_with_context(self, normalizer, sample_transaction, historical_context) -> None:
        """amount_deviation debe calcularse correctamente con contexto histórico."""
        result = normalizer.normalize(sample_transaction, historical_context)
        # $5500 con avg=$3000, std=$1000 → desviación = (5500-3000)/1000 = 2.5
        assert abs(result.amount_deviation - 2.5) < 0.01, (
            f"amount_deviation esperado ~2.5, obtenido {result.amount_deviation}"
        )

    def test_normalize_batch_returns_correct_count(
        self, normalizer, sample_transaction, historical_context
    ) -> None:
        """normalize_batch debe retornar el mismo número de transacciones que recibe."""
        transactions = [sample_transaction] * 5
        results = normalizer.normalize_batch(transactions)
        assert len(results) == 5, f"Esperadas 5 transacciones, obtenidas {len(results)}"

    def test_source_system_preserved(self, normalizer, sample_transaction, historical_context) -> None:
        """El source_system original debe preservarse en la transacción normalizada."""
        result = normalizer.normalize(sample_transaction, historical_context)
        assert result.source_system == "csv"
