"""
Generador de reportes PDF de auditoría financiera.
Usa Jinja2 para renderizar el template HTML y WeasyPrint para convertir a PDF.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from loguru import logger


class ReportGenerator:
    """Orquesta la generación de reportes PDF de auditoría."""

    def __init__(self) -> None:
        """Inicializa el generador con el entorno Jinja2 y rutas de salida."""
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        self.output_dir = Path("reports") / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        date_from: datetime,
        date_to: datetime,
        anomalies: Optional[list[dict]] = None,
        stats: Optional[dict] = None,
        company_name: str = "Empresa Auditada",
        include_false_positives: bool = False,
    ) -> str:
        """
        Genera el reporte PDF completo y lo guarda en disco.

        Args:
            date_from: Fecha inicio del período auditado.
            date_to: Fecha fin del período auditado.
            anomalies: Lista de anomalías a incluir. Si None, usa datos de ejemplo.
            stats: Estadísticas del período. Si None, se calculan desde anomalies.
            company_name: Nombre de la empresa auditada.
            include_false_positives: Si True, incluye FP en el reporte.

        Returns:
            Ruta absoluta del archivo PDF generado.
        """
        # Usar datos de ejemplo si no se proporcionan
        if anomalies is None:
            anomalies = self._get_sample_anomalies()

        # Filtrar falsos positivos si no se requieren
        if not include_false_positives:
            anomalies = [a for a in anomalies if a.get("status") != "FALSE_POSITIVE"]

        # Calcular estadísticas si no se proporcionan
        if stats is None:
            stats = self._calculate_stats(anomalies)

        # Separar anomalías de alta severidad para detalle
        high_severity = [
            a for a in anomalies
            if a.get("severity") in ("HIGH", "CRITICAL")
        ]

        # Preparar contexto del template
        context = {
            "company_name": company_name,
            "period_from": date_from.strftime("%d de %B de %Y"),
            "period_to": date_to.strftime("%d de %B de %Y"),
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "anomalies": anomalies[:500],  # Limitar para evitar PDFs demasiado grandes
            "high_severity_anomalies": high_severity[:50],
            "stats": stats,
        }

        # Renderizar HTML
        template = self.jinja_env.get_template("audit_report.html")
        html_content = template.render(**context)

        # Generar nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        period_str = f"{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}"
        output_path = self.output_dir / f"auditoria_{period_str}_{timestamp}.pdf"

        # Convertir HTML a PDF con WeasyPrint
        try:
            from weasyprint import HTML, CSS
            HTML(string=html_content, base_url=str(Path(__file__).parent)).write_pdf(
                str(output_path)
            )
            logger.info(f"Reporte PDF generado: {output_path}")
        except ImportError:
            # Fallback: guardar como HTML si WeasyPrint no está disponible
            html_path = output_path.with_suffix(".html")
            html_path.write_text(html_content, encoding="utf-8")
            logger.warning(
                f"WeasyPrint no disponible. Reporte guardado como HTML: {html_path}"
            )
            return str(html_path)

        return str(output_path)

    def _calculate_stats(self, anomalies: list[dict]) -> dict:
        """Calcula estadísticas agregadas de las anomalías."""
        total = len(anomalies)
        open_count = sum(1 for a in anomalies if a.get("status") == "OPEN")
        tp_count = sum(1 for a in anomalies if a.get("status") == "TRUE_POSITIVE")
        fp_count = sum(1 for a in anomalies if a.get("status") == "FALSE_POSITIVE")
        critical = sum(1 for a in anomalies if a.get("severity") == "CRITICAL")
        high = sum(1 for a in anomalies if a.get("severity") == "HIGH")

        fp_rate = f"{(fp_count / max(tp_count + fp_count, 1) * 100):.1f}%" if (tp_count + fp_count) > 0 else "N/A"

        return {
            "total_transactions": 10000,  # En producción: consultar BD
            "total_anomalies": total,
            "open_anomalies": open_count,
            "true_positives": tp_count,
            "false_positives": fp_count,
            "critical_count": critical,
            "high_count": high,
            "false_positive_rate": fp_rate,
        }

    def _get_sample_anomalies(self) -> list[dict]:
        """Carga anomalías de muestra desde el CSV de fixtures para demostración."""
        csv_path = Path("tests") / "fixtures" / "sample_transactions.csv"
        if not csv_path.exists():
            return []
        try:
            import pandas as pd
            import numpy as np
            df = pd.read_csv(csv_path)
            anomalies_df = df[df["is_anomaly"] == 1].head(100).copy()
            anomalies_df["anomaly_score"] = np.random.uniform(0.6, 0.99, len(anomalies_df))
            anomalies_df["severity"] = pd.cut(
                anomalies_df["anomaly_score"],
                bins=[0, 0.6, 0.75, 0.9, 1.0],
                labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            ).astype(str)
            anomalies_df["status"] = "OPEN"
            anomalies_df["rules_triggered"] = [[] for _ in range(len(anomalies_df))]
            anomalies_df["narrative"] = None
            return anomalies_df.to_dict("records")
        except Exception as exc:
            logger.warning(f"No se pudieron cargar anomalías de muestra: {exc}")
            return []
