import datetime
from typing import Any

class NarrativeGenerator:
    """Generador de narrativas explicativas para alertas de anomalías."""

    def __init__(self) -> None:
        pass

    def generate(self, transaction: dict, anomaly_score: float, top_factors: list[dict], rules_triggered: list[str]) -> str:
        """Genera una explicación en lenguaje natural sobre por qué una transacción es anómala."""
        
        # Determinar severidad
        if anomaly_score < 0.6:
            severidad = "BAJA"
            recomendacion_segun_severidad = "Monitorear"
        elif anomaly_score <= 0.8:
            severidad = "MEDIA"
            recomendacion_segun_severidad = "Requiere revisión por auditor"
        else:
            severidad = "ALTA"
            recomendacion_segun_severidad = "Requiere revisión urgente"

        # Formatear fecha a español
        if 'date' in transaction and isinstance(transaction['date'], datetime.datetime):
            dt = transaction['date']
        else:
            dt = datetime.datetime.now()
            
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", 
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_formateada_español = f"{dt.day} de {meses[dt.month]} de {dt.year}, {dt.strftime('%H:%M')}"

        # Extraer datos de la transacción
        tx_id = transaction.get('id', 'N/A')
        monto = float(transaction.get('amount', 0.0))
        moneda = transaction.get('currency', 'USD')
        account_debit = transaction.get('account', 'N/A')
        vendor_id = transaction.get('vendor', 'N/A')

        # Construir bullets
        bullets = []
        for factor in top_factors:
            f_name = factor.get('feature', '')
            if f_name == 'log_amount':
                bullets.append("- El monto supera el promedio histórico de este proveedor")
            elif f_name == 'hour_of_day':
                bullets.append(f"- Ocurrió a las {dt.strftime('%H:%M')} (fuera del horario habitual de negocio)")
            elif f_name == 'velocity_1h':
                bullets.append("- Detectamos múltiples transacciones del mismo proveedor en las últimas 1 horas")
            elif f_name == 'velocity_24h':
                bullets.append("- Detectamos múltiples transacciones del mismo proveedor en las últimas 24 horas")
            elif f_name == 'is_weekend':
                bullets.append("- Ocurrió en fin de semana")
            else:
                bullets.append(f"- Factor relevante: {f_name}")
                
        for regla in rules_triggered:
            bullets.append(f"- Regla activada: {regla}")

        if not bullets:
            bullets_str = "- Anomalía detectada sin factores prominentes"
        else:
            bullets_str = "\n".join(bullets)

        template = f"""⚠️ ANOMALÍA DETECTADA — Score: {anomaly_score:.2f}/1.0 ({severidad} SEVERIDAD)

Transacción: {tx_id}
Fecha: {fecha_formateada_español}
Monto: ${monto:,.2f} {moneda}
Cuenta débito: {account_debit}
Proveedor: {vendor_id}

¿Por qué fue marcada?
{bullets_str}

Recomendación: {recomendacion_segun_severidad}"""

        return template
