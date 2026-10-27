import os
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.db.models.ai_models import MedicalReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])
report_service = ReportService()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads', 'reports'))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    writing_mode: str = Form(default='printed'),  # 'printed' | 'handwritten'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and analyze a medical report image or PDF.

    The document is automatically classified (lab report, prescription,
    imaging, discharge, etc.) and the appropriate extraction pipeline is used.
    """
    if writing_mode not in ('printed', 'handwritten'):
        writing_mode = 'printed'

    try:
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Process with OCR + classifier + parser, passing writing_mode
        result = report_service.process_report_image(contents, writing_mode=writing_mode)

        ocr_data = result.get("ocr", {})
        ocr_text = ocr_data.get("full_text", "")
        ocr_confidence = float(ocr_data.get("average_confidence", 0.0))
        parsed = result.get("parsed", {})

        # Extract common fields
        summary = parsed.get("summary", "")
        key_findings = parsed.get("key_findings", [])
        abnormal_values = parsed.get("abnormal_values", {})
        report_type = parsed.get("report_type", "General Medical Report")
        document_category = parsed.get("document_category", "unknown")
        classification_confidence = parsed.get("classification_confidence", 0.0)

        # Build a richer summary string if the parser produced findings
        if key_findings and summary:
            if abnormal_values:
                abnormal_list = "; ".join(
                    f"{k}: {v}" for k, v in abnormal_values.items()
                )
                summary = f"{summary}\nAbnormal values: {abnormal_list}"
        elif not summary:
            summary = "Report processed successfully. Review extracted text for details."

        # Persist to DB
        db_report = MedicalReport(
            id=str(uuid.uuid4()),
            patient_id=current_user.id,
            file_name=file.filename or unique_filename,
            file_path=file_path,
            file_type=file_ext.lstrip("."),
            file_size=len(contents),
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            summary=summary,
            report_type=report_type,
            status="processed",
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

        # Build response — shape varies by document category
        response = {
            "id": db_report.id,
            "status": "processed",
            "writing_mode": writing_mode,
            "document_category": document_category,
            "classification_confidence": classification_confidence,
            "extracted_text": ocr_text,
            "summary": summary,
            "key_findings": key_findings,
            "abnormal_values": abnormal_values,
            "important_values": parsed.get("important_values", {}),
            "report_type": report_type,
            "ocr_confidence": ocr_confidence,
            "ocr_engine": ocr_data.get("engine", "unknown"),
            "patient_insight": result.get("patient_insight", {}),
            "low_confidence_warning": parsed.get("low_confidence_warning", False),
        }

        # Add lab values with confidence for lab reports
        if document_category == 'laboratory_report':
            response["lab_values"] = parsed.get("lab_values", [])

        # Add prescription data for prescriptions
        if document_category == 'prescription':
            response["prescription_data"] = parsed.get("prescription_data", {})

        # Add imaging data
        if document_category == 'diagnostic_imaging':
            response["imaging_data"] = {
                "findings": parsed.get("sections", {}).get("findings", []),
                "impression": parsed.get("sections", {}).get("impression", ""),
            }

        return response

    except Exception as e:
        logger.error(f"Report upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process report. Please try again.")


@router.get("/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a previously uploaded report."""
    report = db.query(MedicalReport).filter(
        MedicalReport.id == report_id,
        MedicalReport.patient_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "file_name": report.file_name,
        "status": report.status,
        "extracted_text": report.ocr_text,
        "summary": report.summary,
        "report_type": report.report_type,
        "ocr_confidence": report.ocr_confidence,
        "created_at": report.created_at.isoformat() if hasattr(report, "created_at") and report.created_at else None,
    }


@router.post("/{report_id}/summarize")
def summarize_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the summary for a report."""
    report = db.query(MedicalReport).filter(
        MedicalReport.id == report_id,
        MedicalReport.patient_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "summary": report.summary or "No summary available for this report.",
    }
