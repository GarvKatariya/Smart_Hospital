"""Unit tests for disease service."""
import pytest
import sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app.services.disease_service import DiseasePredictionService

@patch('app.services.disease_service.xgboost')
@patch('app.services.disease_service.pickle')
@patch('app.services.disease_service.os.path.exists')
def test_disease_prediction(mock_exists, mock_pickle, mock_xgb):
    mock_exists.return_value = True
    mock_model = MagicMock()
    mock_model.predict.return_value = [1]
    mock_model.predict_proba.return_value = [[0.1, 0.9]]
    mock_pickle.load.return_value = mock_model
    
    service = DiseasePredictionService()
    assert service.is_available
    
    features = {
        'age': 50,
        'sex': 1,
        'cp': 2,
        'trestbps': 120,
        'chol': 200,
        'fbs': 0,
        'restecg': 1,
        'thalach': 150,
        'exang': 0,
        'oldpeak': 1.0,
        'slope': 1,
        'ca': 0,
        'thal': 2
    }
    
    result = service.predict_heart_disease(features)
    assert result['prediction'] == 1
    assert result['probability'] == 0.9
    assert result['risk_level'] == 'High Risk'
