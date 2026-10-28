from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.hospital import Doctor
from app.api.deps import require_role
from app.schemas.ai import TriageRequest, TriageResponse
from app.services.triage_service import triage_service
from typing import List, Literal
import re
from pydantic import BaseModel

router = APIRouter(prefix="/api/triage", tags=["triage"])


class QueueStatusUpdate(BaseModel):
    status: Literal["in_progress", "completed", "cancelled"]

@router.post("/predict", response_model=TriageResponse)
def predict_triage(request: TriageRequest, db: Session = Depends(get_db), current_user: User = Depends(require_role(["patient"]))):
    data_dict = request.model_dump()
    data_dict['severity_score'] = data_dict['severity']
    data_dict['symptom_count'] = len([part for part in data_dict['symptoms'].split() if part])
    duration_match = re.fullmatch(
        r'\s*(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?|days?|weeks?)?\s*',
        data_dict['duration'],
        re.IGNORECASE,
    )
    if not duration_match:
        raise HTTPException(status_code=422, detail="Duration must be a number of minutes, hours, days, or weeks")
    duration_value = float(duration_match.group(1))
    duration_unit = (duration_match.group(2) or 'hours').lower()
    if duration_unit.startswith(('minute', 'min')):
        duration_value /= 60
    elif duration_unit.startswith('day'):
        duration_value *= 24
    elif duration_unit.startswith('week'):
        duration_value *= 168
    data_dict['duration_hours'] = duration_value
    # Flatten vital signs into top level for service
    vitals = data_dict.pop('vital_signs', {})
    for k, v in vitals.items():
        data_dict[k] = v
        
    # Set boolean flags
    red_flags = data_dict.get('red_flag_symptoms', [])
    normalized_flags = {flag.strip().lower().replace("_", " ") for flag in red_flags}
    data_dict['has_chest_pain'] = 'chest pain' in normalized_flags
    data_dict['has_breathing_difficulty'] = bool(normalized_flags & {'breathing difficulty', 'shortness of breath'})
    data_dict['has_severe_bleeding'] = 'severe bleeding' in normalized_flags
    data_dict['has_loss_of_consciousness'] = 'loss of consciousness' in normalized_flags

    try:
        result = triage_service.predict_urgency(data_dict, current_user.id, db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return TriageResponse(**result)

@router.get("/queue")
def get_queue(department_id: str = None, db: Session = Depends(get_db), current_user: User = Depends(require_role(["doctor", "admin"]))):
    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=403, detail="Doctor profile is not configured")
        if department_id and department_id != doctor.department_id:
            raise HTTPException(status_code=403, detail="Doctors can only access their own department queue")
        department_id = doctor.department_id
    return triage_service.get_queue(db, department_id)


@router.get("/my-queue")
def get_my_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["patient"])),
):
    """Let patients track their own active queue entries without exposing others."""
    return triage_service.get_patient_queue(db, current_user.id)


@router.patch("/queue/{entry_id}")
def update_queue_entry(
    entry_id: str,
    request: QueueStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["doctor", "admin"])),
):
    try:
        entry = triage_service.update_queue_status(db, entry_id, request.status, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return {"id": entry.id, "status": entry.status}
