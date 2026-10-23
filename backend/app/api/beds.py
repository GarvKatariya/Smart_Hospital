
from fastapi import APIRouter, Depends
from app.api.deps import get_db
from sqlalchemy.orm import Session
from app.services.bed_service import BedService

router = APIRouter(prefix="/api/beds", tags=["Beds"])
bed_service = BedService()

@router.get("/status")
def get_bed_status(db: Session = Depends(get_db)):
    return bed_service.get_current_status(db)

@router.get("/forecast")
def get_bed_forecast():
    return bed_service.get_forecast()
