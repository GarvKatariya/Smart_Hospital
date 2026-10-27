
import os, importlib.util, logging
from typing import Dict, List
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.config import settings

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))
logger = logging.getLogger(__name__)
_spec = importlib.util.spec_from_file_location("bed_inference", os.path.join(MODELS_DIR, 'bed_forecasting', 'inference.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
BedForecastModel = _mod.BedForecastModel


class BedService:
    def __init__(self):
        self.model = BedForecastModel(os.path.join(MODELS_DIR, 'bed_forecasting', 'artifacts'))
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

    def get_forecast(self, db: Session) -> Dict:
        """Forecast occupancy from recorded admissions and live bed inventory."""
        from app.db.models.hospital import BedOccupancy, HospitalBed

        beds = db.query(HospitalBed).all()
        total_beds = len(beds)
        current_occupied = sum(1 for bed in beds if bed.status == 'occupied')
        today = datetime.date.today()
        occupancy_records = db.query(BedOccupancy).all()

        recent_data = []
        observed_occupancy = []
        for offset in range(29, -1, -1):
            observed_date = today - datetime.timedelta(days=offset)
            day_end = datetime.datetime.combine(observed_date, datetime.time.max)
            admissions = sum(1 for row in occupancy_records if row.admission_date.date() == observed_date)
            discharges = sum(
                1 for row in occupancy_records
                if row.actual_discharge_date and row.actual_discharge_date.date() == observed_date
            )
            occupied = sum(
                1 for row in occupancy_records
                if row.admission_date <= day_end
                and (row.actual_discharge_date is None or row.actual_discharge_date > day_end)
            )
            recent_data.append([admissions, discharges, occupied])
            observed_occupancy.append(occupied)

        # Admission history may be missing in a freshly seeded database. Use the
        # live inventory as an explicitly identified baseline rather than fake counts.
        history_available = bool(occupancy_records)
        # The LSTM was trained on the imported Hero DMC series and can score the
        # local 30-day window even when the demo database has fewer than 14 event
        # dates. Keep that provenance and its experimental status visible to users.
        model_history_available = bool(occupancy_records)
        if not history_available:
            recent_data = [[0, 0, current_occupied] for _ in range(30)]
            observed_occupancy = [current_occupied] * 30
        else:
            recent_data[-1][2] = current_occupied
            observed_occupancy[-1] = current_occupied

        if model_history_available:
            self.load_model()
        use_model = model_history_available and self._loaded
        source = (
            'LSTM trained on Hero DMC data; scored on local bed history'
            if use_model else 'Local historical trend'
        )
        model_note = None
        if use_model:
            try:
                raw_forecast = self.model.predict_7day(recent_data)
                model_note = (
                    'Experimental forecast: trained on Hero DMC cardiology data, '
                    'not this hospital. Held-out MAE was 21.1 beds versus 17.8 '
                    'for a persistence baseline.'
                )
            except Exception as exc:
                logger.warning('Bed forecast model failed; using observed trend: %s', exc)
                self._loaded = False
                use_model = False
                source = 'Local historical trend (model unavailable)'

        if not use_model:
            recent_changes = [
                observed_occupancy[index] - observed_occupancy[index - 1]
                for index in range(max(1, len(observed_occupancy) - 7), len(observed_occupancy))
            ]
            daily_change = sum(recent_changes) / len(recent_changes) if recent_changes else 0
            raw_forecast = [current_occupied + daily_change * day for day in range(1, 8)]

        predicted = [
            max(0, min(total_beds, int(round(float(value)))))
            for value in raw_forecast[:7]
        ]
        predicted.extend([current_occupied] * (7 - len(predicted)))
        dates = [
            (today + datetime.timedelta(days=offset)).isoformat()
            for offset in range(1, 8)
        ]
        threshold = settings.OCCUPANCY_WARNING_THRESHOLD / 100
        warnings = [
            f'High occupancy expected on {forecast_date}'
            if total_beds and occupied / total_beds >= threshold else 'Normal'
            for forecast_date, occupied in zip(dates, predicted)
        ]

        return {
            'dates': dates,
            'current_occupied': current_occupied,
            'predicted_occupied': predicted,
            'predicted_available': [total_beds - occupied for occupied in predicted],
            'total_beds': total_beds,
            'source': source if history_available else 'Live occupancy baseline (no admission history)',
            'model_note': model_note,
            'warnings': warnings,
        }
