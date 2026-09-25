"""
Conector para SAP Business One via Service Layer REST API.
Obtiene asientos de diario del endpoint /b1s/v1/JournalEntries.
"""
import os
from datetime import date, datetime
from typing import Any, Optional

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from connectors.base import BaseConnector


class SAPB1Connector(BaseConnector):
    """Conector para SAP Business One Service Layer REST API."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Inicializa el conector SAP B1.

        Args:
            config: Diccionario con service_layer_url, username, password, company_db.
        """
        super().__init__("sap_b1", config)
        self.base_url = config.get("service_layer_url", os.getenv("SAP_B1_SERVICE_LAYER_URL", ""))
        self.username = config.get("username", os.getenv("SAP_B1_USERNAME", ""))
        self.password = config.get("password", os.getenv("SAP_B1_PASSWORD", ""))
        self.company_db = config.get("company_db", os.getenv("SAP_B1_COMPANY_DB", ""))
        self._session_id: Optional[str] = None
        self._session = requests.Session()
        # Ignorar SSL en entornos de desarrollo (configurar cert en producción)
        self._session.verify = config.get("verify_ssl", True)

    def _login(self) -> bool:
        """Inicia sesión en el Service Layer y obtiene el SessionId."""
        url = f"{self.base_url}/b1s/v1/Login"
        payload = {
            "CompanyDB": self.company_db,
            "UserName": self.username,
            "Password": self.password,
        }
        try:
            resp = self._session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            self._session_id = resp.json().get("SessionId")
            self._session.headers.update({"B1SESSION": self._session_id})
            logger.info("SAP B1: sesión iniciada exitosamente")
            return True
        except Exception as exc:
            logger.error(f"SAP B1: error al iniciar sesión: {type(exc).__name__}")
            return False

    def _logout(self) -> None:
        """Cierra la sesión activa en el Service Layer."""
        if self._session_id:
            try:
                self._session.post(f"{self.base_url}/b1s/v1/Logout", timeout=10)
            except Exception:
                pass
            finally:
                self._session_id = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_transactions(self, date_from: date, date_to: date) -> list[dict]:
        """
        Obtiene asientos de diario del SAP B1 en el rango de fechas.

        Args:
            date_from: Fecha inicio.
            date_to: Fecha fin.

        Returns:
            Lista de transacciones normalizadas como dicts.
        """
        self._validate_date_range(date_from, date_to)

        if not self._session_id and not self._login():
            raise ConnectionError("No se pudo autenticar con SAP B1")

        url = f"{self.base_url}/b1s/v1/JournalEntries"
        params = {
            "$filter": (
                f"ReferenceDate ge '{date_from.isoformat()}' and "
                f"ReferenceDate le '{date_to.isoformat()}'"
            ),
            "$select": "JdtNum,ReferenceDate,Memo,TransactionCode,Lines",
            "$top": 1000,
        }

        transactions = []
        try:
            resp = self._session.get(url, params=params, timeout=60)
            resp.raise_for_status()
            entries = resp.json().get("value", [])

            for entry in entries:
                for line in entry.get("Lines", []):
                    tx = {
                        "id": f"SAP-{entry.get('JdtNum')}-{line.get('Line_ID', 0)}",
                        "date": entry.get("ReferenceDate"),
                        "amount": abs(float(line.get("Debit", 0) or line.get("Credit", 0))),
                        "currency": line.get("FCCurrency", "USD"),
                        "account_debit": str(line.get("AccountCode", "")),
                        "account_credit": str(line.get("AccountCode", "")),
                        "description": entry.get("Memo", ""),
                        "vendor_id": str(line.get("ShortName", "")),
                        "source_system": "sap_b1",
                        "raw_data": entry,
                    }
                    transactions.append(tx)

            self._log_fetch_result(len(transactions), date_from, date_to)
        except Exception as exc:
            logger.error(f"SAP B1: error al obtener transacciones: {exc}")
            raise

        return transactions

    def test_connection(self) -> bool:
        """Verifica la conectividad con el Service Layer de SAP B1."""
        if not self.base_url:
            logger.warning("SAP B1: SAP_B1_SERVICE_LAYER_URL no configurado")
            return False
        return self._login()
