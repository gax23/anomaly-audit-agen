from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential

class BaseConnector(ABC):
    """Clase base abstracta para todos los conectores de fuentes de datos."""
    
    def __init__(self, source_name: str, config: dict[str, Any]) -> None:
        self.source_name = source_name
        self.config = config
    
    @abstractmethod
    def fetch_transactions(self, date_from: date, date_to: date) -> list[dict]:
        """Obtiene transacciones del sistema fuente en el rango de fechas indicado."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Verifica que la conexión al sistema fuente es exitosa."""
        pass
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_with_retry(self, date_from: date, date_to: date) -> list[dict]:
        """Versión con reintentos exponenciales de fetch_transactions."""
        return self.fetch_transactions(date_from, date_to)
    
    def _validate_date_range(self, date_from: date, date_to: date) -> None:
        """Valida que el rango de fechas sea válido."""
        if date_from > date_to:
            raise ValueError(f"La fecha de inicio ({date_from}) no puede ser mayor a la fecha de fin ({date_to}).")
    
    def _log_fetch_result(self, count: int, date_from: date, date_to: date) -> None:
        """Registra el resultado de la obtención de datos."""
        print(f"[{self.source_name}] Se obtuvieron {count} transacciones entre {date_from} y {date_to}.")
