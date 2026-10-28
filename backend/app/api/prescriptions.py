from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict, List
import logging
import shutil
import os
import uuid

from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.db.models.ai_models import Prescription, PrescriptionItem

from app.services.prescription_service import prescription_service

router = APIRouter(prefix="/api/prescriptions", tags=["Prescription Analysis"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads', 'prescriptions'))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/analyze")
async def analyze_prescription(
    file: UploadFile = File(...),
    writing_mode: str = Form(default='printed'),  # 'printed' | 'handwritten'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and analyze a prescription image."""
    if writing_mode not in ('printed', 'handwritten'):
        writing_mode = 'printed'

    try:
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = prescription_service.analyze(file_path, writing_mode=writing_mode)
        if result.get("ocr_engine") == "mock":
            try:
                os.remove(file_path)
            except OSError:
                pass
            raise HTTPException(
                status_code=503,
                detail="OCR is unavailable on this server. Start the backend with PaddleOCR installed; no prescription data was extracted.",
            )

        prescription_id = str(uuid.uuid4())
        try:
            db_prescription = Prescription(
                id=prescription_id,
                patient_id=current_user.id,
                file_name=file.filename or unique_filename,
                file_path=file_path,
                ocr_text=result.get("ocr_text", ""),
                ocr_confidence=float(result.get("ocr_confidence", 0.0)),
                structured_data=result.get("medications", []),
                llm_explanation=result.get("llm_explanation", ""),
                status="analyzed",
            )
            db.add(db_prescription)
            db.flush()

            for med in result.get("medications", []):
                item = PrescriptionItem(
                    id=str(uuid.uuid4()),
                    prescription_id=prescription_id,
                    raw_text=med.get("raw_line") or med.get("raw_text", ""),
                    normalized_name=med.get("name_transcribed") or med.get("normalized_name", ""),
                    dosage=med.get("strength") or med.get("dosage", ""),
                    frequency=med.get("frequency", ""),
                    duration=med.get("duration", ""),
                    route=med.get("route", ""),
                    instructions=med.get("meal_instructions", ""),
                    confidence=float(med.get("confidence", 0.0)),
                    needs_verification=bool(med.get("requires_review", True)),
                )
                db.add(item)

            db.commit()
            logger.info(f"Prescription saved: {prescription_id}")
        except Exception as db_err:
            logger.error(f"Failed to save prescription to DB: {db_err}")
            db.rollback()

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError:
            pass

        return {
            "id": prescription_id,
            "status": "success",
            "writing_mode": writing_mode,
            "analysis": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze prescription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during prescription analysis.",
        )


@router.get("/{prescription_id}")
def get_prescription(
    prescription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a previously analyzed prescription."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        Prescription.patient_id == current_user.id,
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    items = db.query(PrescriptionItem).filter(
        PrescriptionItem.prescription_id == prescription_id
    ).all()

    medications = [
        {
            "name_raw": item.raw_text,
            "name_transcribed": item.normalized_name,
            "normalized_name": item.normalized_name,
            "strength": item.dosage,
            "dosage": item.dosage,
            "frequency": item.frequency,
            "duration": item.duration,
            "route": item.route,
            "meal_instructions": item.instructions,
            "confidence": item.confidence,
            "requires_review": item.needs_verification,
        }
        for item in items
    ]

    return {
        "id": prescription.id,
        "status": prescription.status,
        "file_name": prescription.file_name,
        "ocr_text": prescription.ocr_text,
        "ocr_confidence": prescription.ocr_confidence,
        "medications": medications,
        "llm_explanation": prescription.llm_explanation,
        "disclaimer": "This is AI-assisted analysis. Never change medications without consulting your doctor.",
    }
