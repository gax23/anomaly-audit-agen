"""
Rutas de transacciones: ingesta individual, batch y desde CSV.
Endpoint: POST /api/v1/transactions/ingest
Endpoint: POST /api/v1/transactions/ingest/csv
Endpoint: GET  /api/v1/transactions
"""
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import CurrentUser
from database.connection import get_db
from database.repositories.transaction_repo import TransactionRepository
from ingestion.schema import Transaction
from ingestion.normalizer import TransactionNormalizer

router = APIRouter(prefix="/transactions", tags=["Transacciones"])
_repo = TransactionRepository()
_normalizer = TransactionNormalizer()


class TransactionIngesta(BaseModel):
    """Payload para ingesta individual o batch de transacciones."""
    transactions: list[dict] = Field(..., min_length=1, max_length=1000)
    source_system: str = Field(default="api", pattern="^(api|csv|sap_b1|quickbooks|odoo)$")


class TransactionResponse(BaseModel):
    """Respuesta de ingesta de transacciones."""
    processed: int
    errors: int
    transaction_ids: list[str]
    message: str


@router.post(
    "/ingest",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestar transacciones (JSON)",
)
async def ingest_transactions(
    payload: TransactionIngesta,
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Ingesta transacciones individuales o en batch desde JSON."""
    processed, errors, ids = 0, 0, []

    for tx_data in payload.transactions:
        try:
            tx_data["source_system"] = payload.source_system
            tx = Transaction(**tx_data)
            normalized = _normalizer.normalize(tx, {})
            tx_dict = normalized.model_dump()
            tx_dict["id"] = normalized.transaction_id
            saved = await _repo.create(db, tx_dict)
            ids.append(saved.id)
            processed += 1
        except Exception as exc:
            logger.warning(f"Error procesando transacción: {type(exc).__name__}")
            errors += 1

    return TransactionResponse(
        processed=processed,
        errors=errors,
        transaction_ids=ids,
        message=f"Procesadas {processed} transacciones, {errors} errores.",
    )


@router.post(
    "/ingest/csv",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestar transacciones desde archivo CSV",
)
async def ingest_csv(
    _current_user: CurrentUser,
    file: UploadFile = File(..., description="Archivo CSV con transacciones"),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Ingesta transacciones desde un archivo CSV subido directamente."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se aceptan archivos .csv",
        )

    import pandas as pd

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al parsear CSV: {exc}",
        )

    required_cols = {"date", "amount", "account_debit", "account_credit", "description"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Columnas faltantes en CSV: {missing}",
        )

    processed, errors, ids = 0, 0, []
    for _, row in df.iterrows():
        try:
            row_dict = row.where(row.notna(), None).to_dict()
            row_dict["source_system"] = "csv"
            tx = Transaction(**row_dict)
            normalized = _normalizer.normalize(tx, {})
            tx_dict = normalized.model_dump()
            tx_dict["id"] = normalized.transaction_id
            saved = await _repo.create(db, tx_dict)
            ids.append(saved.id)
            processed += 1
        except Exception as exc:
            logger.warning(f"Error en fila CSV: {type(exc).__name__}")
            errors += 1

    return TransactionResponse(
        processed=processed,
        errors=errors,
        transaction_ids=ids,
        message=f"CSV procesado: {processed} transacciones, {errors} errores.",
    )


@router.get(
    "",
    summary="Listar transacciones con filtros",
)
async def list_transactions(
    _current_user: CurrentUser,
    date_from: Optional[datetime] = Query(None, description="Fecha inicio (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Fecha fin (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lista transacciones con filtros opcionales de fecha y paginación."""
    date_from = date_from or datetime(2000, 1, 1)
    date_to = date_to or datetime(2100, 1, 1)
    transactions = await _repo.get_by_date_range(db, date_from, date_to, limit, offset)
    return {
        "total": len(transactions),
        "limit": limit,
        "offset": offset,
        "data": [{"id": t.id, "date": t.date, "source_system": t.source_system,
                  "department": t.department, "currency": t.currency} for t in transactions],
    }
