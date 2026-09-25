import numpy as np
import joblib
from typing import List, Optional
from models.base_detector import BaseDetector
from sklearn.svm import OneClassSVM

class EnsembleDetector(BaseDetector):
    """Ensemble de múltiples detectores de anomalías."""
    
    def __init__(self, detectors: list[BaseDetector], weights: list[float] | None = None,
                 threshold_percentile: float = 95.0) -> None:
        super().__init__(name="EnsembleDetector", threshold_percentile=threshold_percentile)
        self.detectors = detectors
        if weights is None:
            self.weights = [1.0 / len(detectors)] * len(detectors)
        else:
            if len(weights) != len(detectors):
                raise ValueError("El número de pesos debe coincidir con el de detectores.")
            total = sum(weights)
            self.weights = [w / total for w in weights]

    def fit(self, X: np.ndarray) -> None:
        """Entrena todos los detectores."""
        for detector in self.detectors:
            detector.fit(X)
        
        self._is_fitted = True
        scores = self.score(X)
        self.set_threshold(scores)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Calcula el promedio ponderado de los scores de todos los detectores."""
        ensemble_scores = np.zeros(X.shape[0])
        
        for detector, weight in zip(self.detectors, self.weights):
            if not detector.is_fitted:
                raise RuntimeError(f"Detector {detector.name} no está entrenado.")
            scores = detector.score(X)
            min_s, max_s = np.min(scores), np.max(scores)
            if max_s > min_s:
                norm_scores = (scores - min_s) / (max_s - min_s)
            else:
                norm_scores = np.zeros_like(scores)
                
            ensemble_scores += norm_scores * weight
            
        return ensemble_scores

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice usando el ensemble basado en el score > threshold."""
        if not self.is_fitted:
            raise RuntimeError("El modelo no está entrenado.")
        scores = self.score(X)
        return self.is_anomaly(scores)

    def partial_fit(self, X: np.ndarray) -> None:
        """Llama partial_fit de cada detector."""
        for detector in self.detectors:
            detector.partial_fit(X)
            
    def save(self, path: str) -> None:
        """Guarda el ensemble usando joblib."""
        state = {
            'weights': self.weights,
            'threshold': self.threshold,
            'threshold_percentile': self.threshold_percentile,
            '_is_fitted': self._is_fitted
        }
        joblib.dump({'state': state, 'detectors': self.detectors}, path)
        
    def load(self, path: str) -> 'EnsembleDetector':
        """Carga el ensemble usando joblib."""
        data = joblib.load(path)
        self.detectors = data['detectors']
        state = data['state']
        self.weights = state['weights']
        self.threshold = state['threshold']
        self.threshold_percentile = state['threshold_percentile']
        self._is_fitted = state['_is_fitted']
        return self
