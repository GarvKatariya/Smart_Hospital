"""Unit tests for symptom service."""
from unittest.mock import patch, MagicMock

import torch

from app.services.symptom_service import SymptomService
from models.symptom_checker.preprocessing import normalize_symptoms

def test_symptom_normalization():
    vocab = ['headache', 'continuous_sneezing', 'high_fever']
    text = "I have a headache and I am continuous sneezing."
    
    normalized = normalize_symptoms(text, vocab)
    assert 'headache' in normalized
    assert 'continuous_sneezing' in normalized

def test_symptom_service_returns_ranked_prediction():
    mock_model = MagicMock(return_value=torch.tensor([[3.0, 1.0]]))
    service = SymptomService()
    service.model = mock_model
    service.symptom_vocab = ['headache', 'fever']
    service.disease_list = ['Common Cold', 'Migraine']
    service._loaded = True

    with patch('app.services.symptom_service.llm_provider.generate', return_value="Mock explanation"):
        result = service.check_symptoms(symptoms_text="headache")

    assert result['predicted_condition'] == 'Common Cold'
    assert 'Mock explanation' in result['explanation']
    assert result['department'] == 'General Medicine'
    assert result['matched_symptoms'] == ['headache']
    assert len(result['all_predictions']) == 2
