from sqlalchemy import Column, String, Boolean, Float, Integer, ForeignKey, JSON
from app.db.base import Base, BaseModel

class SymptomCheck(Base, BaseModel):
    __tablename__ = 'symptom_checks'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    symptoms_text = Column(String(1000))
    normalized_symptoms = Column(JSON)
    predicted_condition = Column(String(255))
    confidence = Column(Float)
    department_recommendation = Column(String(255))
    llm_explanation = Column(String(2000))
    model_version = Column(String(50))

class DiseasePrediction(Base, BaseModel):
    __tablename__ = 'disease_predictions'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    input_features = Column(JSON)
    prediction = Column(String(255))
    probability = Column(Float)
    risk_category = Column(String(50))
    feature_importance = Column(JSON)
    model_version = Column(String(50))

class MedicalReport(Base, BaseModel):
    __tablename__ = 'medical_reports'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255))
    file_path = Column(String(1000))
    file_type = Column(String(50))
    file_size = Column(Integer)
    ocr_text = Column(String)
    ocr_confidence = Column(Float)
    summary = Column(String)
    report_type = Column(String(100))
    status = Column(String(50), default='uploaded')

class Prescription(Base, BaseModel):
    __tablename__ = 'prescriptions'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255))
    file_path = Column(String(1000))
    ocr_text = Column(String)
    ocr_confidence = Column(Float)
    structured_data = Column(JSON)
    llm_explanation = Column(String(2000))
    status = Column(String(50))

class PrescriptionItem(Base, BaseModel):
    __tablename__ = 'prescription_items'
    prescription_id = Column(String(36), ForeignKey('prescriptions.id'), nullable=False)
    raw_text = Column(String(500))
    normalized_name = Column(String(255))
    dosage = Column(String(100))
    frequency = Column(String(100))
    duration = Column(String(100))
    route = Column(String(100))
    instructions = Column(String(1000))
    confidence = Column(Float)
    needs_verification = Column(Boolean, default=False)

class TriageRecord(Base, BaseModel):
    __tablename__ = 'triage_records'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    symptoms = Column(String(1000))
    severity = Column(Integer)
    duration = Column(String(100))
    age = Column(Integer)
    vital_signs = Column(JSON)
    consciousness_level = Column(String(50))
    red_flag_symptoms = Column(JSON)
    predicted_urgency = Column(String(50))
    confidence = Column(Float)
    override_urgency = Column(String(50))
    override_reason = Column(String(500))
    model_version = Column(String(50))

class ChatbotSession(Base, BaseModel):
    __tablename__ = 'chatbot_sessions'
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    title = Column(String(255))
    is_active = Column(Boolean, default=True)

class ChatbotMessage(Base, BaseModel):
    __tablename__ = 'chatbot_messages'
    session_id = Column(String(36), ForeignKey('chatbot_sessions.id'), nullable=False)
    role = Column(String(50)) # user/assistant
    content = Column(String)
    sources = Column(JSON)

class ModelVersion(Base, BaseModel):
    __tablename__ = 'model_versions'
    model_name = Column(String(255))
    version = Column(String(50))
    training_date = Column(String(50))
    dataset_name = Column(String(255))
    dataset_version = Column(String(50))
    preprocessing_version = Column(String(50))
    metrics = Column(JSON)
    hyperparameters = Column(JSON)
    file_path = Column(String(1000))
    is_active = Column(Boolean, default=False)

class AuditLog(Base, BaseModel):
    __tablename__ = 'audit_logs'
    user_id = Column(String(36), ForeignKey('users.id'))
    action = Column(String(255))
    resource_type = Column(String(255))
    resource_id = Column(String(255))
    details = Column(JSON)
    ip_address = Column(String(255))
