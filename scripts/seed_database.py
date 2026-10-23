"""
Smart Hospital Management System - Database Seeder
Creates demo data for development and demonstration.
All data is synthetic and clearly labeled as such.
"""

import sys
import os
import random
from datetime import datetime, timedelta
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.base import Base, engine
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.hospital import Department, Doctor, DoctorSchedule, Appointment, HospitalBed, BedOccupancy, QueueEntry
from app.db.models.ai_models import SymptomCheck, DiseasePrediction, ModelVersion
from app.core.security import hash_password

def seed_database():
    print("Starting database seeding process...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if already seeded
        admin_exists = db.query(User).filter(User.email == "admin@demo.com").first()
        if admin_exists:
            print("Database already seeded (found admin@demo.com). Exiting.")
            return

        print("Seeding Users...")
        default_pwd = hash_password("Demo@123")
        
        # Base Demo Users
        admin_user = User(email="admin@demo.com", role="admin", full_name="Admin User", hashed_password=default_pwd)
        patient_user = User(email="patient@demo.com", role="patient", full_name="Demo Patient", hashed_password=default_pwd)
        doctor_user = User(email="doctor@demo.com", role="doctor", full_name="Dr. Demo Doctor", hashed_password=default_pwd)
        
        db.add_all([admin_user, patient_user, doctor_user])
        db.commit()

        # Extra Patients
        patient_names = ["Priya Sharma", "Rahul Patel", "Anita Gupta", "Vikram Singh", "Meera Nair"]
        extra_patients = []
        for name in patient_names:
            email = name.lower().replace(" ", ".") + "@demo.com"
            user = User(email=email, role="patient", full_name=name, hashed_password=default_pwd)
            db.add(user)
            extra_patients.append(user)
        db.commit()
        all_patients = [patient_user] + extra_patients

        print("Seeding Departments...")
        departments_data = [
            ("Cardiology", "Heart and cardiovascular system"),
            ("Neurology", "Nervous system disorders"),
            ("Orthopedics", "Bone and joint care"),
            ("Pediatrics", "Child medical care"),
            ("General Medicine", "Primary care and general health"),
            ("Dermatology", "Skin care"),
            ("ENT", "Ear, Nose, and Throat"),
            ("Emergency Medicine", "Urgent and critical care")
        ]
        
        departments_map = {}
        for name, desc in departments_data:
            dept = Department(name=name, description=desc, floor=f"Floor {random.randint(1, 4)}", phone=f"555-01{random.randint(10,99)}")
            db.add(dept)
            departments_map[name] = dept
        db.commit()

        print("Seeding Doctors...")
        doctor_data = [
            ("Dr. Arun Sharma", "Cardiology"),
            ("Dr. Sneha Patel", "Cardiology"),
            ("Dr. Rajesh Kumar", "Neurology"),
            ("Dr. Priya Menon", "Neurology"),
            ("Dr. Suresh Iyer", "Orthopedics"),
            ("Dr. Kavita Reddy", "Orthopedics"),
            ("Dr. Amit Verma", "Pediatrics"),
            ("Dr. Deepika Nair", "Pediatrics"),
            ("Dr. Vikram Joshi", "General Medicine"),
            ("Dr. Anjali Desai", "General Medicine"),
            ("Dr. Manoj Tiwari", "Dermatology"),
            ("Dr. Ritu Kapoor", "Dermatology"),
            ("Dr. Sanjay Gupta", "ENT"),
            ("Dr. Neha Saxena", "ENT"),
            ("Dr. Arjun Malhotra", "Emergency Medicine")
        ]
        
        doctors_list = []
        for doc_name, dept_name in doctor_data:
            email = doc_name.lower().replace(" ", ".").replace("dr.", "dr") + "@demo.com"
            user = User(email=email, role="doctor", full_name=doc_name, hashed_password=default_pwd)
            db.add(user)
            db.commit()
            
            dept = departments_map[dept_name]
            doctor = Doctor(user_id=user.id, department_id=dept.id, specialization=dept_name, experience_years=random.randint(3, 25))
            db.add(doctor)
            doctors_list.append(doctor)
            
            if doc_name == "Dr. Arun Sharma":
                doctor_user_profile = Doctor(user_id=doctor_user.id, department_id=dept.id, specialization=dept_name, experience_years=10)
                db.add(doctor_user_profile)
                doctors_list.append(doctor_user_profile)

        db.commit()

        print("Seeding Doctor Schedules...")
        for doc in doctors_list:
            for day in range(1, 6): # Mon-Fri
                # Morning slot
                db.add(DoctorSchedule(doctor_id=doc.id, day_of_week=day, start_time="09:00", end_time="13:00"))
                # Afternoon slot
                db.add(DoctorSchedule(doctor_id=doc.id, day_of_week=day, start_time="14:00", end_time="17:00"))
        db.commit()

        print("Seeding Hospital Beds...")
        bed_distribution = {
            "Cardiology": {"general": 25, "icu": 5, "private": 0, "semi_private": 0},
            "Neurology": {"general": 20, "icu": 5, "private": 0, "semi_private": 0},
            "Orthopedics": {"general": 20, "icu": 0, "private": 5, "semi_private": 0},
            "Pediatrics": {"general": 15, "icu": 0, "private": 0, "semi_private": 5},
            "General Medicine": {"general": 35, "icu": 0, "private": 5, "semi_private": 0},
            "Dermatology": {"general": 10, "icu": 0, "private": 0, "semi_private": 0},
            "ENT": {"general": 12, "icu": 0, "private": 3, "semi_private": 0},
            "Emergency Medicine": {"general": 20, "icu": 15, "private": 0, "semi_private": 0},
        }

        all_beds = []
        for dept_name, dist in bed_distribution.items():
            dept = departments_map[dept_name]
            bed_counter = 1
            for b_type, count in dist.items():
                for _ in range(count):
                    bed = HospitalBed(
                        department_id=dept.id, 
                        bed_number=f"{dept.name[:3].upper()}-{bed_counter:03d}",
                        bed_type=b_type
                    )
                    db.add(bed)
                    all_beds.append(bed)
                    bed_counter += 1
        db.commit()

        print("Seeding Bed Occupancies...")
        # Randomly occupy ~60 beds
        occupied_beds = random.sample(all_beds, 60)
        for bed in occupied_beds:
            bed.status = 'occupied'
            patient = random.choice(all_patients)
            admit_date = datetime.utcnow() - timedelta(days=random.randint(1, 10))
            expected_discharge = admit_date + timedelta(days=random.randint(3, 14))
            
            occupancy = BedOccupancy(
                bed_id=bed.id,
                patient_id=patient.id,
                admission_date=admit_date,
                expected_discharge_date=expected_discharge,
                status='admitted'
            )
            db.add(occupancy)
        db.commit()

        print("Seeding Appointments...")
        now = datetime.utcnow()
        # 50 historical appointments
        for _ in range(50):
            patient = random.choice(all_patients)
            doctor = random.choice(doctors_list)
            appt_date = now - timedelta(days=random.randint(1, 30))
            status = random.choice(['completed', 'completed', 'completed', 'cancelled', 'no_show'])
            db.add(Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                department_id=doctor.department_id,
                appointment_date=appt_date,
                time_slot=f"{random.randint(9, 16):02d}:00",
                status=status,
                appointment_type=random.choice(['checkup', 'followup'])
            ))
            
        # 10 upcoming appointments
        for _ in range(10):
            patient = random.choice(all_patients)
            doctor = random.choice(doctors_list)
            appt_date = now + timedelta(days=random.randint(1, 14))
            db.add(Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                department_id=doctor.department_id,
                appointment_date=appt_date,
                time_slot=f"{random.randint(9, 16):02d}:00",
                status='scheduled',
                appointment_type='checkup'
            ))
        db.commit()

        print("Seeding Queue Entries...")
        for i in range(8):
            patient = random.choice(all_patients)
            dept = random.choice(list(departments_map.values()))
            db.add(QueueEntry(
                patient_id=patient.id,
                department_id=dept.id,
                queue_number=i+1,
                priority=random.choice(['low', 'medium', 'high', 'emergency']),
                status='waiting',
                check_in_time=now - timedelta(minutes=random.randint(5, 60))
            ))
        db.commit()

        print("Seeding AI Models & Samples...")
        db.add(ModelVersion(model_name="symptom_checker", version="symptom-gru-v1", is_active=True))
        db.add(ModelVersion(model_name="disease_predictor", version="disease-xgboost-v1", is_active=True))

        for _ in range(5):
            db.add(SymptomCheck(
                patient_id=random.choice(all_patients).id,
                symptoms_text="Headache and mild fever",
                predicted_condition="Common Cold",
                confidence=0.85,
                department_recommendation="General Medicine",
                model_version="symptom-gru-v1"
            ))

        for _ in range(3):
            db.add(DiseasePrediction(
                patient_id=random.choice(all_patients).id,
                input_features=json.dumps({"age": 45, "chol": 240}),
                prediction="High Risk of CVD",
                probability=0.72,
                risk_category="High",
                model_version="disease-xgboost-v1"
            ))
        
        db.commit()
        print("Database seeded successfully!")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
