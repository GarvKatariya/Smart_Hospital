"""
Symptom Checker Service
Integrates GRU model + LLM for symptom analysis.
Loads model directly to avoid sys.path conflicts.
"""
import os
import json
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Optional
from app.core.logging import get_logger
from app.core.config import settings
from app.ai.llm.factory import llm_provider

logger = get_logger(__name__)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))
ARTIFACTS_DIR = os.path.join(MODELS_DIR, 'symptom_checker', 'artifacts')

SYMPTOM_PROMPT = """You are a medical information assistant. Based on the AI screening results below, provide a clear, simple explanation for the patient.

Patient Symptoms: {symptoms}
AI Predicted Condition: {predicted_condition} (Confidence: {confidence:.1%})
Recommended Department: {department}

Provide:
1. A simple explanation of what this condition is
2. Why these symptoms might be associated with it
3. Recommended department and next steps
4. A clear disclaimer that this is NOT a diagnosis

Keep the language simple and reassuring. Do not use overly technical terms."""

# Disease → Department mapping
DISEASE_DEPARTMENTS = {
    'fungal infection': 'Dermatology',
    'allergy': 'General Medicine',
    'gerd': 'Gastroenterology',
    'chronic cholestasis': 'Gastroenterology',
    'drug reaction': 'General Medicine',
    'peptic ulcer disease': 'Gastroenterology',
    'aids': 'Infectious Diseases',
    'diabetes': 'Endocrinology',
    'gastroenteritis': 'Gastroenterology',
    'bronchial asthma': 'Pulmonology',
    'hypertension': 'Cardiology',
    'migraine': 'Neurology',
    'cervical spondylosis': 'Orthopedics',
    'paralysis': 'Neurology',
    'jaundice': 'Gastroenterology',
    'malaria': 'Infectious Diseases',
    'chicken pox': 'Infectious Diseases',
    'dengue': 'Infectious Diseases',
    'typhoid': 'Infectious Diseases',
    'hepatitis a': 'Gastroenterology',
    'hepatitis b': 'Gastroenterology',
    'hepatitis c': 'Gastroenterology',
    'hepatitis d': 'Gastroenterology',
    'hepatitis e': 'Gastroenterology',
    'tuberculosis': 'Pulmonology',
    'common cold': 'General Medicine',
    'pneumonia': 'Pulmonology',
    'dimorphic hemolytic anemia': 'Hematology',
    'heart attack': 'Cardiology',
    'urinary tract infection': 'Urology',
    'acne': 'Dermatology',
    'psoriasis': 'Dermatology',
    'impetigo': 'Dermatology',
    'varicose veins': 'Vascular Surgery',
    'hypothyroidism': 'Endocrinology',
    'hyperthyroidism': 'Endocrinology',
    'hypoglycemia': 'Endocrinology',
    'osteoarthritis': 'Orthopedics',
    'arthritis': 'Orthopedics',
}


class SymptomGRU(nn.Module):
    """GRU-based symptom classifier (duplicated from train.py to avoid import issues)."""
    def __init__(self, input_size, hidden_size=128, num_layers=2, num_classes=41, dropout=0.3):
        super().__init__()
        self.embedding = nn.Linear(input_size, hidden_size)
        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = self.embedding(x)
        x = x.unsqueeze(1)
        gru_out, _ = self.gru(x)
        gru_out = gru_out[:, -1, :]
        gru_out = self.dropout(gru_out)
        out = self.fc(gru_out)
        return out


class SymptomService:
    def __init__(self):
        self.model = None
        self.symptom_vocab = []
        self.disease_list = []
        self._loaded = False
    
    def load_model(self):
        """Load GRU model and vocabulary directly."""
        try:
            config_path = os.path.join(ARTIFACTS_DIR, 'training_config.json')
            model_path = os.path.join(ARTIFACTS_DIR, 'symptom_gru_v1.pt')
            vocab_path = os.path.join(ARTIFACTS_DIR, 'symptom_vocab.json')
            disease_path = os.path.join(ARTIFACTS_DIR, 'disease_labels.json')
            
            if not os.path.exists(model_path):
                logger.warning(f'Symptom model not found at {model_path}')
                return
            
            # Load vocabulary
            if os.path.exists(vocab_path):
                with open(vocab_path) as f:
                    self.symptom_vocab = json.load(f)
            
            if os.path.exists(disease_path):
                with open(disease_path) as f:
                    self.disease_list = json.load(f)
            
            # Load config for sizes
            input_size = len(self.symptom_vocab)
            num_classes = len(self.disease_list)
            
            if input_size == 0 or num_classes == 0:
                logger.warning('Empty symptom vocab or disease list')
                return
            
            self.model = SymptomGRU(
                input_size=input_size,
                hidden_size=128,
                num_layers=2,
                num_classes=num_classes,
                dropout=0.3
            )
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                # Override sizes from checkpoint config if available
                if 'model_config' in checkpoint:
                    cfg = checkpoint['model_config']
                    input_size = cfg.get('input_size', input_size)
                    num_classes = cfg.get('num_classes', num_classes)
                    # Recreate model with correct config
                    self.model = SymptomGRU(
                        input_size=input_size,
                        hidden_size=cfg.get('hidden_size', 128),
                        num_layers=cfg.get('num_layers', 2),
                        num_classes=num_classes,
                        dropout=cfg.get('dropout', 0.3)
                    )
            else:
                state_dict = checkpoint
            
            self.model.load_state_dict(state_dict)
            self.model.eval()
            self._loaded = True
            logger.info(f'Symptom checker loaded: {len(self.symptom_vocab)} symptoms, {len(self.disease_list)} diseases')
        except Exception as e:
            logger.error(f'Failed to load symptom model: {e}')
            self._loaded = False
    
    def check_symptoms(self, symptoms_text: str = '', selected_symptoms: List[str] = None) -> Dict:
        if not self._loaded:
            self.load_model()
        if not self._loaded:
            raise RuntimeError('Symptom checker model not available')
        
        # Combine and normalize symptoms
        all_symptoms = list(selected_symptoms or [])
        if symptoms_text:
            words = symptoms_text.lower().replace(',', ' ').replace('.', ' ').split()
            all_symptoms.extend([w.strip() for w in words if w.strip()])
        
        # Normalize: replace spaces with underscores
        normalized = [s.strip().lower().replace(' ', '_') for s in all_symptoms]
        
        # Match against vocabulary
        symptom_to_idx = {s: i for i, s in enumerate(self.symptom_vocab)}
        matched = [s for s in normalized if s in symptom_to_idx]
        
        if not matched:
            return {
                'error': 'No recognized symptoms',
                'available_symptoms': self.symptom_vocab[:30],
                'input_symptoms': normalized
            }
        
        # Build multi-hot vector
        x = np.zeros(len(self.symptom_vocab), dtype=np.float32)
        for s in matched:
            x[symptom_to_idx[s]] = 1.0
        
        # Predict
        with torch.no_grad():
            x_tensor = torch.FloatTensor(x).unsqueeze(0)
            logits = self.model(x_tensor)
            probs = torch.softmax(logits, dim=1).numpy()[0]
        
        # Get top 3 predictions
        top_indices = np.argsort(probs)[::-1][:3]
        predictions = []
        for idx in top_indices:
            disease = self.disease_list[idx] if idx < len(self.disease_list) else f'Unknown-{idx}'
            disease_lower = disease.lower().replace('_', ' ')
            dept = DISEASE_DEPARTMENTS.get(disease_lower, 'General Medicine')
            predictions.append({
                'disease': disease.replace('_', ' ').title(),
                'confidence': float(probs[idx]),
                'department': dept
            })
        
        top = predictions[0]
        
        # LLM explanation
        try:
            prompt = SYMPTOM_PROMPT.format(
                symptoms=', '.join(matched),
                predicted_condition=top['disease'],
                confidence=top['confidence'],
                department=top['department']
            )
            explanation = llm_provider.generate(prompt, context={
                'predicted_condition': top['disease'],
                'confidence': top['confidence'],
                'department': top['department']
            })
        except Exception as e:
            logger.error(f'LLM explanation failed: {e}')
            explanation = (f"Based on your symptoms, our AI model suggests a possible association "
                         f"with {top['disease']} (confidence: {top['confidence']:.1%}). "
                         f"Please consult a {top['department']} specialist.")
        
        return {
            'predicted_condition': top['disease'],
            'confidence': top['confidence'],
            'department': top['department'],
            'all_predictions': predictions,
            'matched_symptoms': matched,
            'explanation': explanation,
            'model_version': 'symptom-gru-v1',
            'disclaimer': 'This is an AI-assisted screening tool and NOT a medical diagnosis. '
                         'Please consult a qualified healthcare professional.'
        }
    
    def get_symptoms_list(self) -> List[str]:
        if not self._loaded:
            self.load_model()
        return self.symptom_vocab
    
    @property
    def is_available(self):
        return self._loaded

symptom_service = SymptomService()
