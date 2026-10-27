"""Regression tests for emergency triage and queue persistence."""
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.hospital import Department, QueueEntry
from app.db.models.user import User
from app.db.models.ai_models import TriageRecord
from app.services.triage_service import TriageService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_emergency_override_saves_triage_and_queue_atomically(db_session):
    patient = User(email="patient@example.com", hashed_password="x", full_name="Test Patient", role="patient")
    department = Department(name="Emergency Medicine")
    db_session.add_all([patient, department])
    db_session.commit()

    service = TriageService()
    service._loaded = True
    service.model = Mock()
    service.model.predict.return_value = {
        "urgency": "Low", "confidence": 0.7, "model_version": "test-model",
    }
    data = {
        "symptoms": "chest pain and difficulty breathing",
        "severity_score": 8,
        "duration_hours": 1,
        "age": 45,
        "red_flag_symptoms": ["chest pain", "shortness of breath"],
        "has_chest_pain": True,
        "has_breathing_difficulty": True,
        "has_severe_bleeding": False,
        "has_loss_of_consciousness": False,
        "consciousness_level": "alert",
    }

    result = service.predict_urgency(data, patient.id, db_session)

    assert result["urgency"] == "Emergency"
    assert result["override_applied"] is True
    assert db_session.query(TriageRecord).count() == 1
    queue_entry = db_session.query(QueueEntry).one()
    assert queue_entry.patient_id == patient.id
    assert queue_entry.department_id == department.id
    assert queue_entry.priority == "emergency"


def test_triage_does_not_save_without_emergency_department(db_session):
    service = TriageService()
    service._loaded = True
    service.model = Mock()
    service.model.predict.return_value = {
        "urgency": "Low", "confidence": 0.7, "model_version": "test-model",
    }

    with pytest.raises(RuntimeError, match="Emergency Medicine department"):
        service.predict_urgency({"symptoms": "headache"}, "missing-patient", db_session)

    assert db_session.query(TriageRecord).count() == 0
