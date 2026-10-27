from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models.hospital import Doctor, DoctorSchedule, Department, Appointment
from app.db.models.user import User
from app.schemas.hospital import ScheduleResponse, ScheduleCreate
from app.api.deps import get_current_user, require_role
from typing import List, Optional
from datetime import datetime, date

router = APIRouter(prefix="/api/doctors", tags=["doctors"])

@router.get("/me/stats")
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for the logged-in doctor.

    Demo Doctor (doctor@demo.com) gets hardcoded demo values.
    All other doctors get real database-backed statistics.
    """
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")

    # Find the Doctor record for this user
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    # Real doctor — query actual database
    if not doctor:
        # User has role=doctor but no Doctor row (e.g. registered via /register without admin)
        return {
            "appointments_today": 0,
            "pending_reports": 0,
            "total_patients": 0,
            "is_demo": False,
        }

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Appointments today for this doctor (non-cancelled)
    appointments_today = db.query(func.count(Appointment.id)).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today_start,
        Appointment.appointment_date <= today_end,
        Appointment.status != "cancelled",
    ).scalar() or 0

    # Total unique patients (distinct patient_id across all appointments)
    total_patients = db.query(func.count(func.distinct(Appointment.patient_id))).filter(
        Appointment.doctor_id == doctor.id,
    ).scalar() or 0

    # Pending reports: no doctor_id on medical_reports table, so this is 0
    # (documented assumption in implementation plan)
    pending_reports = 0

    return {
        "appointments_today": appointments_today,
        "pending_reports": pending_reports,
        "total_patients": total_patients,
        "is_demo": False,
    }


@router.get("/")
def read_doctors(department_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Doctor)
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    doctors = query.offset(skip).limit(limit).all()

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


@router.get("/{id}")
def read_doctor(id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    user = db.query(User).filter(User.id == doctor.user_id).first()
    dept = db.query(Department).filter(Department.id == doctor.department_id).first()
    return {
        "id": doctor.id,
        "user_id": doctor.user_id,
        "department_id": doctor.department_id,
        "full_name": user.full_name if user else "Unknown",
        "email": user.email if user else "",
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "is_available": doctor.is_available,
        "department_name": dept.name if dept else "Unknown",
    }


@router.get("/{id}/schedule", response_model=List[ScheduleResponse])
def read_doctor_schedule(id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == id).all()


@router.post("/{id}/schedule", response_model=ScheduleResponse)
def create_doctor_schedule(id: str, schedule: ScheduleCreate, db: Session = Depends(get_db), current_user=Depends(require_role(["admin", "doctor"]))):
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if current_user.role == "doctor" and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Doctors can only manage their own schedules")
    if schedule.doctor_id != id:
        raise HTTPException(status_code=400, detail="Schedule doctor_id must match the URL")
    if not 1 <= schedule.day_of_week <= 7:
        raise HTTPException(status_code=422, detail="day_of_week must be between 1 (Monday) and 7 (Sunday)")
    try:
        start = datetime.strptime(schedule.start_time, "%H:%M").time()
        end = datetime.strptime(schedule.end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=422, detail="Schedule times must use HH:MM format")
    if start >= end or not 5 <= schedule.slot_duration_minutes <= 240:
        raise HTTPException(status_code=422, detail="Schedule time range or slot duration is invalid")
    schedule_data = schedule.model_dump(exclude={"doctor_id"})
    db_schedule = DoctorSchedule(**schedule_data, doctor_id=id)
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule
