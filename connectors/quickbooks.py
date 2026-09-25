"""
Conector para QuickBooks Online usando OAuth2 y el SDK python-quickbooks.
Obtiene transacciones del diario general de QuickBooks.
"""
import os
from datetime import date
from typing import Any, Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from connectors.base import BaseConnector


class QuickBooksConnector(BaseConnector):
    """Conector para QuickBooks Online via OAuth2 + python-quickbooks SDK."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Inicializa el conector QuickBooks Online.

        Args:
            config: Diccionario con client_id, client_secret, refresh_token, realm_id.
        """
        super().__init__("quickbooks", config)
        self.client_id = config.get("client_id", os.getenv("QUICKBOOKS_CLIENT_ID", ""))
        self.client_secret = config.get("client_secret", os.getenv("QUICKBOOKS_CLIENT_SECRET", ""))
        self.refresh_token = config.get("refresh_token", os.getenv("QUICKBOOKS_REFRESH_TOKEN", ""))
        self.realm_id = config.get("realm_id", os.getenv("QUICKBOOKS_REALM_ID", ""))
        self.redirect_uri = config.get(
            "redirect_uri", os.getenv("QUICKBOOKS_REDIRECT_URI", "http://localhost:8000/callback")
        )
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Obtiene o crea un cliente autenticado de QuickBooks."""
        try:
            from quickbooks import QuickBooks
            from quickbooks.objects.base import QuickbooksBaseObject

            if self._client is None:
                from intuitlib.client import AuthClient
                auth_client = AuthClient(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri=self.redirect_uri,
                    environment="production",
                )
                auth_client.refresh(refresh_token=self.refresh_token)
                self._client = QuickBooks(
                    auth_client=auth_client,
                    refresh_token=self.refresh_token,
                    company_id=self.realm_id,
                )
            return self._client
        except ImportError:
            raise ImportError(
                "python-quickbooks no está instalado. "
                "Ejecute: pip install python-quickbooks intuitlib"
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=15))
    def fetch_transactions(self, date_from: date, date_to: date) -> list[dict]:
        """
        Obtiene transacciones del diario de QuickBooks en el rango de fechas.

        Args:
            date_from: Fecha inicio.
            date_to: Fecha fin.

        Returns:
            Lista de transacciones normalizadas como dicts.
        """
        self._validate_date_range(date_from, date_to)
        client = self._get_client()

        try:
            from quickbooks.objects.journalentry import JournalEntry
            entries = JournalEntry.query(
                f"SELECT * FROM JournalEntry WHERE TxnDate >= '{date_from}' "
                f"AND TxnDate <= '{date_to}' MAXRESULTS 1000",
                qb=client,
            )
        except Exception as exc:
            logger.error(f"QuickBooks: error al obtener JournalEntries: {exc}")
            raise

        transactions = []
        for entry in entries:
            for line in getattr(entry, "Line", []):
                detail = getattr(line, "JournalEntryLineDetail", None)
                if not detail:
                    continue
                tx = {
                    "id": f"QB-{entry.Id}-{line.Id}",
                    "date": str(entry.TxnDate),
                    "amount": abs(float(getattr(line, "Amount", 0))),
                    "currency": getattr(entry, "CurrencyRef", {}).get("value", "USD"),
                    "account_debit": getattr(detail, "AccountRef", {}).get("value", ""),
                    "account_credit": getattr(detail, "AccountRef", {}).get("value", ""),
                    "description": getattr(line, "Description", "") or "",
                    "vendor_id": getattr(entry, "DocNumber", ""),
                    "source_system": "quickbooks",
                    "raw_data": entry.to_dict() if hasattr(entry, "to_dict") else {},
                }
                transactions.append(tx)

        self._log_fetch_result(len(transactions), date_from, date_to)
        return transactions

    def test_connection(self) -> bool:
        """Verifica la conectividad con QuickBooks Online."""
        if not self.client_id or not self.client_secret:
            logger.warning("QuickBooks: credenciales no configuradas")
            return False
        try:
            self._get_client()
            return True
        except Exception as exc:
            logger.error(f"QuickBooks: error de conexión: {exc}")
            return False
