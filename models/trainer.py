import numpy as np
import time
from typing import Dict, List, Optional, Any
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from loguru import logger
from models.base_detector import BaseDetector

class ModelTrainer:
    """Clase para entrenar, evaluar y preparar características para los modelos."""
    
    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self._is_scaler_fitted = False
        
    def prepare_features(self, transactions: list[dict], is_training: bool = False) -> np.ndarray:
        """Extrae y escala las 9 características necesarias."""
        features = []
        for t in transactions:
            row = [
                float(t.get('log_amount', 0.0)),
                float(t.get('hour_of_day', 0.0)),
                float(t.get('day_of_week', 0.0)),
                float(t.get('is_weekend', 0.0)),
                float(t.get('account_encoded', 0.0)),
                float(t.get('vendor_risk_score', 0.0)),
                float(t.get('amount_deviation', 0.0)),
                float(t.get('velocity_1h', 0.0)),
                float(t.get('velocity_24h', 0.0))
            ]
            features.append(row)
            
        X = np.array(features)
        
        if is_training:
            X_scaled = self.scaler.fit_transform(X)
            self._is_scaler_fitted = True
        else:
            if not self._is_scaler_fitted:
                logger.warning("Scaler no está entrenado. Retornando datos sin escalar.")
                return X
            X_scaled = self.scaler.transform(X)
            
        return X_scaled

    def train(self, detector: BaseDetector, X: np.ndarray, y: np.ndarray | None = None) -> dict[str, float]:
        """Entrena el modelo usando validación cruzada temporal si y está presente. Retorna las métricas de entrenamiento."""
        logger.info(f"Entrenando modelo: {detector.name}")
        start_time = time.time()
        
        if y is None or len(np.unique(y)) < 2:
            detector.fit(X)
            train_time = time.time() - start_time
            logger.info("Entrenamiento sin etiquetas completado.")
            return {"train_time_seconds": train_time}
            
        tscv = TimeSeriesSplit(n_splits=5)
        metrics = {"auc_roc": [], "precision": [], "recall": [], "f1": []}
        
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X[train_index], X[test_index]
            y_test = y[test_index]
            
            if len(np.unique(y_test)) < 2:
                continue
                
            detector.fit(X_train)
            
            preds = detector.predict(X_test)
            scores = detector.score(X_test)
            
            metrics["auc_roc"].append(roc_auc_score(y_test, scores))
            metrics["precision"].append(precision_score(y_test, preds, zero_division=0))
            metrics["recall"].append(recall_score(y_test, preds, zero_division=0))
            metrics["f1"].append(f1_score(y_test, preds, zero_division=0))
            
        avg_metrics = {k: float(np.mean(v)) if v else 0.0 for k, v in metrics.items()}
        
        detector.fit(X)
        avg_metrics["train_time_seconds"] = time.time() - start_time
        
        logger.info(f"Métricas CV finalizadas: {avg_metrics}")
        return avg_metrics

    def evaluate(self, detector: BaseDetector, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Evalúa un detector ya entrenado y calcula métricas."""
        if not detector.is_fitted:
            raise RuntimeError("El modelo debe estar entrenado para ser evaluado.")
            
        preds = detector.predict(X)
        scores = detector.score(X)
        
        metrics = {
            "auc_roc": float(roc_auc_score(y, scores)) if len(np.unique(y)) > 1 else 0.0,
            "precision": float(precision_score(y, preds, zero_division=0)),
            "recall": float(recall_score(y, preds, zero_division=0)),
            "f1": float(f1_score(y, preds, zero_division=0))
        }
        
        return metrics
