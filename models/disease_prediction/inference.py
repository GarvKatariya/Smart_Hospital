"""
Disease Prediction - Inference Service
"""
import joblib
import numpy as np
import os
from typing import Dict, Any

FEATURE_NAMES = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 
                 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal']

class DiseasePredictionModel:
    def __init__(self, model_dir: str = 'artifacts'):
        self.model = None
        self.scaler = None
        self.feature_names = FEATURE_NAMES
        self.model_dir = model_dir
        self._loaded = False
    
    def load(self) -> bool:
        """Load the serialized Random Forest classifier artifact."""
        try:
            model_path = os.path.join(self.model_dir, 'disease_random_forest_v1.joblib')
            
            if not os.path.exists(model_path):
                return False
                
            scaler_path = os.path.join(self.model_dir, 'scaler_v3.joblib')
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self._loaded = True
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Make prediction from feature dictionary.
        
        Returns:
        {
            "prediction": 0 or 1,
            "probability": float,
            "risk_category": "Low" | "Medium" | "High",
            "feature_importance": {feature: importance},
            "model_version": "disease-random-forest-v1"
        }
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
            
        # Validate and align features
        feature_vector = []
        for name in self.feature_names:
            if name not in features:
                raise ValueError(f"Missing required feature: {name}")
            feature_vector.append(float(features[name]))
            
        # Create numpy array and scale
        X = np.array(feature_vector).reshape(1, -1)
        X_scaled = self.scaler.transform(X) if self.scaler else X
        
        # Predict
        pred = int(self.model.predict(X_scaled)[0])
        prob = float(self.model.predict_proba(X_scaled)[0][1])
        
        # Extract feature importances if available
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_importance = {feat: float(imp) for feat, imp in zip(self.feature_names, importances)}
            # Get top 5
            feature_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True)[:5])
            
        return {
            "prediction": pred,
            "probability": prob,
            "risk_category": self.get_risk_category(prob),
            "feature_importance": feature_importance,
            "model_version": "disease-random-forest-v1"
        }
    
    def get_risk_category(self, probability: float) -> str:
        if probability < 0.3: return "Low"
        elif probability < 0.7: return "Medium"
        else: return "High"
