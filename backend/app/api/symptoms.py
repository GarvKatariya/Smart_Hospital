from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.schemas.ai import SymptomCheckRequest, SymptomCheckResponse
from app.services.symptom_service import symptom_service
from app.db.models.user import User
from app.db.models.ai_models import SymptomCheck
from app.core.logging import get_logger
import json

router = APIRouter(prefix='/api/symptoms', tags=['Symptom Checker'])
logger = get_logger(__name__)

@router.post('/check')
def check_symptoms(request: SymptomCheckRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = symptom_service.check_symptoms(
            symptoms_text=request.symptoms_text,
            selected_symptoms=request.selected_symptoms
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        # Store in DB
        record = SymptomCheck(
            patient_id=current_user.id,
            symptoms_text=request.symptoms_text,
            normalized_symptoms=json.dumps(result.get('matched_symptoms', [])),
            predicted_condition=result['predicted_condition'],
            confidence=result['confidence'],
            department_recommendation=result['department'],
            llm_explanation=result['explanation'],
            model_version=result['model_version']
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return {
            'id': record.id,
            'predicted_condition': result['predicted_condition'],
            'confidence': result['confidence'],
            'department': result['department'],
            'all_predictions': result['all_predictions'],
            'matched_symptoms': result['matched_symptoms'],
            'explanation': result['explanation'],
            'disclaimer': result['disclaimer'],
            'created_at': record.created_at.isoformat() if record.created_at else None
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Symptom check failed: {e}')
        raise HTTPException(status_code=500, detail='Symptom check failed')

@router.get('/')
def list_symptoms():
    try:
        symptoms = symptom_service.get_symptoms_list()
        if symptoms:
            return {'symptoms': symptoms, 'count': len(symptoms)}
        return {'symptoms': [], 'count': 0, 'message': 'Symptom checker model not loaded yet'}
    except Exception as e:
        logger.error(f'Failed to list symptoms: {e}')
        return {'symptoms': [], 'count': 0, 'message': 'Model not available'}
