"""
Appointment Service — provides real DB-based slot recommendations.

The ML-based recommender (AppointmentRecommender) is loaded lazily and
only used if the artifact is present. When absent, a rule-based fallback
generates real candidate slots from the database using doctor schedules.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import datetime
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models')


class AppointmentService:
    def __init__(self):
        self._recommender = None
        self._ml_loaded = False
        self._ml_attempted = False

    def _ensure_ml(self):
        """Lazy-load the ML recommender; silently skip if artifact is absent."""
        if self._ml_attempted:
            return
        self._ml_attempted = True
        try:
            spec = importlib.util.spec_from_file_location(
                "appt_inference",
                os.path.join(MODELS_DIR, 'appointment_recommendation', 'inference.py'),
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            rec = mod.AppointmentRecommender()
            if rec.load():
                self._recommender = rec
                self._ml_loaded = True
                logger.info('Appointment recommendation ML model loaded')
            else:
                logger.info('Appointment recommendation model artifact missing — using rule-based fallback')
        except Exception as e:
            logger.info(f'Appointment recommendation ML model not available ({e}) — using rule-based fallback')

    def get_recommendations(
        self,
        department_id: str,
        patient_id: str,
        urgency: str,
        db,
    ) -> List[Dict]:
        """
        Return up to 5 recommended appointment slots for the given department.

        Uses real DB data (DoctorSchedule + existing appointments) to find
        free slots. Optionally scores them with the ML model if available.
        """
        self._ensure_ml()

        from app.db.models.hospital import Doctor, DoctorSchedule, Appointment, Department
        from app.db.models.user import User

        today = datetime.date.today()
        # Look ahead up to 14 days
        lookahead_days = 14

        # Get all doctors in the department that are available
        doctors = (
            db.query(Doctor)
            .filter(Doctor.department_id == department_id, Doctor.is_available == True)
            .all()
        )
        if not doctors:
            return []

        dept = db.query(Department).filter(Department.id == department_id).first()
        dept_name = dept.name if dept else 'Unknown'

        candidates: List[Dict] = []

        for doctor in doctors:
            doctor_user = db.query(User).filter(User.id == doctor.user_id).first()
            doctor_name = doctor_user.full_name if doctor_user else 'Doctor'

            # Get the doctor's weekly schedule
            schedules = (
                db.query(DoctorSchedule)
                .filter(DoctorSchedule.doctor_id == doctor.id, DoctorSchedule.is_active == True)
                .all()
            )
            if not schedules:
                continue

            # Build a map of day_of_week → schedule slots
            schedule_map: Dict[int, List[DoctorSchedule]] = {}
            for s in schedules:
                schedule_map.setdefault(s.day_of_week, []).append(s)

            # Get existing appointments for this doctor in the lookahead window
            window_start = datetime.datetime.combine(today, datetime.time.min)
            window_end = window_start + datetime.timedelta(days=lookahead_days)
            existing = (
                db.query(Appointment)
                .filter(
                    Appointment.doctor_id == doctor.id,
                    Appointment.appointment_date >= window_start,
                    Appointment.appointment_date <= window_end,
                    Appointment.status == 'scheduled',
                )
                .all()
            )
            booked_slots = {
                (a.appointment_date.date(), a.time_slot)
                for a in existing
            }

            # Walk through the next 14 days and generate free slots
            for offset in range(1, lookahead_days + 1):
                check_date = today + datetime.timedelta(days=offset)
                # DoctorSchedule uses 1=Mon … 7=Sun, matching the seed data.
                dow = check_date.weekday() + 1
                day_slots = schedule_map.get(dow, [])

                for sched in day_slots:
                    # Generate hourly slots within the schedule window
                    try:
                        start_h, start_m = map(int, sched.start_time.split(':'))
                        end_h, end_m = map(int, sched.end_time.split(':'))
                    except (ValueError, AttributeError):
                        continue

                    slot_duration = sched.slot_duration_minutes or 30
                    if slot_duration <= 0:
                        continue
                    current = datetime.datetime(
                        check_date.year, check_date.month, check_date.day,
                        start_h, start_m,
                    )
                    end_dt = datetime.datetime(
                        check_date.year, check_date.month, check_date.day,
                        end_h, end_m,
                    )

                    while current < end_dt:
                        time_str = current.strftime('%H:%M')
                        if (check_date, time_str) not in booked_slots:
                            candidates.append({
                                'date': check_date.isoformat(),
                                'time': time_str,
                                'doctor_id': doctor.id,
                                'doctor_name': doctor_name,
                                'department_id': department_id,
                                'department_name': dept_name,
                                'specialization': doctor.specialization or dept_name,
                                'day_of_week': dow,
                                'hour': current.hour,
                                'urgency': urgency,
                                # ML scoring fields
                                'department_encoded': 1,
                                'appointment_type_encoded': 1,
                                'urgency_encoded': 1 if urgency in ('medium', 'high') else 0,
                            })
                        current += datetime.timedelta(minutes=slot_duration)

                        if len(candidates) >= 50:
                            break
                    if len(candidates) >= 50:
                        break
                if len(candidates) >= 50:
                    break

        if not candidates:
            return []

        # Score with ML model if available, otherwise rank by urgency + date proximity
        if self._ml_loaded and self._recommender:
            try:
                scored = self._recommender.score_slots(candidates)
                return scored[:5]
            except Exception as e:
                logger.warning(f'ML scoring failed ({e}), using rule-based ranking')

        # Rule-based ranking: prefer sooner dates, prioritise urgency
        candidates.sort(key=lambda c: (c['date'], c['time']))
        return candidates[:5]
