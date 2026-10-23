from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.hospital import Department
from app.schemas.hospital import DepartmentCreate, DepartmentResponse
from app.api.deps import require_role
from typing import List

router = APIRouter(prefix="/api/departments", tags=["departments"])

@router.get("/", response_model=List[DepartmentResponse])
def read_departments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Department).offset(skip).limit(limit).all()

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
    db.commit()
    db.refresh(db_department)
    return db_department

@router.put("/{id}", response_model=DepartmentResponse)
def update_department(id: str, department_in: DepartmentCreate, db: Session = Depends(get_db), current_user = Depends(require_role(["admin"]))):
    department = db.query(Department).filter(Department.id == id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    for var, value in vars(department_in).items():
        setattr(department, var, value) if value else None
    db.add(department)
    db.commit()
    db.refresh(department)
    return department
