
import sys, os, importlib.util
from typing import Dict, List
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models')
_spec = importlib.util.spec_from_file_location("bed_inference", os.path.join(MODELS_DIR, 'bed_forecasting', 'inference.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
BedForecastModel = _mod.BedForecastModel


class BedService:
    def __init__(self):
        self.model = BedForecastModel()
        self._loaded = False

    def load_model(self):
        if not self._loaded:
            self._loaded = self.model.load()

    def get_current_status(self, db: Session) -> List[Dict]:
        """Return per-department bed occupancy from the database."""
        from app.db.models.hospital import HospitalBed, Department

        # Get all departments
        departments = db.query(Department).filter(Department.is_active == True).all()

        result = []
        for dept in departments:
            beds = db.query(HospitalBed).filter(HospitalBed.department_id == dept.id).all()
            total = len(beds)
            occupied = len([b for b in beds if b.status == 'occupied'])
            available = len([b for b in beds if b.status == 'available'])
            maintenance = len([b for b in beds if b.status == 'maintenance'])

            # Only include departments that have beds configured
            if total > 0:
                result.append({
                    'department_id': dept.id,
                    'department': {'id': dept.id, 'name': dept.name},
                    'total_capacity': total,
                    'occupied': occupied,
                    'available': available,
                    'maintenance': maintenance,
                    'occupancy_rate': round(occupied / total, 3) if total > 0 else 0.0,
                })

        return result

    def get_summary(self, db: Session) -> Dict:
        """Return overall hospital bed summary."""
        from app.db.models.hospital import HospitalBed

        total = db.query(HospitalBed).count()
        occupied = db.query(HospitalBed).filter(HospitalBed.status == 'occupied').count()
        available = db.query(HospitalBed).filter(HospitalBed.status == 'available').count()

        return {
            'total_beds': total,
            'occupied': occupied,
            'available': available,
            'occupancy_rate': round(occupied / total, 3) if total > 0 else 0.0,
        }

    def get_forecast(self, recent_data=None) -> Dict:
        self.load_model()
        if not recent_data:
            # Use mock recent data (30 days of [admissions, discharges, occupied_beds])
            recent_data = [[10, 8, 400] for _ in range(30)]

        forecast = self.model.predict_7day(recent_data) if self._loaded else [400] * 7

        return {
            'dates': [(datetime.date.today() + datetime.timedelta(days=i)).isoformat() for i in range(1, 8)],
            'predicted_occupied': forecast,
            'predicted_available': [500 - x for x in forecast],
            'warnings': ['High occupancy expected' if x > 450 else 'Normal' for x in forecast],
        }
