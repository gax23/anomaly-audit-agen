"""
Rutas de anomalías: listado paginado, detalle, explicación SHAP y feedback de auditor.
GET  /api/v1/anomalies
GET  /api/v1/anomalies/{id}
GET  /api/v1/anomalies/{id}/explain
POST /api/v1/anomalies/{id}/feedback
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import CurrentUser
from database.connection import get_db
from database.repositories.anomaly_repo import AnomalyRepository

router = APIRouter(prefix="/anomalies", tags=["Anomalías"])
_repo = AnomalyRepository()


class FeedbackPayload(BaseModel):
    """Payload para marcar el resultado de una anomalía como TP/FP."""
    status: str  # "TRUE_POSITIVE" | "FALSE_POSITIVE" | "UNDER_REVIEW"
    reviewer_id: str
    notes: Optional[str] = None


@router.get(
    "",
    summary="Listar anomalías detectadas con filtros",
)
async def list_anomalies(
    _current_user: CurrentUser,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    status_filter: Optional[str] = Query(None, alias="status",
                                         pattern="^(OPEN|TRUE_POSITIVE|FALSE_POSITIVE|UNDER_REVIEW)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Lista anomalías detectadas con filtros opcionales.
    Retorna lista paginada con metadata de paginación.
    """
    anomalies, total = await _repo.get_paginated(
        db,
        page=page,
        page_size=page_size,
        severity=severity,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "data": [
            {
                "id": a.id,
                "transaction_id": a.transaction_id[:8] + "***",  # Enmascarar parcialmente
                "detected_at": a.detected_at,
                "anomaly_score": a.anomaly_score,
                "severity": a.severity,
                "rules_triggered": a.rules_triggered,
                "status": a.status,
            }
            for a in anomalies
        ],
    }


@router.get(
    "/{anomaly_id}",
    summary="Obtener detalle de una anomalía",
)
async def get_anomaly(
    anomaly_id: str,
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna el detalle completo de una anomalía por su ID."""
    anomaly = await _repo.get_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomalía {anomaly_id} no encontrada",
        )

    return {
        "id": anomaly.id,
        "transaction_id": anomaly.transaction_id,
        "detected_at": anomaly.detected_at,
        "anomaly_score": anomaly.anomaly_score,
        "severity": anomaly.severity,
        "rules_triggered": anomaly.rules_triggered,
        "ml_score": anomaly.ml_score,
        "narrative": anomaly.narrative,
        "shap_plot_path": anomaly.shap_plot_path,
        "status": anomaly.status,
        "reviewer_id": anomaly.reviewer_id,
        "reviewer_notes": anomaly.reviewer_notes,
        "reviewed_at": anomaly.reviewed_at,
    }


@router.get(
    "/{anomaly_id}/explain",
    summary="Obtener explicación SHAP + narrativa para una anomalía",
)
async def explain_anomaly(
    anomaly_id: str,
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Retorna la explicación completa de una anomalía:
    - SHAP values por feature
    - Texto narrativo en español
    - Ruta al waterfall plot PNG
    """
    anomaly = await _repo.get_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomalía {anomaly_id} no encontrada",
        )

    return {
        "anomaly_id": anomaly.id,
        "anomaly_score": anomaly.anomaly_score,
        "severity": anomaly.severity,
        "narrative": anomaly.narrative or "Explicación no disponible. Re-ejecute la detección.",
        "shap_values": anomaly.shap_values or {},
        "shap_plot_url": f"/static/plots/{anomaly.id}.png" if anomaly.shap_plot_path else None,
        "rules_triggered": anomaly.rules_triggered,
        "feature_names": [
            "log_amount", "hour_of_day", "day_of_week", "is_weekend",
            "account_encoded", "vendor_risk_score", "amount_deviation",
            "velocity_1h", "velocity_24h",
        ],
    }


@router.post(
    "/{anomaly_id}/feedback",
    summary="Registrar feedback del auditor (TP/FP)",
)
async def submit_feedback(
    anomaly_id: str,
    payload: FeedbackPayload,
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Permite al auditor marcar una anomalía como Verdadero Positivo (TP)
    o Falso Positivo (FP) para mejorar el modelo con aprendizaje incremental.
    """
    valid_statuses = {"TRUE_POSITIVE", "FALSE_POSITIVE", "UNDER_REVIEW"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Valores permitidos: {valid_statuses}",
        )

    updated = await _repo.update_status(
        db,
        anomaly_id=anomaly_id,
        status=payload.status,
        reviewer_id=payload.reviewer_id,
        notes=payload.notes or "",
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomalía {anomaly_id} no encontrada",
        )

    return {
        "message": "Feedback registrado exitosamente",
        "anomaly_id": anomaly_id,
        "new_status": payload.status,
        "reviewer_id": payload.reviewer_id,
    }
