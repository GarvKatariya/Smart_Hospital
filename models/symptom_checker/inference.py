"""
Symptom Checker - Inference Service
"""
import torch
import numpy as np
import json
import os
from typing import Dict, List, Optional

class SymptomCheckerModel:
    def __init__(self, model_dir='artifacts'):
        self.model = None
        self.symptom_vocab = None
        self.symptom_to_idx = None
        self.disease_labels = None
        self.disease_dept_map = None
        self.model_dir = model_dir
        self._loaded = False
    
    def load(self) -> bool:
        try:
            from train import SymptomGRU
            
            # Load model checkpoint
            checkpoint = torch.load(
                os.path.join(self.model_dir, 'symptom_gru_v1.pt'),
                map_location='cpu',
                weights_only=False
            )
            config = checkpoint['model_config']
            self.model = SymptomGRU(**config)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            # Load vocabularies
            with open(os.path.join(self.model_dir, 'symptom_vocab.json')) as f:
                self.symptom_vocab = json.load(f)
            with open(os.path.join(self.model_dir, 'symptom_to_idx.json')) as f:
                self.symptom_to_idx = json.load(f)
            with open(os.path.join(self.model_dir, 'disease_labels.json')) as f:
                self.disease_labels = json.load(f)
            
            # Load department map
            dept_map_path = os.path.join(os.path.dirname(self.model_dir), '..', '..', 
                                        'data', 'raw', 'symptom_checker', 'disease_department_map.json')
            if os.path.exists(dept_map_path):
                with open(dept_map_path) as f:
                    self.disease_dept_map = json.load(f)
            else:
                self.disease_dept_map = {}
            
            self._loaded = True
            return True
        except Exception as e:
            print(f'Failed to load symptom checker model: {e}')
            return False
    
    def predict(self, symptoms: List[str], top_k: int = 3) -> Dict:
        if not self._loaded:
            raise RuntimeError('Model not loaded')
        
        # Create multi-hot vector
        x = np.zeros(len(self.symptom_vocab), dtype=np.float32)
        matched_symptoms = []
        for symptom in symptoms:
            s = symptom.strip().lower().replace(' ', '_')
            if s in self.symptom_to_idx:
                x[self.symptom_to_idx[s]] = 1.0
                matched_symptoms.append(s)
        
        if not matched_symptoms:
            return {
                'error': 'No recognized symptoms found',
                'recognized_symptoms': [],
                'available_symptoms': self.symptom_vocab[:20]
            }
        
        # Predict
        with torch.no_grad():
            input_tensor = torch.FloatTensor(x).unsqueeze(0)
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1).squeeze().numpy()
        
        # Top-k predictions
        top_indices = np.argsort(probs)[::-1][:top_k]
        predictions = []
        for idx in top_indices:
            disease = self.disease_labels[idx]
            predictions.append({
                'disease': disease,
                'confidence': float(probs[idx]),
                'department': self.disease_dept_map.get(disease, 'General Medicine')
            })
        
        return {
            'predictions': predictions,
            'matched_symptoms': matched_symptoms,
            'top_prediction': predictions[0] if predictions else None,
            'model_version': 'symptom-gru-v1'
        }
