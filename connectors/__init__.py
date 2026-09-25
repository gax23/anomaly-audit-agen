"""Módulo de conectores a fuentes de datos ERP y archivos."""
from connectors.base import BaseConnector
from connectors.csv_excel import CSVExcelConnector
from connectors.sap_b1 import SAPB1Connector
from connectors.quickbooks import QuickBooksConnector
from connectors.odoo import OdooConnector

__all__ = ["BaseConnector", "CSVExcelConnector", "SAPB1Connector", "QuickBooksConnector", "OdooConnector"]

