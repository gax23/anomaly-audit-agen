"""
Conector para Odoo via XML-RPC con autenticación por API key.
Compatible con Odoo 14, 15, 16 y 17.
"""
import os
import xmlrpc.client
from datetime import date, datetime
from typing import Any, Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from connectors.base import BaseConnector


class OdooConnector(BaseConnector):
    """Conector para Odoo via XML-RPC con autenticación por API key."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Inicializa el conector Odoo.

        Args:
            config: Diccionario con url, database, username, api_key.
        """
        super().__init__("odoo", config)
        self.url = config.get("url", os.getenv("ODOO_URL", ""))
        self.database = config.get("database", os.getenv("ODOO_DATABASE", ""))
        self.username = config.get("username", os.getenv("ODOO_USERNAME", ""))
        self.api_key = config.get("api_key", os.getenv("ODOO_API_KEY", ""))
        self._uid: Optional[int] = None
        self._models_proxy: Optional[xmlrpc.client.ServerProxy] = None

    def _authenticate(self) -> bool:
        """Autentica contra Odoo y obtiene el UID del usuario."""
        if not self.url or not self.database:
            logger.warning("Odoo: URL o base de datos no configurados")
            return False
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self._uid = common.authenticate(
                self.database, self.username, self.api_key, {}
            )
            if self._uid:
                self._models_proxy = xmlrpc.client.ServerProxy(
                    f"{self.url}/xmlrpc/2/object"
                )
                logger.info(f"Odoo: autenticado como UID {self._uid}")
                return True
            logger.error("Odoo: autenticación fallida (UID=0)")
            return False
        except Exception as exc:
            logger.error(f"Odoo: error de autenticación: {exc}")
            return False

    def _execute(self, model: str, method: str, domain: list, fields: list) -> list:
        """Ejecuta una llamada XML-RPC al modelo de Odoo."""
        if not self._uid or not self._models_proxy:
            raise ConnectionError("No autenticado. Llame a test_connection() primero.")
        return self._models_proxy.execute_kw(
            self.database, self._uid, self.api_key,
            model, method,
            [domain],
            {"fields": fields, "limit": 5000},
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=15))
    def fetch_transactions(self, date_from: date, date_to: date) -> list[dict]:
        """
        Obtiene asientos contables (account.move.line) de Odoo en el rango de fechas.

        Args:
            date_from: Fecha inicio.
            date_to: Fecha fin.

        Returns:
            Lista de transacciones normalizadas como dicts.
        """
        self._validate_date_range(date_from, date_to)

        if not self._uid and not self._authenticate():
            raise ConnectionError("No se pudo autenticar con Odoo")

        domain = [
            ("date", ">=", str(date_from)),
            ("date", "<=", str(date_to)),
            ("move_id.state", "=", "posted"),  # Solo asientos confirmados
        ]

        fields = ["id", "date", "debit", "credit", "account_id", "name",
                  "partner_id", "currency_id", "move_id"]

        try:
            lines = self._execute("account.move.line", "search_read", domain, fields)
        except Exception as exc:
            logger.error(f"Odoo: error al obtener account.move.line: {exc}")
            raise

        transactions = []
        for line in lines:
            amount = float(line.get("debit", 0) or line.get("credit", 0))
            if amount == 0:
                continue

            account = line.get("account_id", [None, ""])
            partner = line.get("partner_id", [None, ""])
            currency = line.get("currency_id", [None, "USD"])
            move = line.get("move_id", [None, ""])

            tx = {
                "id": f"ODOO-{line['id']}",
                "date": str(line.get("date", "")),
                "amount": amount,
                "currency": currency[1] if isinstance(currency, list) else "USD",
                "account_debit": str(account[1] if isinstance(account, list) else account),
                "account_credit": str(account[1] if isinstance(account, list) else account),
                "description": str(line.get("name", "") or move[1] if isinstance(move, list) else ""),
                "vendor_id": str(partner[1] if isinstance(partner, list) and partner[0] else ""),
                "source_system": "odoo",
                "raw_data": line,
            }
            transactions.append(tx)

        self._log_fetch_result(len(transactions), date_from, date_to)
        return transactions

    def test_connection(self) -> bool:
        """Verifica la conectividad con Odoo."""
        return self._authenticate()
