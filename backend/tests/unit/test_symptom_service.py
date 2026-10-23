"""Unit tests for symptom service."""
import pytest
import sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app.services.symptom_service import SymptomService
from models.symptom_checker.preprocessing import normalize_symptoms

def test_symptom_normalization():
    vocab = ['headache', 'continuous_sneezing', 'high_fever']
    text = "I have a headache and I am continuous sneezing."
    
    normalized = normalize_symptoms(text, vocab)
    assert 'headache' in normalized
    assert 'continuous_sneezing' in normalized

@patch('app.services.symptom_service.SymptomCheckerModel')
def test_symptom_service(mock_model_class):
    mock_instance = mock_model_class.return_value
    mock_instance.load.return_value = True
    mock_instance.symptom_vocab = ['headache', 'fever']
    mock_instance.predict.return_value = {
        'predictions': [{'disease': 'Common Cold', 'confidence': 0.9, 'department': 'General Medicine'}],
        'matched_symptoms': ['headache'],
        'top_prediction': {'disease': 'Common Cold', 'confidence': 0.9, 'department': 'General Medicine'},
        'model_version': 'v1'
    }
    
    service = SymptomService()
    service.model = mock_instance
    service._loaded = True
    
    # Needs LLM mocking if generating explanations, so we pass just basic test
    with patch('app.services.symptom_service.llm_provider.generate', return_value="Mock explanation"):
        result = service.check_symptoms(symptoms_text="headache")
        
        assert result['predicted_condition'] == 'Common Cold'
        assert 'Mock explanation' in result['explanation']
        assert result['department'] == 'General Medicine'
