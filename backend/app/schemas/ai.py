from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class SymptomCheckRequest(BaseModel):
    symptoms_text: str
    selected_symptoms: Optional[List[str]] = None

class SymptomCheckResponse(BaseModel):
    id: str
    predicted_condition: str
    confidence: float
    department: str
    explanation: str
    disclaimer: str = "This is an AI prediction and not a medical diagnosis."
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DiseasePredictionRequest(BaseModel):
    age: int
    sex: int
    cp: int
    trestbps: int
    chol: int
    fbs: int
    restecg: int
    thalach: int
    exang: int
    oldpeak: float
    slope: int
    ca: int
    thal: int

class DiseasePredictionResponse(BaseModel):
    prediction: str
    probability: float
    risk_category: str
    feature_importance: Dict[str, float]
    disclaimer: str = "This is an AI prediction and not a medical diagnosis."

class ReportUploadResponse(BaseModel):
    id: str
    file_name: str
    status: str

class ReportSummaryResponse(BaseModel):
    id: str
    report_type: str
    summary: str
    key_findings: List[str]
    important_values: Dict[str, str]
    abnormal_values: Dict[str, str]
    explanation: str
    questions: List[str]
    disclaimer: str = "This is an AI generated summary and not a medical diagnosis."

class MedicationItem(BaseModel):
    raw_text: str
    normalized_name: str
    dosage: str
    frequency: str
    duration: str
    route: str
    confidence: float
    needs_verification: bool

class PrescriptionAnalysisResponse(BaseModel):
    medications: List[MedicationItem]
    llm_explanation: str
    disclaimer: str = "This is an AI extraction. Always verify with the original prescription."

class ChatMessageRequest(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    response: str
    sources: List[str]

class BedForecastResponse(BaseModel):
    current_occupancy: int
    available_beds: int
    occupancy_rate: float
    forecast: List[Dict[str, Any]]
    warnings: List[str]

class TriageRequest(BaseModel):
    symptoms: str
    severity: int
    duration: str
    age: int
    vital_signs: Dict[str, Any]
    consciousness_level: str
    red_flag_symptoms: List[str]

class TriageResponse(BaseModel):
    urgency: str
    confidence: float
    queue_number: int
    estimated_wait: int
    override_applied: bool
    disclaimer: str = "This is an AI triage prediction and not a final medical decision."

class AppointmentRecommendation(BaseModel):
    doctor_name: str
    department: str
    date: str
    time_slot: str
    score: float
    reason: str
