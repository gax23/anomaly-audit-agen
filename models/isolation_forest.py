import numpy as np
import joblib
from typing import List, Optional
from sklearn.ensemble import IsolationForest
from models.base_detector import BaseDetector

class IsolationForestDetector(BaseDetector):
    """Detector de anomalías usando Isolation Forest de scikit-learn."""
    
    def __init__(self, n_estimators: int = 200, contamination: float = 0.05, 
                 random_state: int = 42, threshold_percentile: float = 95.0) -> None:
        super().__init__(name="IsolationForest", threshold_percentile=threshold_percentile)
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            n_estimators=n_estimators, 
            contamination=contamination,
            random_state=random_state
        )
        self.buffer: List[np.ndarray] = []
        self._fitted_data: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray) -> None:
        """Entrena el modelo de Isolation Forest."""
        self.model.fit(X)
        self._fitted_data = X.copy()
        self._is_fitted = True
        scores = self.score(X)
        self.set_threshold(scores)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Calcula el score de anomalía (invierte el score negativo de sklearn)."""
        raw_scores = -self.model.score_samples(X)
        
        min_score = -0.5  
        max_score = 0.5   
        
        normalized = (raw_scores - min_score) / (max_score - min_score)
        return np.clip(normalized, 0, 1)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice si las muestras son anomalías (1) o normales (0)."""
        if not self.is_fitted:
            raise RuntimeError("El modelo no está entrenado.")
        scores = self.score(X)
        return self.is_anomaly(scores)

    def partial_fit(self, X: np.ndarray) -> None:
        """Re-entrena con todos los datos acumulados (guarda buffer interno)."""
        self.buffer.append(X)
        if self._fitted_data is not None:
            all_data = np.vstack([self._fitted_data] + self.buffer)
        else:
            all_data = np.vstack(self.buffer)
            
        self.fit(all_data)
        
    def save(self, path: str) -> None:
        """Guarda el modelo con joblib."""
        super().save(path)
        
    def load(self, path: str) -> 'IsolationForestDetector':
        """Carga el modelo con joblib."""
        return super().load(path)
