
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.hospital import Appointment, Doctor, Department
from app.services.appointment_service import AppointmentService
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, time
import uuid

router = APIRouter(prefix="/api/appointments", tags=["appointments"])
appointment_service = AppointmentService()


class AppointmentCreate(BaseModel):
    department_id: str
    doctor_id: str
    date: str          # "YYYY-MM-DD"
    time: str          # "HH:MM"
    reason: Optional[str] = ""


class RecommendRequest(BaseModel):
    department_id: str
    urgency: Optional[str] = "low"  # low | medium | high | emergency


@router.get("/")
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List appointments for the current user."""
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == current_user.id
    ).order_by(Appointment.appointment_date.desc()).all()

    result = []
    for apt in appointments:
        doctor = db.query(Doctor).filter(Doctor.id == apt.doctor_id).first()
        dept = db.query(Department).filter(Department.id == apt.department_id).first()
        doctor_user = None
        if doctor:
            doctor_user = db.query(User).filter(User.id == doctor.user_id).first()
        result.append({
            "id": apt.id,
            "appointment_date": apt.appointment_date.isoformat() if apt.appointment_date else None,
            "appointment_time": apt.time_slot if hasattr(apt, 'time_slot') else None,
            "status": apt.status,
            "reason": apt.notes or "",
            "doctor": {"full_name": doctor_user.full_name if doctor_user else "Unknown"},
            "department": {"name": dept.name if dept else "Unknown"},
        })
    return result


@router.post("/")
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Book a new appointment with validation."""
    # 1. Verify doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # 2. Verify doctor is available
    if not doctor.is_available:
        raise HTTPException(status_code=400, detail="This doctor is currently not available for appointments")

    # 3. Verify department matches doctor's actual department
    if data.department_id != doctor.department_id:
        raise HTTPException(
            status_code=400,
            detail="Department mismatch: the selected doctor does not belong to the selected department"
        )

    apt = Appointment(
        id=str(uuid.uuid4()),
        patient_id=current_user.id,
        doctor_id=data.doctor_id,
        department_id=doctor.department_id,  # always use doctor's real department
        appointment_date=datetime.strptime(data.date, "%Y-%m-%d"),
        time_slot=data.time,
        appointment_type="consultation",
        status="scheduled",
        urgency="low",
        notes=data.reason or "",
    )

    db.add(apt)
    db.commit()
    db.refresh(apt)
    return {"id": apt.id, "status": "scheduled", "message": "Appointment booked successfully"}


@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel an appointment."""
    apt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_user.id
    ).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    apt.status = "cancelled"
    db.commit()
    return {"message": "Appointment cancelled"}


@router.post("/recommend")
def recommend_slots(
    data: RecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return up to 5 recommended available appointment slots."""
    slots = appointment_service.get_recommendations(
        department_id=data.department_id,
        patient_id=current_user.id,
        urgency=data.urgency or "low",
        db=db,
    )
    return {"slots": slots, "count": len(slots)}
