from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.ai import TriageRequest, TriageResponse
from app.services.triage_service import triage_service
from typing import List

router = APIRouter(prefix="/api/triage", tags=["triage"])

@router.post("/predict", response_model=TriageResponse)
def predict_triage(request: TriageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data_dict = request.model_dump()
    # Flatten vital signs into top level for service
    vitals = data_dict.pop('vital_signs', {})
    for k, v in vitals.items():
        data_dict[k] = v
        
    # Set boolean flags
    red_flags = data_dict.get('red_flag_symptoms', [])
    data_dict['has_chest_pain'] = 'chest pain' in red_flags or 'chest_pain' in red_flags
    data_dict['has_breathing_difficulty'] = 'breathing difficulty' in red_flags or 'shortness of breath' in red_flags
    data_dict['has_severe_bleeding'] = 'severe bleeding' in red_flags
    data_dict['has_loss_of_consciousness'] = 'loss of consciousness' in red_flags
    
    result = triage_service.predict_urgency(data_dict, current_user.id, db)
    return TriageResponse(**result)

@router.get("/queue")
def get_queue(department_id: str = None, db: Session = Depends(get_db)):
    return triage_service.get_queue(db, department_id)
