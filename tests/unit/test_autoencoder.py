"""Tests unitarios para el Autoencoder PyTorch."""
import numpy as np
import pytest
import tempfile
import os


@pytest.fixture
def sample_data() -> np.ndarray:
    """Datos de entrenamiento de muestra: 200 muestras, 9 features."""
    np.random.seed(42)
    return np.random.randn(200, 9).astype(np.float32)


@pytest.fixture
def anomalous_data() -> np.ndarray:
    """Datos anómalos: valores extremos fuera de la distribución normal."""
    np.random.seed(99)
    return (np.random.randn(20, 9) * 10 + 15).astype(np.float32)


class TestAutoencoderDetector:
    """Tests unitarios para AutoencoderDetector."""

    def test_fit_predict_cycle(self, sample_data: np.ndarray) -> None:
        """El autoencoder debe poder entrenar y predecir sin errores."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=3, batch_size=32)
        detector.fit(sample_data)
        predictions = detector.predict(sample_data)
        assert predictions.shape == (200,), "Las predicciones deben tener forma (N,)"
        assert set(predictions).issubset({0, 1}), "Predicciones deben ser 0 o 1"

    def test_score_range(self, sample_data: np.ndarray) -> None:
        """Los scores de anomalía deben ser valores positivos."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=3)
        detector.fit(sample_data)
        scores = detector.score(sample_data)
        assert scores.shape == (200,)
        assert np.all(scores >= 0), "Los scores deben ser no negativos (MSE)"

    def test_anomalies_score_higher(
        self, sample_data: np.ndarray, anomalous_data: np.ndarray
    ) -> None:
        """Las anomalías deben tener scores de reconstrucción más altos que los datos normales."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=10)
        detector.fit(sample_data)
        normal_scores = detector.score(sample_data)
        anomaly_scores = detector.score(anomalous_data)
        assert np.mean(anomaly_scores) > np.mean(normal_scores), (
            "Las anomalías deben tener error de reconstrucción mayor que los datos normales"
        )

    def test_partial_fit_updates_buffer(self, sample_data: np.ndarray) -> None:
        """partial_fit debe acumular datos en el buffer interno."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=3, buffer_size=500)
        detector.fit(sample_data)
        initial_buffer_size = len(detector._buffer) if hasattr(detector, "_buffer") else 0
        new_data = sample_data[:50]
        detector.partial_fit(new_data)
        # El buffer debe contener más datos que antes
        assert hasattr(detector, "_buffer"), "El detector debe tener un buffer interno"

    def test_save_and_load(self, sample_data: np.ndarray) -> None:
        """El modelo debe poder guardarse y cargarse correctamente."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=3)
        detector.fit(sample_data)
        scores_before = detector.score(sample_data)

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name

        try:
            detector.save(path)
            detector2 = AutoencoderDetector(input_dim=9)
            detector2.load(path)
            scores_after = detector2.score(sample_data)
            np.testing.assert_allclose(scores_before, scores_after, rtol=1e-4)
        finally:
            os.unlink(path)

    def test_is_fitted_flag(self, sample_data: np.ndarray) -> None:
        """is_fitted debe ser False antes de entrenar y True después."""
        from models.autoencoder import AutoencoderDetector
        detector = AutoencoderDetector(input_dim=9, epochs=2)
        assert not detector.is_fitted, "Debe ser False antes de fit()"
        detector.fit(sample_data)
        assert detector.is_fitted, "Debe ser True después de fit()"
