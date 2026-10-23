"""Inference module for Triage GRU Model."""
import torch
import numpy as np
import joblib
import os
from typing import Dict

class TriageGRU(torch.nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=4, dropout=0.3):
        super().__init__()
        self.embedding = torch.nn.Linear(input_size, hidden_size)
        self.gru = torch.nn.GRU(hidden_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.dropout = torch.nn.Dropout(dropout)
        self.fc = torch.nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = self.embedding(x)
        x = x.unsqueeze(1)
        out, _ = self.gru(x)
        out = self.dropout(out[:, -1, :])
        return self.fc(out)

class TriageModel:
    def __init__(self, artifacts_dir: str = 'artifacts'):
        self.artifacts_dir = artifacts_dir
        self.model = None
        self.scaler = None
        self.le_consc = None
        self._loaded = False
        
        self.base_dir = os.path.dirname(__file__)
        self.full_artifacts_dir = os.path.join(self.base_dir, self.artifacts_dir)
        
    def load(self) -> bool:
        try:
            self.scaler = joblib.load(os.path.join(self.full_artifacts_dir, 'scaler.joblib'))
            self.le_consc = joblib.load(os.path.join(self.full_artifacts_dir, 'le_consc.joblib'))
            
            # 10 num + 1 cat + 4 bin = 15
            self.model = TriageGRU(input_size=15)
            self.model.load_state_dict(torch.load(os.path.join(self.full_artifacts_dir, 'triage_gru_v1.pt')))
            self.model.eval()
            self._loaded = True
            return True
        except Exception as e:
            print(f"Failed to load TriageModel: {e}")
            return False
            
    def predict(self, features: Dict) -> Dict:
        if not self._loaded:
            raise RuntimeError("Model not loaded")
            
        num_features = [
            features.get('symptom_count', 1),
            features.get('severity_score', 1),
            features.get('duration_hours', 1),
            features.get('age', 30),
            features.get('heart_rate', 80),
            features.get('blood_pressure_systolic', 120),
            features.get('blood_pressure_diastolic', 80),
            features.get('temperature', 37.0),
            features.get('respiratory_rate', 16),
            features.get('oxygen_saturation', 98)
        ]
        
        num_arr = self.scaler.transform([num_features])[0]
        
        consc = features.get('consciousness_level', 'alert')
        if consc not in self.le_consc.classes_:
            consc = 'alert'
        consc_arr = self.le_consc.transform([consc])
        
        bin_arr = [
            int(features.get('has_chest_pain', 0)),
            int(features.get('has_breathing_difficulty', 0)),
            int(features.get('has_severe_bleeding', 0)),
            int(features.get('has_loss_of_consciousness', 0))
        ]
        
        X = np.hstack([num_arr, consc_arr, bin_arr])
        inputs = torch.FloatTensor([X])
        
        with torch.no_grad():
            outputs = self.model(inputs)
            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
            confidence, predicted = torch.max(probs, 0)
            
        labels = ['Emergency', 'High', 'Medium', 'Low']
        
        return {
            'urgency': labels[predicted.item()],
            'confidence': float(confidence.item()),
            'model_version': 'triage-gru-v1'
        }
