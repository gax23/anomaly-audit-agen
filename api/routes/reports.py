"""
Rutas de reportes: generación de PDF de auditoría por período.
GET /api/v1/reports/generate
"""
from datetime import datetime, date
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from api.auth import CurrentUser

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.get(
    "/generate",
    summary="Generar reporte PDF de auditoría",
    response_class=FileResponse,
)
async def generate_report(
    _current_user: CurrentUser,
    date_from: date = Query(..., description="Fecha inicio del período (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha fin del período (YYYY-MM-DD)"),
    include_false_positives: bool = Query(False, description="Incluir falsos positivos en el reporte"),
) -> FileResponse:
    """
    Genera un reporte PDF de auditoría para el período indicado.
    Incluye resumen ejecutivo, tabla de anomalías y gráficos.
    """
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from debe ser anterior a date_to",
        )

    try:
        from reports.generator import ReportGenerator
        generator = ReportGenerator()

        pdf_path = await generator.generate(
            date_from=datetime.combine(date_from, datetime.min.time()),
            date_to=datetime.combine(date_to, datetime.max.time()),
            include_false_positives=include_false_positives,
        )

        if not Path(pdf_path).exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al generar el reporte PDF",
            )

        filename = f"auditoria_{date_from}_{date_to}.pdf"
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Módulo de reportes no disponible. Verifique que WeasyPrint está instalado.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando reporte: {type(exc).__name__}",
        )


@router.get(
    "/preview",
    summary="Vista previa de datos del reporte (JSON)",
)
async def preview_report(
    _current_user: CurrentUser,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> dict:
    """Retorna un preview JSON de los datos que incluiría el reporte PDF."""
    return {
        "period": {"from": str(date_from), "to": str(date_to)},
        "summary": {
            "total_transactions": 0,
            "total_anomalies": 0,
            "true_positives": 0,
            "false_positives": 0,
            "open": 0,
            "total_amount_at_risk": 0.0,
        },
        "note": "Conecte la base de datos para ver datos reales",
    }
