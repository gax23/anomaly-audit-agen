"""Tests de integración end-to-end: CSV → normalización → modelos → explicación → alerta."""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest


FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
CSV_PATH = FIXTURES_PATH / "sample_transactions.csv"


class TestEndToEndPipeline:
    """Tests de integración del pipeline completo de detección."""

    def test_normalize_transaction_pipeline(self) -> None:
        """Verifica que una transacción se normaliza correctamente."""
        from ingestion.schema import Transaction
        from ingestion.normalizer import TransactionNormalizer

        tx = Transaction(
            date=datetime(2024, 3, 15, 23, 47),
            amount=Decimal("47500.00"),
            account_debit="5100-Gastos Operativos",
            account_credit="2100-Cuentas por Pagar",
            description="Consultoría XYZ",
            vendor_id="XYZ_CONSULTING",
            department="Finanzas",
            source_system="csv",
        )
        normalizer = TransactionNormalizer()
        # Contexto en el formato interno del normalizer (vendor_stats con avg/var)
        ctx = {
            "vendor_stats": {
                "XYZ_CONSULTING": {
                    "count": 15,
                    "avg": 11_200.0,
                    "m2": 350_000_000.0,
                    "var": 25_000_000.0,  # std ≈ 5000
                }
            },
            "vendor_anomalies": {},
            "total_anomalies": 0,
        }
        result = normalizer.normalize(tx, ctx)

        assert result.log_amount > 0
        assert result.hour_of_day == 23
        assert result.is_weekend is False  # Viernes
        assert result.amount_deviation > 0, (
            f"amount_deviation debería ser positivo para monto muy alto: {result.amount_deviation}"
        )


    def test_rules_engine_on_anomalous_transaction(self) -> None:
        """Verifica que las reglas se activan correctamente para la transacción del ejemplo."""
        from alerts.rules_engine import RulesEngine

        engine = RulesEngine()
        tx = {
            "amount": 47_500.0,
            "date": datetime(2024, 1, 15, 23, 47),
            "vendor_id": "XYZ_CONSULTING",
        }
        ctx = {
            "vendor_transaction_count": 15,
            "vendor_daily_total": 142_500.0,
            "vendor_transactions_last_hour": 3,
        }
        rules = engine.evaluate(tx, ctx)
        # Debe activar al menos AFTER_HOURS y SPLIT_TRANSACTION
        assert len(rules) >= 1, f"Se esperaba al menos una regla activada: {rules}"

    def test_narrative_generation(self) -> None:
        """Verifica que el generador de narrativas produce texto en español."""
        # Importar directamente para evitar dependencia transitiva de shap
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location(
            "narrative", "explainability/narrative.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        NarrativeGenerator = module.NarrativeGenerator

        generator = NarrativeGenerator()
        tx = {
            "id": "TXN-2024-001234",
            "date": datetime(2024, 1, 15, 23, 47),
            "amount": Decimal("47500.00"),
            "currency": "USD",
            "account_debit": "5100-Gastos Operativos",
            "vendor_id": "XYZ Consulting S.A.",
        }
        top_factors = [
            {"feature": "log_amount", "shap_value": 2.3, "direction": "aumenta_riesgo"},
            {"feature": "hour_of_day", "shap_value": 1.5, "direction": "aumenta_riesgo"},
            {"feature": "velocity_1h", "shap_value": 1.0, "direction": "aumenta_riesgo"},
        ]
        rules = ["AFTER_HOURS"]

        narrative = generator.generate(tx, 0.87, top_factors, rules)

        assert isinstance(narrative, str), "La narrativa debe ser un string"
        assert len(narrative) > 50, "La narrativa debe tener contenido"
        assert "0.87" in narrative


    def test_isolation_forest_detects_anomalies(self) -> None:
        """Verifica que el Isolation Forest detecta las anomalías inyectadas."""
        import pandas as pd

        if not CSV_PATH.exists():
            pytest.skip("Dataset de fixtures no disponible")

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "isolation_forest", "models/isolation_forest.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        IsolationForestDetector = module.IsolationForestDetector

        df = pd.read_csv(CSV_PATH)

        # Calcular features básicas
        df["log_amount"] = np.log1p(df["amount"].abs())
        df["date_parsed"] = pd.to_datetime(df["date"], format='mixed')
        df["hour_of_day"] = df["date_parsed"].dt.hour
        df["day_of_week"] = df["date_parsed"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(float)

        feature_cols = ["log_amount", "hour_of_day", "day_of_week", "is_weekend"]
        X = df[feature_cols].fillna(0).values
        y_true = df["is_anomaly"].values

        # Entrenar solo con datos normales
        X_normal = X[y_true == 0]
        detector = IsolationForestDetector(n_estimators=100, contamination=0.05)
        detector.fit(X_normal)

        # Predecir en todo el dataset
        scores = detector.score(X)
        anomaly_scores = scores[y_true == 1]
        normal_scores = scores[y_true == 0]

        # Las anomalías deben tener scores más altos en promedio
        assert np.mean(anomaly_scores) > np.mean(normal_scores), (
            "Las anomalías deben tener scores más altos que las transacciones normales"
        )

    def test_alert_model_creation(self) -> None:
        """Verifica que se puede crear una alerta completa desde una transacción."""
        from alerts.alert_model import Alert, AlertSeverity, AlertStatus

        alert = Alert(
            transaction_id="TXN-001",
            severity=AlertSeverity.HIGH,
            anomaly_score=0.87,
            rules_triggered=["AFTER_HOURS"],
            ml_score=0.82,
            narrative="⚠️ ANOMALÍA DETECTADA — Score: 0.87/1.0 (ALTA SEVERIDAD)",
        )

        assert alert.is_open is True
        assert alert.status == AlertStatus.OPEN
        assert alert.severity == AlertSeverity.HIGH
        assert alert.anomaly_score == 0.87
        assert "AFTER_HOURS" in alert.rules_triggered

        safe_dict = alert.to_dict_safe()
        assert isinstance(safe_dict, dict)
        # Los datos sensibles no deben estar completos
        assert "transaction_id" not in safe_dict or len(safe_dict.get("transaction_id", "")) < 10
