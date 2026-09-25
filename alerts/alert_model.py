from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(str, Enum):
    OPEN = "OPEN"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    TRUE_POSITIVE = "TRUE_POSITIVE"
    UNDER_REVIEW = "UNDER_REVIEW"

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    severity: AlertSeverity
    anomaly_score: float  # 0.0 a 1.0
    rules_triggered: list[str] = Field(default_factory=list)
    ml_score: Optional[float] = None
    narrative: Optional[str] = None
    shap_plot_path: Optional[str] = None
    status: AlertStatus = AlertStatus.OPEN
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    @property
    def is_open(self) -> bool:
        return self.status == AlertStatus.OPEN
    
    def to_dict_safe(self) -> dict:
        """Serializa la alerta sin datos sensibles para logging."""
        tx_id_safe = f"***{self.transaction_id[-4:]}" if self.transaction_id and len(self.transaction_id) > 4 else "***"
        
        return {
            "id": self.id,
            "transaction_id_masked": tx_id_safe,
            "severity": self.severity.value,
            "anomaly_score": self.anomaly_score,
            "rules_triggered": self.rules_triggered,
            "status": self.status.value,
            "created_at": self.created_at.isoformat()
        }
