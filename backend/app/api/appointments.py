
from fastapi import APIRouter, Depends, HTTPException
from typing import Literal, Optional
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, require_role
from app.db.models.user import User
from app.db.models.hospital import Appointment, Doctor, DoctorSchedule, Department
from app.services.appointment_service import AppointmentService
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, time
import uuid
from app.services.audit_service import record_audit

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
    urgency: Literal["low", "medium", "high", "emergency"] = "low"


@router.get("/")
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List appointments for the current user."""
    query = db.query(Appointment)
    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            return []
        query = query.filter(Appointment.doctor_id == doctor.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted")

    appointments = query.order_by(Appointment.appointment_date.desc()).all()

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
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can book appointments")

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

    try:
        requested_date = date.fromisoformat(data.date)
        requested_time = time.fromisoformat(data.time)
    except ValueError:
        raise HTTPException(status_code=422, detail="Date or time is invalid")

    appointment_at = datetime.combine(requested_date, requested_time)
    if appointment_at <= datetime.now():
        raise HTTPException(status_code=400, detail="Appointments must be booked for a future time")

    schedules = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor.id,
        DoctorSchedule.is_active.is_(True),
        DoctorSchedule.day_of_week == requested_date.weekday() + 1,
    ).all()
    slot_is_scheduled = False
    for schedule in schedules:
        try:
            start = time.fromisoformat(schedule.start_time)
            end = time.fromisoformat(schedule.end_time)
            duration = schedule.slot_duration_minutes or 30
            start_minutes = start.hour * 60 + start.minute
            requested_minutes = requested_time.hour * 60 + requested_time.minute
            end_minutes = end.hour * 60 + end.minute
            if duration > 0 and start_minutes <= requested_minutes < end_minutes:
                slot_is_scheduled = (requested_minutes - start_minutes) % duration == 0
                if slot_is_scheduled:
                    break
        except (ValueError, TypeError):
            continue
    if not slot_is_scheduled:
        raise HTTPException(status_code=400, detail="The selected time is outside the doctor's schedule")

    existing = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == appointment_at,
        Appointment.status == "scheduled",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This appointment slot is already booked")

    apt = Appointment(
        id=str(uuid.uuid4()),
        patient_id=current_user.id,
        doctor_id=data.doctor_id,
        department_id=doctor.department_id,  # always use doctor's real department
        appointment_date=appointment_at,
        time_slot=requested_time.strftime("%H:%M"),
        appointment_type="consultation",
        status="scheduled",
        urgency="low",
        notes=data.reason or "",
    )

    db.add(apt)
    record_audit(db, user_id=current_user.id, action="appointment.created", resource_type="appointment", resource_id=apt.id, details={"doctor_id": doctor.id, "appointment_date": appointment_at.isoformat()})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This appointment slot is already booked") from exc
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
    record_audit(db, user_id=current_user.id, action="appointment.cancelled", resource_type="appointment", resource_id=apt.id)
    db.commit()
    return {"message": "Appointment cancelled"}


@router.post("/recommend")
def recommend_slots(
    data: RecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["patient"])),
):
    """Return up to 5 recommended available appointment slots."""
    slots = appointment_service.get_recommendations(
        department_id=data.department_id,
        patient_id=current_user.id,
        urgency=data.urgency or "low",
        db=db,
    )
    return {"slots": slots, "count": len(slots)}
