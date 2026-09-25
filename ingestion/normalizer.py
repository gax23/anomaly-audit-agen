import math
import hashlib
from typing import Any
from ingestion.schema import Transaction, NormalizedTransaction

class TransactionNormalizer:
    """Normaliza transacciones y calcula características para Machine Learning."""
    
    def __init__(self) -> None:
        self.historical_context: dict[str, Any] = {
            "vendor_stats": {},  # id -> {count, avg, m2, var}
            "vendor_anomalies": {}, # id -> count
            "total_anomalies": 0
        }
        
    def _encode_account(self, account: str) -> float:
        """Codifica la cuenta como un float entre 0 y 1 usando hashing."""
        h = hashlib.sha256(account.encode('utf-8')).hexdigest()
        return int(h[:8], 16) / 0xffffffff
        
    def normalize(self, transaction: Transaction, historical_context: dict[str, Any] = None) -> NormalizedTransaction:
        """Normaliza una transacción, calculando sus features."""
        ctx = historical_context if historical_context is not None else self.historical_context
        
        amount_float = float(transaction.amount)
        log_amount = math.log(abs(amount_float) + 1)
        hour_of_day = transaction.date.hour
        day_of_week = transaction.date.weekday()
        is_weekend = day_of_week >= 5
        account_encoded = self._encode_account(transaction.account_debit)
        
        amount_deviation = 0.0
        vendor_risk_score = 0.5
        
        vid = transaction.vendor_id
        if vid and vid in ctx.get("vendor_stats", {}):
            v_stats = ctx["vendor_stats"][vid]
            v_avg = v_stats.get("avg", 0.0)
            v_var = v_stats.get("var", 1.0)
            v_std = math.sqrt(v_var) if v_var > 0 else 1.0
            amount_deviation = (amount_float - v_avg) / v_std
            
            anomalies = ctx.get("vendor_anomalies", {}).get(vid, 0)
            total = ctx.get("total_anomalies", 1)
            vendor_risk_score = min(1.0, (anomalies / total) * 10) if total > 0 else 0.5
            
        return NormalizedTransaction(
            transaction_id=transaction.id,
            date=transaction.date,
            amount=transaction.amount,
            currency=transaction.currency,
            account_debit=transaction.account_debit,
            account_credit=transaction.account_credit,
            description=transaction.description,
            vendor_id=transaction.vendor_id,
            employee_id=transaction.employee_id,
            department=transaction.department,
            source_system=transaction.source_system,
            log_amount=log_amount,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            account_encoded=account_encoded,
            vendor_risk_score=vendor_risk_score,
            amount_deviation=amount_deviation,
            velocity_1h=0,
            velocity_24h=0,
            is_anomaly=None,
            anomaly_score=None
        )

    def normalize_batch(self, transactions: list[Transaction]) -> list[NormalizedTransaction]:
        """Normaliza un lote completo de transacciones."""
        normalized = []
        for tx in transactions:
            norm_tx = self.normalize(tx)
            normalized.append(norm_tx)
            self.update_historical_context(norm_tx)
        return normalized

    def update_historical_context(self, transaction: NormalizedTransaction) -> None:
        """Actualiza el contexto histórico de proveedores en línea (algoritmo de Welford)."""
        vid = transaction.vendor_id
        if not vid:
            return
            
        stats = self.historical_context.setdefault("vendor_stats", {})
        if vid not in stats:
            stats[vid] = {"count": 0, "avg": 0.0, "m2": 0.0, "var": 0.0}
            
        v = stats[vid]
        v["count"] += 1
        amount_val = float(transaction.amount)
        delta = amount_val - v["avg"]
        v["avg"] += delta / v["count"]
        delta2 = amount_val - v["avg"]
        v["m2"] += delta * delta2
        
        if v["count"] > 1:
            v["var"] = v["m2"] / (v["count"] - 1)
