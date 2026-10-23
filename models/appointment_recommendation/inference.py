
import joblib
from typing import List, Dict
import os

class AppointmentRecommender:
    def __init__(self, model_dir='models/appointment_recommendation/artifacts'):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
    
    def load(self) -> bool:
        try:
            self.model = joblib.load(os.path.join(self.model_dir, 'xgb_model.pkl'))
            self.scaler = joblib.load(os.path.join(self.model_dir, 'scaler.pkl'))
            return True
        except:
            return False
            
    def score_slots(self, candidate_slots: List[Dict]) -> List[Dict]:
        if not self.model or not candidate_slots: return candidate_slots
        
        # This assumes candidate slots have 'department_encoded', 'day_of_week', 'hour', 'appointment_type_encoded', 'urgency_encoded'
        features = [[s.get('department_encoded',0), s.get('day_of_week',0), s.get('hour',0), s.get('appointment_type_encoded',0), s.get('urgency_encoded',0)] for s in candidate_slots]
        scaled = self.scaler.transform(features)
        
        probs = self.model.predict_proba(scaled)[:, 1]
        
        for i, slot in enumerate(candidate_slots):
            slot['score'] = float(probs[i])
            slot['recommendation_reason'] = 'High likelihood of completion' if probs[i] > 0.7 else 'Standard slot'
            
        return sorted(candidate_slots, key=lambda x: x['score'], reverse=True)
