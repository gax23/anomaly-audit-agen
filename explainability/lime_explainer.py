import numpy as np
from typing import Any, Callable

try:
    from lime.lime_tabular import LimeTabularExplainer
except ImportError:
    LimeTabularExplainer = None

FEATURE_NAMES = [
    'log_amount', 'hour_of_day', 'day_of_week', 'is_weekend',
    'account_encoded', 'vendor_risk_score', 'amount_deviation',
    'velocity_1h', 'velocity_24h'
]

class LIMEExplainer:
    """Generador de explicaciones LIME para modelos de detección de anomalías."""
    
    def __init__(self, training_data: np.ndarray, mode: str = 'classification') -> None:
        self.training_data = training_data
        self.mode = mode
        if LimeTabularExplainer:
            self.explainer = LimeTabularExplainer(
                training_data,
                feature_names=FEATURE_NAMES[:training_data.shape[1]],
                mode=self.mode,
                discretize_continuous=True
            )
        else:
            self.explainer = None
    
    def explain(self, X_background: np.ndarray, sample: np.ndarray, predict_fn: Callable) -> dict:
        """Calcula LIME values para una muestra. Retorna dict con values y feature names."""
        if not self.explainer:
            return {'error': 'lime package not available'}
            
        sample_1d = sample.flatten() if sample.ndim > 1 else sample
        
        explanation = self.explainer.explain_instance(
            sample_1d,
            predict_fn,
            num_features=len(FEATURE_NAMES)
        )
        return {'explanation': explanation}
    
    def get_top_factors(self, explanation: dict, n_top: int = 3) -> list[dict]:
        """Retorna los N factores más importantes con nombre, valor LIME y dirección."""
        if 'explanation' not in explanation:
            return []
            
        exp = explanation['explanation']
        top_features = exp.as_list()[:n_top]
        
        top_factors = []
        for feature_desc, val in top_features:
            feature_name = 'unknown'
            for fn in FEATURE_NAMES:
                if fn in feature_desc:
                    feature_name = fn
                    break
                    
            top_factors.append({
                'feature': feature_name,
                'shap_value': float(val),
                'direction': 'aumenta_riesgo' if val > 0 else 'disminuye_riesgo',
                'description': feature_desc
            })
        return top_factors
