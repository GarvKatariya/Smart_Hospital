"""Heart disease prediction service using the local Random Forest artifact."""
import os
import joblib
import numpy as np
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))
ARTIFACTS_DIR = os.path.join(MODELS_DIR, 'disease_prediction', 'artifacts')

FEATURE_NAMES = [
    'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs',
    'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'
]


class DiseaseService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self._loaded = False
    
    def load_model(self):
        """Load the serialized Random Forest classifier."""
        try:
            model_path = os.path.join(ARTIFACTS_DIR, 'disease_random_forest_v1.joblib')
            
            if not os.path.exists(model_path):
                logger.warning(f"Model not found at {model_path}")
                return
            
            scaler_path = os.path.join(ARTIFACTS_DIR, 'scaler_v3.joblib')
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self._loaded = True
            logger.info("Disease prediction Random Forest loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load disease prediction model: {e}")
            self._loaded = False
    
    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Make a disease prediction."""
        if not self._loaded:
            self.load_model()
        if not self._loaded:
            raise RuntimeError("Disease prediction model is not available. Please train the model first.")
        
        # Build feature array in correct order
        feature_values = [float(features.get(name, 0)) for name in FEATURE_NAMES]
        X = np.array([feature_values])
        if self.scaler:
            X = self.scaler.transform(X)
        
        # Predict
        prediction = int(self.model.predict(X)[0])
        probability = float(self.model.predict_proba(X)[0][1])
        
        # Risk categorization
        if probability >= 0.7:
            risk_category = "High"
        elif probability >= 0.4:
            risk_category = "Medium"
        else:
            risk_category = "Low"
        
        # Feature importance
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            for name, imp in zip(FEATURE_NAMES, importances):
                feature_importance[name] = float(imp)
        
        return {
            "prediction": prediction,
            "probability": probability,
            "risk_category": risk_category,
            "feature_importance": feature_importance,
            "model_version": "disease-random-forest-v1",
        }
    
    @property
    def is_available(self) -> bool:
        return self._loaded

# Singleton
disease_service = DiseaseService()
