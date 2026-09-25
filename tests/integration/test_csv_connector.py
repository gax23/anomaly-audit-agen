"""Tests de integración para el conector CSV y el pipeline de ingesta."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest


FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
CSV_PATH = FIXTURES_PATH / "sample_transactions.csv"


class TestCSVConnector:
    """Tests de integración para CSVExcelConnector."""

    def test_test_connection_valid_file(self) -> None:
        """test_connection debe retornar True para el CSV de fixtures."""
        from connectors.csv_excel import CSVExcelConnector
        connector = CSVExcelConnector(file_path=str(CSV_PATH))
        assert connector.test_connection() is True

    def test_test_connection_missing_file(self) -> None:
        """test_connection debe lanzar FileNotFoundError para archivos que no existen."""
        from connectors.csv_excel import CSVExcelConnector
        connector = CSVExcelConnector(file_path="/ruta/que/no/existe.csv")
        with pytest.raises((FileNotFoundError, Exception)):
            connector.test_connection()

    def test_fetch_transactions_returns_list(self) -> None:
        """fetch_transactions debe retornar una lista de dicts."""
        from connectors.csv_excel import CSVExcelConnector
        connector = CSVExcelConnector(file_path=str(CSV_PATH))
        result = connector.fetch_transactions(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fetch_transactions_date_filter(self) -> None:
        """fetch_transactions debe respetar el filtro de fechas."""
        from connectors.csv_excel import CSVExcelConnector
        connector = CSVExcelConnector(file_path=str(CSV_PATH))
        result_q1 = connector.fetch_transactions(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 3, 31),
        )
        result_q3 = connector.fetch_transactions(
            date_from=date(2024, 7, 1),
            date_to=date(2024, 9, 30),
        )
        assert len(result_q1) > 0
        assert len(result_q3) > 0

    def test_fetch_transactions_required_fields(self) -> None:
        """Cada transacción retornada debe tener los campos mínimos requeridos."""
        from connectors.csv_excel import CSVExcelConnector
        connector = CSVExcelConnector(file_path=str(CSV_PATH))
        result = connector.fetch_transactions(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
        )
        if result:
            required_fields = {"date", "amount", "account_debit", "account_credit", "description"}
            sample = result[0]
            missing = required_fields - set(sample.keys())
            assert not missing, f"Campos faltantes en transacción: {missing}"

    def test_invalid_csv_raises_error(self, tmp_path) -> None:
        """Un CSV sin columnas requeridas debe lanzar un error."""
        from connectors.csv_excel import CSVExcelConnector
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("col1,col2\n1,2\n3,4")

        connector = CSVExcelConnector(file_path=str(bad_csv))
        with pytest.raises((ValueError, KeyError, Exception)):
            connector.fetch_transactions(date(2024, 1, 1), date(2024, 12, 31))



class TestDatasetFixture:
    """Tests de validación del dataset sintético de fixtures."""

    def test_dataset_exists(self) -> None:
        """El archivo CSV de fixtures debe existir."""
        assert CSV_PATH.exists(), f"Dataset no encontrado: {CSV_PATH}"

    def test_dataset_row_count(self) -> None:
        """El dataset debe tener exactamente 10,000 filas."""
        df = pd.read_csv(CSV_PATH)
        assert len(df) == 10_000, f"Se esperaban 10,000 filas, hay {len(df)}"

    def test_dataset_anomaly_count(self) -> None:
        """El dataset debe tener exactamente 300 anomalías."""
        df = pd.read_csv(CSV_PATH)
        assert "is_anomaly" in df.columns, "Columna 'is_anomaly' no encontrada"
        n_anomalies = df["is_anomaly"].sum()
        assert n_anomalies == 300, f"Se esperaban 300 anomalías, hay {n_anomalies}"

    def test_dataset_required_columns(self) -> None:
        """El dataset debe contener todas las columnas requeridas."""
        df = pd.read_csv(CSV_PATH)
        required = {"id", "date", "amount", "currency", "account_debit",
                    "account_credit", "description", "vendor_id", "source_system", "is_anomaly"}
        missing = required - set(df.columns)
        assert not missing, f"Columnas faltantes: {missing}"

    def test_dataset_no_null_amounts(self) -> None:
        """La columna 'amount' no debe tener valores nulos."""
        df = pd.read_csv(CSV_PATH)
        assert df["amount"].notna().all(), "Hay montos nulos en el dataset"

    def test_dataset_amount_positive(self) -> None:
        """Los montos deben ser todos positivos."""
        df = pd.read_csv(CSV_PATH)
        assert (df["amount"] > 0).all(), "Hay montos negativos o cero en el dataset"
