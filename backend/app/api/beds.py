
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal
from app.api.deps import get_db, get_current_user
from sqlalchemy.orm import Session
from app.services.bed_service import BedService
from app.db.models.user import User
from app.api.deps import require_role
from app.db.models.hospital import HospitalBed, Department
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/beds", tags=["Beds"])
bed_service = BedService()

@router.get("/status")
def get_bed_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return bed_service.get_current_status(db)

@router.get("/forecast")
def get_bed_forecast(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return bed_service.get_forecast(db)


class BedStatusUpdate(BaseModel):
    status: Literal['available', 'occupied', 'maintenance', 'reserved']


@router.get('/inventory')
def get_bed_inventory(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    beds = db.query(HospitalBed, Department).join(
        Department, HospitalBed.department_id == Department.id
    ).order_by(Department.name, HospitalBed.bed_number).all()
    return [{
        'id': bed.id,
        'department_id': bed.department_id,
        'department_name': department.name,
        'bed_number': bed.bed_number,
        'bed_type': bed.bed_type,
        'status': bed.status,
    } for bed, department in beds]


@router.patch('/inventory/{bed_id}', dependencies=[Depends(require_role(['admin']))])
def update_bed_status(
    bed_id: str,
    request: BedStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bed = db.query(HospitalBed).filter(HospitalBed.id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail='Bed not found')
    previous_status = bed.status
    bed.status = request.status
    record_audit(
        db,
        user_id=current_user.id,
        action='bed.status_updated',
        resource_type='hospital_bed',
        resource_id=bed.id,
        details={'bed_number': bed.bed_number, 'from': previous_status, 'to': request.status},
    )
    db.commit()
    db.refresh(bed)
    return {'id': bed.id, 'status': bed.status}
