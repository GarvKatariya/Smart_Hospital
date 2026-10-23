"""Triage Service handling AI predictions and queue management."""
import sys, os, importlib.util
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models')
_spec = importlib.util.spec_from_file_location("triage_inference", os.path.join(MODELS_DIR, 'triage', 'inference.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
TriageModel = _mod.TriageModel

from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logging import get_logger
from app.db.models.ai_models import TriageRecord
from app.db.models.hospital import QueueEntry


logger = get_logger(__name__)

class TriageService:
    def __init__(self):
        self.model = TriageModel()
        self._loaded = False
        
    def load(self):
        self._loaded = self.model.load()
        if self._loaded:
            logger.info("Triage GRU model loaded successfully.")
        else:
            logger.warning("Failed to load Triage GRU model. Run training script first.")
            
    def predict_urgency(self, data: Dict, patient_id: str, db: Session) -> Dict:
        if not self._loaded:
            self.load()
            
        # 1. Check safety overrides
        override = None
        reason = None
        
        if data.get('has_chest_pain') and data.get('has_breathing_difficulty'):
            override = 'Emergency'
            reason = 'chest_pain_breathing'
        elif data.get('has_loss_of_consciousness'):
            override = 'Emergency'
            reason = 'unconscious'
        elif data.get('has_severe_bleeding'):
            override = 'Emergency'
            reason = 'severe_bleeding'
        elif data.get('oxygen_saturation', 100) < 90:
            override = 'Emergency'
            reason = 'low_spo2'
        elif data.get('consciousness_level') in ['pain', 'unresponsive']:
            override = 'Emergency'
            reason = 'consciousness_level_critical'
            
        prediction = None
        if self._loaded:
            try:
                prediction = self.model.predict(data)
            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                
        if not prediction:
            prediction = {'urgency': 'Medium', 'confidence': 0.0, 'model_version': 'fallback'}
            
        final_urgency = override if override else prediction['urgency']
        
        # Save Triage Record
        triage_record = TriageRecord(
            patient_id=patient_id,
            symptoms=data.get('symptoms', ''),
            severity=data.get('severity_score', 0),
            duration=str(data.get('duration_hours', 0)),
            age=data.get('age', 0),
            vital_signs={
                'hr': data.get('heart_rate'),
                'bp_sys': data.get('blood_pressure_systolic'),
                'bp_dia': data.get('blood_pressure_diastolic'),
                'temp': data.get('temperature'),
                'rr': data.get('respiratory_rate'),
                'spo2': data.get('oxygen_saturation')
            },
            consciousness_level=data.get('consciousness_level', 'alert'),
            red_flag_symptoms=data.get('red_flag_symptoms', []),
            predicted_urgency=prediction['urgency'],
            confidence=prediction['confidence'],
            override_urgency=override,
            override_reason=reason,
            model_version=prediction['model_version']
        )
        db.add(triage_record)
        db.commit()
        db.refresh(triage_record)
        
        # Determine Wait time and queue
        priority_map = {'Emergency': 0, 'High': 15, 'Medium': 45, 'Low': 90}
        wait_time = priority_map.get(final_urgency, 60)
        
        # Get next queue number for Emergency Department (hardcoded for simplicity)
        from app.db.models.hospital import Department
        dept = db.query(Department).filter(Department.name == 'Emergency Medicine').first()
        dept_id = dept.id if dept else "unknown"
        
        q_count = db.query(QueueEntry).filter(QueueEntry.department_id == dept_id, QueueEntry.status == 'waiting').count()
        
        queue_entry = QueueEntry(
            patient_id=patient_id,
            department_id=dept_id,
            queue_number=q_count + 1,
            priority=final_urgency.lower(),
            estimated_wait_minutes=wait_time,
            check_in_time=datetime.utcnow()
        )
        db.add(queue_entry)
        db.commit()
        
        return {
            'urgency': final_urgency,
            'confidence': prediction['confidence'],
            'queue_number': queue_entry.queue_number,
            'estimated_wait': wait_time,
            'override_applied': bool(override)
        }
        
    def get_queue(self, db: Session, department_id: str = None) -> List[Dict]:
        query = db.query(QueueEntry).filter(QueueEntry.status == 'waiting')
        if department_id:
            query = query.filter(QueueEntry.department_id == department_id)
            
        # Priority mapping for sorting
        priority_order = {'emergency': 1, 'high': 2, 'medium': 3, 'low': 4}
        
        entries = query.all()
        # Sort by priority then check-in time
        entries.sort(key=lambda x: (priority_order.get(x.priority, 5), x.check_in_time))
        
        return [
            {
                'id': q.id,
                'patient_id': q.patient_id,
                'queue_number': q.queue_number,
                'priority': q.priority,
                'estimated_wait': q.estimated_wait_minutes,
                'check_in_time': q.check_in_time.isoformat()
            } for q in entries
        ]

triage_service = TriageService()
