import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from app.api.deps import require_role, get_db
from app.db.models.user import User
from app.db.models.hospital import Doctor, Department, Appointment, HospitalBed
from app.db.models.ai_models import ModelVersion, AuditLog
from app.core.security import hash_password
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────

class DoctorCreateRequest(BaseModel):
    full_name: str
    email: str
    password: str
    department_id: str
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None


# ── Doctor CRUD ──────────────────────────────────────────────

@router.get("/doctors", dependencies=[Depends(require_role(["admin"]))])
def list_doctors(db: Session = Depends(get_db)):
    """List all doctors with user and department info."""
    doctors = db.query(Doctor).all()
    result = []
    for doc in doctors:
        user = db.query(User).filter(User.id == doc.user_id).first()
        dept = db.query(Department).filter(Department.id == doc.department_id).first()
        result.append({
            "id": doc.id,
            "user_id": doc.user_id,
            "department_id": doc.department_id,
            "full_name": user.full_name if user else "Unknown",
            "email": user.email if user else "",
            "specialization": doc.specialization,
            "qualification": doc.qualification,
            "experience_years": doc.experience_years,
            "is_available": doc.is_available,
            "department_name": dept.name if dept else "Unknown",
        })
    return result


@router.post("/doctors")
def create_doctor(data: DoctorCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"]))):
    """Create a new doctor: User + Doctor records in one transaction."""

    # 1. Validate department exists
    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Department not found")

    # 2. Check email uniqueness
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    # 3. Create User with role="doctor"
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="doctor",
    )
    db.add(user)
    db.flush()

    # 4. Create Doctor linked to User and Department
    doctor = Doctor(
        id=str(uuid.uuid4()),
        user_id=user.id,
        department_id=data.department_id,
        specialization=data.specialization,
        qualification=data.qualification,
        experience_years=data.experience_years,
        is_available=True,
    )
    db.add(doctor)
    record_audit(db, user_id=current_user.id, action="doctor.created", resource_type="doctor", resource_id=doctor.id, details={"department_id": dept.id, "email": user.email})
    db.commit()
    db.refresh(user)
    db.refresh(doctor)

    return {
        "id": doctor.id,
        "user_id": user.id,
        "department_id": doctor.department_id,
        "full_name": user.full_name,
        "email": user.email,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "is_available": doctor.is_available,
        "department_name": dept.name,
        "message": f"Doctor '{user.full_name}' created successfully",
    }


# ── Stats ────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(require_role(["admin"]))])
def get_stats(db: Session = Depends(get_db)):
    """Return real-time hospital statistics."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    total_patients = db.query(User).filter(User.role == "patient").count()
    total_doctors = db.query(Doctor).count()
    total_departments = db.query(Department).filter(Department.is_active == True).count()
    appointments_today = db.query(Appointment).filter(
        Appointment.appointment_date >= today_start
    ).count()
    total_beds = db.query(HospitalBed).count()
    available_beds = db.query(HospitalBed).filter(HospitalBed.status == "available").count()
    occupied_beds = db.query(HospitalBed).filter(HospitalBed.status == "occupied").count()
    total_appointments = db.query(Appointment).count()
    scheduled_appointments = db.query(Appointment).filter(
        Appointment.status == "scheduled"
    ).count()

    return {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_departments": total_departments,
        "appointments_today": appointments_today,
        "total_appointments": total_appointments,
        "scheduled_appointments": scheduled_appointments,
        "total_beds": total_beds,
        "available_beds": available_beds,
        "occupied_beds": occupied_beds,
        "occupancy_rate": round(occupied_beds / total_beds * 100, 1) if total_beds > 0 else 0.0,
    }


# ── Patients ─────────────────────────────────────────────────

@router.get("/patients", dependencies=[Depends(require_role(["admin"]))])
def get_patients(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all registered patients."""
    patients = db.query(User).filter(User.role == "patient").offset(skip).limit(limit).all()
    total = db.query(User).filter(User.role == "patient").count()

    return {
        "total": total,
        "patients": [
            {
                "id": p.id,
                "full_name": p.full_name,
                "email": p.email,
                "phone": getattr(p, "phone", None),
                "is_active": getattr(p, "is_active", True),
                "created_at": p.created_at.isoformat() if hasattr(p, "created_at") and p.created_at else None,
            }
            for p in patients
        ],
    }


# ── Audit Logs ───────────────────────────────────────────────

@router.get("/audit-logs", dependencies=[Depends(require_role(["admin"]))])
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List recent audit log entries."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(AuditLog).count()
    actor_ids = {log.user_id for log in logs if log.user_id}
    actors = {
        user.id: user.full_name
        for user in db.query(User).filter(User.id.in_(actor_ids)).all()
    } if actor_ids else {}

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "actor_name": actors.get(log.user_id, "System"),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if hasattr(log, "created_at") and log.created_at else None,
            }
            for log in logs
        ],
    }


# ── ML Models ────────────────────────────────────────────────

# Known models in the system with their artifact paths
_KNOWN_MODELS = [
    {"name": "symptom_checker", "display": "Symptom Checker (GRU)", "artifact": "models/symptom_checker/artifacts/symptom_gru_v1.pt"},
    {"name": "disease_prediction", "display": "Disease Prediction (Random Forest)", "artifact": "models/disease_prediction/artifacts/disease_random_forest_v1.joblib"},
    {"name": "triage", "display": "Triage (GRU)", "artifact": "models/triage/artifacts/triage_gru_v1.pt"},
    {"name": "bed_forecasting", "display": "Bed Forecasting (LSTM)", "artifact": "models/bed_forecasting/artifacts/bed_lstm_v1.pt"},
    {"name": "appointment_recommendation", "display": "Appointment Recommendation (XGBoost)", "artifact": "models/appointment_recommendation/artifacts/appointment_xgb_v1.joblib"},
    {"name": "prescription_ner", "display": "Prescription Entity Extraction (Rules)", "artifact": "models/prescription/artifacts/model_config.json", "rule_based": True},
]

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@router.get("/models", dependencies=[Depends(require_role(["admin"]))])
def get_models(db: Session = Depends(get_db)):
    """Return status of all ML models — from DB records if available, otherwise from disk check."""
    db_versions = {mv.model_name: mv for mv in db.query(ModelVersion).all()}

    result = []
    for m in _KNOWN_MODELS:
        artifact_path = os.path.join(_PROJECT_ROOT, m["artifact"])
        artifact_exists = os.path.isfile(artifact_path)

        db_entry = db_versions.get(m["name"])
        is_rule_based = m.get("rule_based", False)
        result.append({
            "name": m["name"],
            "display_name": m["display"],
            "version": (db_entry.version if db_entry and db_entry.version else "rules-v1") if is_rule_based else (db_entry.version if db_entry else ("1.0" if artifact_exists else None)),
            "is_active": artifact_exists if is_rule_based else (db_entry.is_active if db_entry else artifact_exists),
            "artifact_present": artifact_exists,
            "training_date": db_entry.training_date if db_entry else None,
            "metrics": db_entry.metrics if db_entry else None,
        })

    return {"models": result}
