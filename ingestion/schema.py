from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Any
from decimal import Decimal
import uuid

class Transaction(BaseModel):
    """Modelo de transacción en formato nativo de la fuente de datos."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime
    amount: Decimal
    currency: str = "USD"
    account_debit: str
    account_credit: str
    description: str
    vendor_id: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    source_system: str  # "sap_b1" | "quickbooks" | "odoo" | "csv"
    raw_data: dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        """Valida que el monto de la transacción sea estrictamente positivo."""
        if v <= 0:
            raise ValueError("El monto debe ser estrictamente positivo.")
        return v
    
    @field_validator('currency')
    @classmethod  
    def currency_must_be_valid(cls, v: str) -> str:
        """Valida que la moneda tenga longitud válida."""
        if len(v) != 3:
            raise ValueError("El código de moneda debe tener 3 caracteres.")
        return v.upper()

class JournalEntry(BaseModel):
    """Entrada de diario contable."""
    entry_id: str
    date: datetime
    reference: str
    lines: list[Transaction]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool = False
    
    def validate_balance(self) -> bool:
        """Valida si los débitos son iguales a los créditos."""
        self.is_balanced = (self.total_debit == self.total_credit)
        return self.is_balanced

class NormalizedTransaction(BaseModel):
    """Transacción normalizada con features de ML pre-calculadas."""
    # Campos base de Transaction
    transaction_id: str
    date: datetime
    amount: Decimal
    currency: str
    account_debit: str
    account_credit: str
    description: str
    vendor_id: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    source_system: str
    
    # Features de ML
    log_amount: float
    hour_of_day: int
    day_of_week: int
    is_weekend: bool
    account_encoded: float
    vendor_risk_score: float = 0.5
    amount_deviation: float = 0.0
    velocity_1h: int = 0
    velocity_24h: int = 0
    
    # Metadata
    is_anomaly: Optional[bool] = None  # Para datos etiquetados
    anomaly_score: Optional[float] = None
