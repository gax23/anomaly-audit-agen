import shap
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend sin pantalla
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any

FEATURE_NAMES = [
    'log_amount', 'hour_of_day', 'day_of_week', 'is_weekend',
    'account_encoded', 'vendor_risk_score', 'amount_deviation',
    'velocity_1h', 'velocity_24h'
]

class SHAPExplainer:
    """Generador de explicaciones SHAP para modelos de detección de anomalías."""
    
    def __init__(self, model: Any, model_type: str = 'tree') -> None:
        # model_type: 'tree' para IsolationForest, 'deep' para Autoencoder, 'kernel' para fallback
        self.model = model
        self.model_type = model_type
        self.explainer = None
    
    def explain(self, X: np.ndarray, sample_idx: int = 0) -> dict:
        """Calcula SHAP values para una muestra. Retorna dict con values y feature names."""
        sample = X[sample_idx:sample_idx+1]
        
        if self.model_type == 'tree':
            if self.explainer is None:
                self.explainer = shap.TreeExplainer(self.model)
            shap_values = self.explainer.shap_values(sample)
        elif self.model_type == 'deep':
            if self.explainer is None:
                # Wrapper para PyTorch con KernelExplainer y background de 100 muestras
                predict_fn = getattr(self.model, 'predict', self.model)
                bg_size = min(100, len(X))
                background = shap.sample(X, bg_size) if len(X) > bg_size else X
                self.explainer = shap.KernelExplainer(predict_fn, background)
            shap_values = self.explainer.shap_values(sample)
        else:
            if self.explainer is None:
                predict_fn = getattr(self.model, 'predict', self.model)
                bg_size = min(100, len(X))
                background = shap.sample(X, bg_size) if len(X) > bg_size else X
                self.explainer = shap.KernelExplainer(predict_fn, background)
            shap_values = self.explainer.shap_values(sample)
            
        return {
            'values': np.array(shap_values)[0],
            'feature_names': FEATURE_NAMES[:X.shape[1]]
        }
    
    def generate_waterfall_plot(self, shap_values: np.ndarray, 
                                 sample: np.ndarray, 
                                 output_path: str) -> str:
        """Genera waterfall plot y lo guarda como PNG. Retorna la ruta del archivo."""
        fig, ax = plt.subplots(figsize=(10, 6))
        exp = shap.Explanation(values=shap_values, data=sample, 
                               feature_names=FEATURE_NAMES[:len(shap_values)])
        shap.plots.waterfall(exp, show=False)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight')
        plt.close(fig)
        return output_path
    
    def get_top_factors(self, shap_values: np.ndarray, n_top: int = 3) -> list[dict]:
        """Retorna los N factores más importantes con nombre, valor SHAP y dirección."""
        indices = np.argsort(np.abs(shap_values))[::-1][:n_top]
        top_factors = []
        for idx in indices:
            val = float(shap_values[idx])
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f'feature_{idx}'
            top_factors.append({
                'feature': name,
                'shap_value': val,
                'direction': 'aumenta_riesgo' if val > 0 else 'disminuye_riesgo'
            })
        return top_factors
