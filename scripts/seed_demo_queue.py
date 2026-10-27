"""Add clearly labeled synthetic queue records for local demonstration."""

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.models.hospital import Department, QueueEntry
from app.db.models.user import User
from app.db.session import SessionLocal


DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "demo_queue.json")
DEMO_PREFIX = "DEMO_QUEUE:"


def main() -> None:
    with open(DATA_FILE, encoding="utf-8") as file:
        data = json.load(file)

    db = SessionLocal()
    try:
        existing = db.query(QueueEntry).filter(QueueEntry.notes.like(f"{DEMO_PREFIX}%")).count()
        if existing:
            print(f"Demo queue already loaded ({existing} records); no changes made.")
            return

        department = db.query(Department).filter(
            Department.name == data["department"], Department.is_active.is_(True)
        ).first()
        if not department:
            raise SystemExit(
                f"Active '{data['department']}' department not found. Seed the base demo database first."
            )

        now = datetime.utcnow()
        entries = data["entries"]
        for queue_number, item in enumerate(entries, start=1):
            patient = db.query(User).filter(
                User.email == item["patient_email"], User.role == "patient"
            ).first()
            if not patient:
                raise SystemExit(
                    f"Demo patient {item['patient_email']} not found. Seed the base demo database first."
                )
            db.add(QueueEntry(
                patient_id=patient.id,
                department_id=department.id,
                queue_number=queue_number,
                priority=item["priority"],
                status=item["status"],
                check_in_time=now - timedelta(minutes=item["minutes_ago"]),
                estimated_wait_minutes=item["estimated_wait_minutes"],
                notes=f"{DEMO_PREFIX}{item['notes']}",
            ))
        db.commit()
        print(f"Loaded {len(entries)} synthetic queue entries for {department.name}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
