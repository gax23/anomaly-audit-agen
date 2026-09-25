from datetime import datetime
from decimal import Decimal
from typing import Optional

class RulesEngine:
    """Motor de reglas de negocio deterministas para detección de anomalías financieras."""
    
    def __init__(self,
                 round_amount_threshold: float = 10_000.0,
                 after_hours_amount_threshold: float = 5_000.0,
                 velocity_spike_limit: int = 5,
                 velocity_window_minutes: int = 60,
                 split_transaction_daily_threshold: float = 50_000.0,
                 new_vendor_amount_threshold: float = 30_000.0) -> None:
        self.round_amount_threshold = round_amount_threshold
        self.after_hours_amount_threshold = after_hours_amount_threshold
        self.velocity_spike_limit = velocity_spike_limit
        self.velocity_window_minutes = velocity_window_minutes
        self.split_transaction_daily_threshold = split_transaction_daily_threshold
        self.new_vendor_amount_threshold = new_vendor_amount_threshold
    
    def evaluate(self, transaction: dict, historical_context: dict) -> list[str]:
        """Evalúa todas las reglas. Retorna lista de nombres de reglas activadas."""
        rules_triggered = []
        for rule_fn in [self._check_round_amount, self._check_after_hours,
                        self._check_velocity_spike, self._check_split_transaction,
                        self._check_new_vendor_large]:
            result = rule_fn(transaction, historical_context)
            if result:
                rules_triggered.append(result)
        return rules_triggered
    
    def _check_round_amount(self, tx: dict, ctx: dict) -> Optional[str]:
        """ROUND_AMOUNT: monto exactamente redondo > umbral."""
        amount = float(tx.get('amount', 0))
        if amount > self.round_amount_threshold:
            if amount % 1000 == 0 or amount % 500 == 0:
                return "ROUND_AMOUNT"
        return None
    
    def _check_after_hours(self, tx: dict, ctx: dict) -> Optional[str]:
        """AFTER_HOURS: transacciones entre 22:00-06:00 o fin de semana con monto > umbral."""
        amount = float(tx.get('amount', 0))
        if amount <= self.after_hours_amount_threshold:
            return None
            
        dt = tx.get('date')
        if not isinstance(dt, datetime):
            return None
            
        if dt.weekday() >= 5:
            return "AFTER_HOURS"
            
        if dt.hour >= 22 or dt.hour < 6:
            return "AFTER_HOURS"
            
        return None
    
    def _check_velocity_spike(self, tx: dict, ctx: dict) -> Optional[str]:
        """VELOCITY_SPIKE: más de N tx del mismo proveedor en 1 hora."""
        count = ctx.get('vendor_transactions_last_hour', 0)
        if count > self.velocity_spike_limit:
            return "VELOCITY_SPIKE"
        return None
    
    def _check_split_transaction(self, tx: dict, ctx: dict) -> Optional[str]:
        """SPLIT_TRANSACTION: suma de tx del mismo proveedor en el día > umbral."""
        daily_total = float(ctx.get('vendor_daily_total', 0))
        amount = float(tx.get('amount', 0))
        if (daily_total + amount) > self.split_transaction_daily_threshold:
            return "SPLIT_TRANSACTION"
        return None
    
    def _check_new_vendor_large(self, tx: dict, ctx: dict) -> Optional[str]:
        """NEW_VENDOR_LARGE: primer pago a proveedor nuevo con monto > umbral."""
        count = ctx.get('vendor_transaction_count', 0)
        amount = float(tx.get('amount', 0))
        if count == 0 and amount > self.new_vendor_amount_threshold:
            return "NEW_VENDOR_LARGE"
        return None
