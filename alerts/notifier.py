import os
import smtplib
from email.message import EmailMessage
import httpx
import asyncio
from typing import Optional

from alerts.alert_model import Alert

class AlertNotifier:
    """Notificador de alertas a través de múltiples canales."""
    
    def __init__(self) -> None:
        pass
        
    async def send_email(self, alert: Alert, to_email: str) -> bool:
        """Envía un email con los detalles de la alerta."""
        try:
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "25"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_pass = os.getenv("SMTP_PASS", "")
            from_email = os.getenv("SMTP_FROM", "alerts@anomaly-audit.local")
            
            msg = EmailMessage()
            msg.set_content(alert.narrative or "Alerta sin narrativa.")
            msg['Subject'] = f"[ALERTA {alert.severity.value}] Anomalía detectada - {alert.transaction_id}"
            msg['From'] = from_email
            msg['To'] = to_email
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                self._sync_send_email,
                smtp_host, smtp_port, smtp_user, smtp_pass, msg
            )
            return True
        except Exception as e:
            return False
            
    def _sync_send_email(self, host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
        """Función síncrona para envío de emails."""
        with smtplib.SMTP(host, port) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)

    async def send_webhook(self, alert: Alert, webhook_url: str) -> bool:
        """Envía los datos de la alerta a un webhook HTTP POST."""
        try:
            payload = {
                "alert_id": alert.id,
                "severity": alert.severity.value,
                "score": alert.anomaly_score,
                "rules": alert.rules_triggered
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            return True
        except Exception as e:
            return False

    def notify(self, alert: Alert) -> None:
        """Notifica por canales configurados gestionando el ciclo de eventos."""
        to_email = os.getenv("ALERT_EMAIL_TO")
        webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        
        if not to_email and not webhook_url:
            return
            
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            tasks = []
            if to_email:
                tasks.append(self.send_email(alert, to_email))
            if webhook_url:
                tasks.append(self.send_webhook(alert, webhook_url))
                
            if tasks:
                if loop.is_running():
                    for t in tasks:
                        asyncio.create_task(t)
                else:
                    loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:
            pass
