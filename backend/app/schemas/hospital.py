from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    floor: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DoctorBase(BaseModel):
    user_id: str
    department_id: str
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    is_available: bool = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ScheduleBase(BaseModel):
    doctor_id: str
    day_of_week: int
    start_time: str
    end_time: str
    slot_duration_minutes: int = 30
    is_active: bool = True

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AppointmentBase(BaseModel):
    patient_id: str
    doctor_id: str
    department_id: str
    appointment_date: datetime
    time_slot: str
    appointment_type: Optional[str] = None
    status: str = 'scheduled'
    urgency: str = 'low'
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QueueEntryBase(BaseModel):
    patient_id: str
    department_id: str
    queue_number: int
    priority: str = 'medium'
    status: str = 'waiting'
    estimated_wait_minutes: Optional[int] = None
    notes: Optional[str] = None

class QueueEntryCreate(QueueEntryBase):
    pass

class QueueEntryResponse(QueueEntryBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
