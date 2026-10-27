
import torch
import joblib
import numpy as np
from typing import List, Dict
import os
import sys

# Add this model's directory to path so train.py and preprocessing.py can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import BedForecastLSTM

class BedForecastModel:
    def __init__(self, model_dir='models/bed_forecasting/artifacts'):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
    
    def load(self) -> bool:
        try:
            self.model = BedForecastLSTM()
            model_path = os.path.join(self.model_dir, 'bed_lstm_v1.pt')
            if not os.path.exists(model_path): return False
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()
            
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            return True
        except Exception:
            return False
    
    def predict_next_day(self, recent_data: List[List[float]]) -> float:
        if not self.model or not self.scaler:
            return 0.0
        
        scaled_data = self.scaler.transform(recent_data)
        x = torch.tensor([scaled_data], dtype=torch.float32)
        with torch.no_grad():
            out = self.model(x).numpy()[0]
        out = out + scaled_data[-1, 2]
        return float((out[0] - self.scaler.min_[2]) / self.scaler.scale_[2])
    
    def predict_7day(self, recent_data: List[List[float]]) -> List[float]:
        if not self.model or not self.scaler:
            return [0.0]*7
            
        scaled_data = self.scaler.transform(recent_data)
        x = torch.tensor([scaled_data], dtype=torch.float32)
        with torch.no_grad():
            out = self.model(x).numpy()[0]
        out = out + scaled_data[-1, 2]
        return ((out - self.scaler.min_[2]) / self.scaler.scale_[2]).tolist()
