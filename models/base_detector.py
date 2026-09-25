import abc
import numpy as np
import joblib

class BaseDetector(abc.ABC):
    """Clase base abstracta para todos los detectores de anomalías."""

    def __init__(self, name: str, threshold_percentile: float = 95.0) -> None:
        self.name = name
        self.threshold_percentile = threshold_percentile
        self.threshold: float = 0.0
        self._is_fitted: bool = False

    @abc.abstractmethod
    def fit(self, X: np.ndarray) -> None:
        """Entrena el modelo con los datos proporcionados."""
        pass

    @abc.abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice si las muestras son anomalías (1) o no (0)."""
        pass

    @abc.abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        """Calcula el score de anomalía para cada muestra."""
        pass

    def partial_fit(self, X: np.ndarray) -> None:
        """Aprendizaje incremental. Por defecto no hace nada."""
        pass

    def set_threshold(self, scores: np.ndarray) -> None:
        """Calcula el threshold basado en el percentil configurado."""
        self.threshold = float(np.percentile(scores, self.threshold_percentile))

    def is_anomaly(self, scores: np.ndarray) -> np.ndarray:
        """Convierte scores a predicciones binarias usando el threshold."""
        return (scores > self.threshold).astype(int)

    @property
    def is_fitted(self) -> bool:
        """Indica si el modelo ha sido entrenado."""
        return self._is_fitted

    def save(self, path: str) -> None:
        """Guarda el modelo en el path especificado."""
        joblib.dump({
            'name': self.name,
            'threshold_percentile': self.threshold_percentile,
            'threshold': self.threshold,
            '_is_fitted': self._is_fitted,
            'model': getattr(self, 'model', None)
        }, path)

    def load(self, path: str) -> 'BaseDetector':
        """Carga el modelo desde el path especificado."""
        data = joblib.load(path)
        self.name = data['name']
        self.threshold_percentile = data['threshold_percentile']
        self.threshold = data['threshold']
        self._is_fitted = data['_is_fitted']
        if 'model' in data and data['model'] is not None:
            self.model = data['model']
        return self
