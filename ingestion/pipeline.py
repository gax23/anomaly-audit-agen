from datetime import date
from typing import Any
from connectors.base import BaseConnector
from connectors.csv_excel import CSVExcelConnector
from ingestion.schema import Transaction
from ingestion.normalizer import TransactionNormalizer

class IngestionPipeline:
    """Orquesta el pipeline de ingesta de datos."""
    
    def __init__(self) -> None:
        self.normalizer = TransactionNormalizer()
        
    async def ingest_from_connector(self, connector: BaseConnector, date_from: date, date_to: date) -> dict[str, int]:
        """Orquesta fetch -> validate -> normalize -> store -> trigger_detection."""
        stats = {"processed": 0, "errors": 0, "anomalies_detected": 0}
        
        try:
            if not connector.test_connection():
                raise ConnectionError("Fallo en la prueba de conexión al origen de datos.")
                
            raw_data = connector.fetch_with_retry(date_from, date_to)
            
            transactions = []
            for item in raw_data:
                try:
                    tx = Transaction(**item)
                    transactions.append(tx)
                except Exception as e:
                    stats["errors"] += 1
            
            normalized_txs = self.normalizer.normalize_batch(transactions)
            stats["processed"] = len(normalized_txs)
            
            # trigger_detection simulado o logica final
            for tx in normalized_txs:
                if getattr(tx, "is_anomaly", False):
                    stats["anomalies_detected"] += 1
                    
        except Exception as e:
            print(f"Error en ingest_from_connector: {e}")
            stats["errors"] += 1
            
        return stats

    async def ingest_from_csv(self, file_path: str) -> dict[str, int]:
        """Ejecuta la ingesta especificamente desde un archivo CSV."""
        connector = CSVExcelConnector(file_path=file_path)
        d_from = date(1970, 1, 1)
        d_to = date.today()
        return await self.ingest_from_connector(connector, d_from, d_to)
