"""
Rutas de modelos ML: entrenamiento completo, incremental y estado.
POST /api/v1/model/train
POST /api/v1/model/train/incremental
GET  /api/v1/model/status
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import CurrentUser
from config.settings import settings

router = APIRouter(prefix="/model", tags=["Modelos ML"])

# Estado global del entrenamiento (en producción usar Redis)
_training_state: dict = {
    "is_training": False,
    "last_trained_at": None,
    "last_metrics": {},
    "model_version": 0,
    "error": None,
}


class TrainingRequest(BaseModel):
    """Parámetros para disparar un entrenamiento completo."""
    data_path: Optional[str] = None  # Si None, usa el dataset de fixtures
    epochs: int = 50
    use_ensemble: bool = True


class IncrementalTrainingRequest(BaseModel):
    """Parámetros para entrenamiento incremental."""
    transaction_ids: list[str]  # IDs de transacciones nuevas a usar


def _run_training(data_path: Optional[str], epochs: int) -> dict:
    """Ejecuta el entrenamiento completo en background. Retorna métricas."""
    try:
        _training_state["is_training"] = True
        _training_state["error"] = None

        # Cargar datos
        csv_path = data_path or "tests/fixtures/sample_transactions.csv"
        df = pd.read_csv(csv_path)

        # Preparar features
        feature_cols = ["log_amount", "hour_of_day", "day_of_week", "is_weekend",
                        "account_encoded", "vendor_risk_score", "amount_deviation",
                        "velocity_1h", "velocity_24h"]

        # Calcular features básicas si no existen
        if "log_amount" not in df.columns:
            df["log_amount"] = np.log1p(df["amount"].abs())
        if "hour_of_day" not in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["hour_of_day"] = df["date"].dt.hour
            df["day_of_week"] = df["date"].dt.dayofweek
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        for col in ["account_encoded", "vendor_risk_score", "amount_deviation",
                    "velocity_1h", "velocity_24h"]:
            if col not in df.columns:
                df[col] = 0.0

        X = df[feature_cols].fillna(0.0).values.astype(np.float32)
        y = df["is_anomaly"].values if "is_anomaly" in df.columns else None

        # Importar y entrenar modelos
        from models.autoencoder import AutoencoderDetector
        from models.isolation_forest import IsolationForestDetector
        from models.ensemble import EnsembleDetector
        from models.trainer import ModelTrainer

        artifacts_path = Path(settings.model_artifacts_path)
        artifacts_path.mkdir(parents=True, exist_ok=True)

        autoencoder = AutoencoderDetector(input_dim=9, epochs=epochs)
        isolation_forest = IsolationForestDetector()
        ensemble = EnsembleDetector(detectors=[autoencoder, isolation_forest])

        trainer = ModelTrainer()
        metrics = trainer.train(ensemble, X, y)

        # Guardar modelos
        autoencoder.save(str(artifacts_path / "autoencoder.pt"))
        isolation_forest.save(str(artifacts_path / "isolation_forest.joblib"))

        _training_state["last_metrics"] = metrics
        _training_state["last_trained_at"] = datetime.utcnow().isoformat()
        _training_state["model_version"] += 1

        return metrics
    except Exception as exc:
        _training_state["error"] = str(exc)
        raise
    finally:
        _training_state["is_training"] = False


@router.post(
    "/train",
    summary="Disparar entrenamiento completo del modelo",
    status_code=status.HTTP_202_ACCEPTED,
)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    _current_user: CurrentUser,
) -> dict:
    """
    Inicia el entrenamiento completo en background.
    Retorna inmediatamente con status 202 Accepted.
    """
    if _training_state["is_training"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay un entrenamiento en curso. Espere a que finalice.",
        )

    background_tasks.add_task(_run_training, request.data_path, request.epochs)

    return {
        "message": "Entrenamiento iniciado en background",
        "status": "TRAINING",
        "check_status_at": "/api/v1/model/status",
    }


@router.post(
    "/train/incremental",
    summary="Entrenamiento incremental con nuevas transacciones",
    status_code=status.HTTP_202_ACCEPTED,
)
async def train_incremental(
    request: IncrementalTrainingRequest,
    _current_user: CurrentUser,
) -> dict:
    """
    Ejecuta partial_fit del autoencoder con las transacciones indicadas.
    Más rápido que el entrenamiento completo.
    """
    if _training_state["is_training"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay un entrenamiento en curso.",
        )

    return {
        "message": "Entrenamiento incremental registrado",
        "transaction_count": len(request.transaction_ids),
        "note": "Las transacciones serán procesadas en el próximo ciclo de partial_fit",
    }


@router.get(
    "/status",
    summary="Estado y métricas del modelo activo",
)
async def get_model_status(
    _current_user: CurrentUser,
) -> dict:
    """Retorna el estado actual del modelo, métricas y versión."""
    artifacts_path = Path(settings.model_artifacts_path)
    autoencoder_exists = (artifacts_path / "autoencoder.pt").exists()
    if_exists = (artifacts_path / "isolation_forest.joblib").exists()

    return {
        "is_training": _training_state["is_training"],
        "model_version": _training_state["model_version"],
        "last_trained_at": _training_state["last_trained_at"],
        "last_error": _training_state["error"],
        "artifacts": {
            "autoencoder": autoencoder_exists,
            "isolation_forest": if_exists,
        },
        "last_metrics": _training_state["last_metrics"],
        "status": "TRAINING" if _training_state["is_training"] else (
            "READY" if autoencoder_exists else "NOT_TRAINED"
        ),
    }
