from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.hospital import Department
from app.schemas.hospital import DepartmentCreate, DepartmentResponse
from app.api.deps import require_role
from typing import List
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/departments", tags=["departments"])

@router.get("/", response_model=List[DepartmentResponse])
def read_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return db.query(Department).filter(Department.is_active.is_(True)).offset(skip).limit(min(limit, 200)).all()


@router.get("/admin/all", response_model=List[DepartmentResponse])
def read_all_departments(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"])),
):
    return db.query(Department).order_by(Department.name).all()

@router.get("/{id}", response_model=DepartmentResponse)
def read_department(id: str, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department

@router.post("/", response_model=DepartmentResponse)
def create_department(department: DepartmentCreate, db: Session = Depends(get_db), current_user = Depends(require_role(["admin"]))):
    db_department = Department(**department.model_dump())
    db.add(db_department)
    db.flush()
    record_audit(db, user_id=current_user.id, action="department.created", resource_type="department", resource_id=db_department.id, details={"name": db_department.name})
    db.commit()
    db.refresh(db_department)
    return db_department

@router.put("/{id}", response_model=DepartmentResponse)
def update_department(id: str, department_in: DepartmentCreate, db: Session = Depends(get_db), current_user = Depends(require_role(["admin"]))):
    department = db.query(Department).filter(Department.id == id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    for field, value in department_in.model_dump().items():
        setattr(department, field, value)
    record_audit(db, user_id=current_user.id, action="department.updated", resource_type="department", resource_id=department.id, details={"name": department.name, "is_active": department.is_active})
    db.commit()
    db.refresh(department)
    return department
