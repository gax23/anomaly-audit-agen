import os
import pandas as pd
from datetime import date
from typing import Any
from connectors.base import BaseConnector

class CSVExcelConnector(BaseConnector):
    """Conector para archivos CSV y Excel."""
    
    REQUIRED_COLUMNS = ['date', 'amount', 'account_debit', 'account_credit', 'description']
    
    def __init__(self, file_path: str, date_column: str = 'date', encoding: str = 'utf-8', **kwargs: Any) -> None:
        super().__init__(source_name="csv_excel", config={"file_path": file_path, "encoding": encoding})
        self.file_path = file_path
        self.date_column = date_column
        self.encoding = encoding
        
    def test_connection(self) -> bool:
        """Verifica que el archivo existe y tiene las columnas mínimas requeridas."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"El archivo {self.file_path} no existe.")
        
        try:
            if self.file_path.endswith('.csv'):
                df = pd.read_csv(self.file_path, nrows=0, encoding=self.encoding)
            elif self.file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(self.file_path, nrows=0)
            else:
                raise ValueError("Formato no soportado. Debe ser CSV o Excel.")
            
            missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing:
                raise ValueError(f"Columnas faltantes requeridas: {missing}")
                
            return True
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise e
            print(f"Error al probar la conexión: {e}")
            return False

    def fetch_transactions(self, date_from: date, date_to: date) -> list[dict]:
        """Obtiene transacciones filtradas por el rango de fechas, validando la estructura."""
        self._validate_date_range(date_from, date_to)
        
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"El archivo {self.file_path} no existe.")
            
        if self.file_path.endswith('.csv'):
            df = pd.read_csv(self.file_path, encoding=self.encoding)
        elif self.file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(self.file_path)
        else:
            raise ValueError("Formato no soportado.")
            
        # Validar columnas
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes requeridas: {missing}")
            
        # Parse dates auto-detectando formato
        df[self.date_column] = pd.to_datetime(df[self.date_column], format='mixed')
        
        # Filtro por rango de fechas
        mask = (df[self.date_column].dt.date >= date_from) & (df[self.date_column].dt.date <= date_to)
        df_filtered = df.loc[mask].copy()
        
        # Convertir fechas a strings ISO para el retorno
        df_filtered[self.date_column] = df_filtered[self.date_column].astype(str)
        
        records = df_filtered.to_dict(orient='records')
        self._log_fetch_result(len(records), date_from, date_to)
        return records
