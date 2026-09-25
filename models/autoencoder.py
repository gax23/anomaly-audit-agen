import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, List
from models.base_detector import BaseDetector

class _AutoencoderNet(nn.Module):
    """Red neuronal autoencoder para detección de anomalías."""
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

class AutoencoderDetector(BaseDetector):
    """Detector de anomalías basado en Autoencoder PyTorch con aprendizaje incremental."""
    
    def __init__(self, input_dim: int = 9, lr: float = 1e-3, 
                 epochs: int = 50, batch_size: int = 256,
                 buffer_size: int = 500, threshold_percentile: float = 95.0) -> None:
        super().__init__(name="Autoencoder", threshold_percentile=threshold_percentile)
        self.input_dim = input_dim
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.buffer_size = buffer_size
        self.net = _AutoencoderNet(input_dim)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        self.criterion = nn.MSELoss(reduction='none')
        self.buffer: List[np.ndarray] = []
        self._buffer = self.buffer
        
    def fit(self, X: np.ndarray) -> None:
        """Entrena el autoencoder desde cero."""
        self.net.train()
        dataset = torch.tensor(X, dtype=torch.float32)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        for epoch in range(self.epochs):
            self._train_epoch(dataloader)
            
        self._is_fitted = True
        
        # Calcular threshold
        self.net.eval()
        with torch.no_grad():
            scores = self.score(X)
        self.set_threshold(scores)
        
    def _train_epoch(self, dataloader: torch.utils.data.DataLoader) -> float:
        """Ejecuta una época de entrenamiento. Retorna loss promedio."""
        total_loss = 0.0
        for batch in dataloader:
            self.optimizer.zero_grad()
            outputs = self.net(batch)
            loss = self.criterion(outputs, batch).mean()
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item() * len(batch)
        return total_loss / len(dataloader.dataset)
        
    def score(self, X: np.ndarray) -> np.ndarray:
        """Calcula el error de reconstrucción (anomaly score) por transacción."""
        self.net.eval()
        with torch.no_grad():
            tensor_X = torch.tensor(X, dtype=torch.float32)
            outputs = self.net(tensor_X)
            errors = torch.mean((outputs - tensor_X) ** 2, dim=1).numpy()
        return errors
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice si cada muestra es anomalía (1) o normal (0)."""
        if not self.is_fitted:
            raise RuntimeError("El modelo no está entrenado.")
        scores = self.score(X)
        return self.is_anomaly(scores)
        
    def partial_fit(self, X: np.ndarray) -> None:
        """Aprendizaje incremental: acumula en buffer, entrena cuando buffer lleno."""
        self.buffer.append(X)
        current_size = sum(len(x) for x in self.buffer)
        
        if current_size >= self.buffer_size:
            buffer_data = np.vstack(self.buffer)
            dataset = torch.tensor(buffer_data, dtype=torch.float32)
            dataloader = torch.utils.data.DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
            
            self.net.train()
            for _ in range(max(1, self.epochs // 5)):
                self._train_epoch(dataloader)
                
            self.buffer = []
            
    def save(self, path: str) -> None:
        """Guarda modelo y threshold en disco."""
        torch.save({
            'model_state': self.net.state_dict(),
            'threshold': self.threshold,
            'input_dim': self.input_dim,
            'is_fitted': self._is_fitted,
            'threshold_percentile': self.threshold_percentile
        }, path)
        
    def load(self, path: str) -> 'AutoencoderDetector':
        """Carga modelo desde disco."""
        checkpoint = torch.load(path)
        self.input_dim = checkpoint['input_dim']
        self.net = _AutoencoderNet(self.input_dim)
        self.net.load_state_dict(checkpoint['model_state'])
        self.threshold = checkpoint['threshold']
        self._is_fitted = checkpoint['is_fitted']
        self.threshold_percentile = checkpoint['threshold_percentile']
        return self
