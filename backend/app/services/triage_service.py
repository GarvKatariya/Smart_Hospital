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
from app.db.models.user import User
from app.services.audit_service import record_audit


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
        
        from app.db.models.hospital import Department
        dept = db.query(Department).filter(
            Department.name == 'Emergency Medicine',
            Department.is_active.is_(True),
        ).first()
        if not dept:
            raise RuntimeError('Emergency Medicine department is not configured')

        # Save triage and queue data as one transaction.
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
        
        # Determine Wait time and queue
        priority_map = {'Emergency': 0, 'High': 15, 'Medium': 45, 'Low': 90}
        wait_time = priority_map.get(final_urgency, 60)
        
        dept_id = dept.id
        
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
        record_audit(db, user_id=patient_id, action="triage.completed", resource_type="triage", resource_id=triage_record.id, details={"urgency": final_urgency, "queue_number": queue_entry.queue_number})
        db.commit()
        
        return {
            'urgency': final_urgency,
            'confidence': prediction['confidence'],
            'queue_number': queue_entry.queue_number,
            'estimated_wait': wait_time,
            'override_applied': bool(override)
        }
        
    def get_queue(self, db: Session, department_id: str = None) -> List[Dict]:
        query = db.query(QueueEntry).filter(QueueEntry.status.in_(['waiting', 'in_progress']))
        if department_id:
            query = query.filter(QueueEntry.department_id == department_id)
            
        # Priority mapping for sorting
        priority_order = {'emergency': 1, 'high': 2, 'medium': 3, 'low': 4}
        
        entries = query.all()
        # Sort by priority then check-in time
        entries.sort(key=lambda x: (priority_order.get(x.priority, 5), x.check_in_time or datetime.max))
        patient_ids = {entry.patient_id for entry in entries}
        patients = {
            patient.id: patient.full_name
            for patient in db.query(User).filter(User.id.in_(patient_ids)).all()
        } if patient_ids else {}
        
        return [
            {
                'id': q.id,
                'patient_id': q.patient_id,
                'patient_name': patients.get(q.patient_id, 'Patient'),
                'queue_number': q.queue_number,
                'priority': q.priority,
                'status': q.status,
                'estimated_wait': q.estimated_wait_minutes,
                'check_in_time': q.check_in_time.isoformat() if q.check_in_time else None,
                'is_demo': (q.notes or '').startswith('DEMO_QUEUE:'),
                'notes': (q.notes or '').removeprefix('DEMO_QUEUE:') or None,
            } for q in entries
        ]

    def get_patient_queue(self, db: Session, patient_id: str) -> List[Dict]:
        """Return only this patient's active queue entries and safe status details."""
        from app.db.models.hospital import Department

        active_statuses = ('waiting', 'in_progress')
        entries = db.query(QueueEntry).filter(
            QueueEntry.status.in_(active_statuses)
        ).all()
        priority_order = {'emergency': 1, 'high': 2, 'medium': 3, 'low': 4}
        entries.sort(key=lambda entry: (
            priority_order.get((entry.priority or '').lower(), 5),
            entry.check_in_time or datetime.max,
        ))
        departments = {
            department.id: department.name
            for department in db.query(Department).all()
        }

        result = []
        for entry in entries:
            if entry.patient_id != patient_id:
                continue
            ahead = sum(
                1 for other in entries
                if other.department_id == entry.department_id
                and (
                    priority_order.get((other.priority or '').lower(), 5),
                    other.check_in_time or datetime.max,
                ) < (
                    priority_order.get((entry.priority or '').lower(), 5),
                    entry.check_in_time or datetime.max,
                )
            )
            result.append({
                'id': entry.id,
                'queue_number': entry.queue_number,
                'priority': entry.priority,
                'status': entry.status,
                'estimated_wait': entry.estimated_wait_minutes,
                'patients_ahead': ahead,
                'department_name': departments.get(entry.department_id, 'Hospital'),
                'check_in_time': entry.check_in_time.isoformat() if entry.check_in_time else None,
            })
        return result

    def update_queue_status(self, db: Session, entry_id: str, new_status: str, actor_id: str) -> QueueEntry | None:
        allowed_transitions = {
            'waiting': {'in_progress', 'cancelled'},
            'in_progress': {'completed', 'cancelled'},
        }
        entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
        if not entry:
            return None
        if new_status not in allowed_transitions.get(entry.status, set()):
            raise ValueError(f"Cannot change queue status from {entry.status} to {new_status}")

        now = datetime.utcnow()
        entry.status = new_status
        if new_status == 'in_progress':
            entry.called_at = now
        elif new_status == 'completed':
            entry.completed_at = now
        record_audit(db, user_id=actor_id, action=f"queue.{new_status}", resource_type="queue_entry", resource_id=entry.id)
        db.commit()
        db.refresh(entry)
        return entry

triage_service = TriageService()
