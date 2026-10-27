from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Index, text
from app.db.base import Base, BaseModel

class Department(Base, BaseModel):
    __tablename__ = 'departments'
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    floor = Column(String(50))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)

class Doctor(Base, BaseModel):
    __tablename__ = 'doctors'
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=False)
    specialization = Column(String(255))
    qualification = Column(String(255))
    experience_years = Column(Integer)
    is_available = Column(Boolean, default=True)

class DoctorSchedule(Base, BaseModel):
    __tablename__ = 'doctor_schedules'
    doctor_id = Column(String(36), ForeignKey('doctors.id'), nullable=False)
    day_of_week = Column(Integer, nullable=False) # 1=Monday … 7=Sunday
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    slot_duration_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

class Appointment(Base, BaseModel):
    __tablename__ = 'appointments'
    __table_args__ = (
        Index(
            'uq_appointment_active_doctor_slot',
            'doctor_id',
            'appointment_date',
            unique=True,
            sqlite_where=text("status = 'scheduled'"),
            postgresql_where=text("status = 'scheduled'"),
        ),
    )
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    doctor_id = Column(String(36), ForeignKey('doctors.id'), nullable=False)
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    time_slot = Column(String(10), nullable=False)
    appointment_type = Column(String(50)) # checkup/followup/consultation/emergency
    status = Column(String(50), default='scheduled') # scheduled/completed/cancelled/no_show
    urgency = Column(String(50), default='low') # low/medium/high/emergency
    notes = Column(String(1000))

class HospitalBed(Base, BaseModel):
    __tablename__ = 'hospital_beds'
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=False)
    bed_number = Column(String(50), nullable=False)
    bed_type = Column(String(50)) # general/icu/private/semi_private
    status = Column(String(50), default='available') # available/occupied/maintenance/reserved

class BedOccupancy(Base, BaseModel):
    __tablename__ = 'bed_occupancy'
    bed_id = Column(String(36), ForeignKey('hospital_beds.id'), nullable=False)
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    admission_date = Column(DateTime, nullable=False)
    expected_discharge_date = Column(DateTime)
    actual_discharge_date = Column(DateTime)
    status = Column(String(50), default='admitted') # admitted/discharged/transferred

class QueueEntry(Base, BaseModel):
    __tablename__ = 'queue_entries'
    patient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=False)
    queue_number = Column(Integer, nullable=False)
    priority = Column(String(50), default='medium') # emergency/high/medium/low
    status = Column(String(50), default='waiting') # waiting/in_progress/completed/cancelled
    check_in_time = Column(DateTime)
    estimated_wait_minutes = Column(Integer)
    called_at = Column(DateTime)
    completed_at = Column(DateTime)
    notes = Column(String(1000))
