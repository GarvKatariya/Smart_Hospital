"""
Smart Hospital Management System - Synthetic Data Generator
Generates synthetic datasets for ML training and forecasting models.
All data generated is completely synthetic.
"""

import os
import random
import csv
from datetime import datetime, timedelta

# Set random seed for reproducibility
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'synthetic')

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def generate_bed_forecasting_data():
    out_dir = os.path.join(DATA_DIR, 'beds')
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, 'daily_occupancy.csv')
    
    departments = [
        ("Cardiology", 30),
        ("Neurology", 25),
        ("Orthopedics", 25),
        ("Pediatrics", 20),
        ("General Medicine", 40),
        ("Dermatology", 10),
        ("ENT", 15),
        ("Emergency Medicine", 35)
    ]
    
    start_date = datetime.now() - timedelta(days=730)
    
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'department', 'admissions', 'discharges', 'occupied_beds', 'available_beds', 'total_beds', 'occupancy_rate'])
        
        for dept_name, total_beds in departments:
            current_occupied = int(total_beds * 0.7) # Start at 70%
            
            for day in range(730):
                current_date = start_date + timedelta(days=day)
                is_weekend = current_date.weekday() >= 5
                
                # Seasonality (higher in winter - Dec/Jan/Feb)
                month = current_date.month
                season_factor = 1.2 if month in [12, 1, 2] else 1.0
                
                # Weekend factor (fewer admissions on weekends usually, except Emergency)
                weekend_factor = 0.8 if is_weekend and dept_name != "Emergency Medicine" else 1.1
                
                # Base rates
                base_admissions = int(total_beds * 0.1 * season_factor * weekend_factor)
                base_discharges = int(total_beds * 0.1) # Discharges more steady
                
                # Add noise
                admissions = max(0, int(random.gauss(base_admissions, 2)))
                discharges = max(0, int(random.gauss(base_discharges, 2)))
                
                # Calculate new occupied, clamped to [0, total_beds]
                new_occupied = current_occupied + admissions - discharges
                new_occupied = max(0, min(new_occupied, total_beds))
                
                # Realized admissions/discharges based on limits
                actual_admissions = new_occupied - current_occupied + discharges
                
                current_occupied = new_occupied
                available = total_beds - current_occupied
                rate = round(current_occupied / total_beds, 4)
                
                writer.writerow([
                    current_date.strftime('%Y-%m-%d'),
                    dept_name,
                    actual_admissions,
                    discharges,
                    current_occupied,
                    available,
                    total_beds,
                    rate
                ])
                
    print(f"Generated bed forecasting data at {out_path}")

def generate_appointment_history_data():
    out_dir = os.path.join(DATA_DIR, 'appointments')
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, 'appointment_history.csv')
    
    departments = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "General Medicine", "Dermatology", "ENT"]
    
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'appointment_id', 'patient_age', 'patient_gender', 'department', 'doctor_id', 
            'day_of_week', 'hour', 'appointment_type', 'urgency', 'duration_minutes', 
            'was_completed', 'was_no_show', 'wait_time_minutes', 'doctor_workload', 'patient_preferred_hour'
        ])
        
        for i in range(5000):
            dept = random.choice(departments)
            age = int(random.gauss(45, 20))
            age = max(1, min(100, age))
            if dept == "Pediatrics":
                age = random.randint(1, 16)
                
            hour = random.randint(9, 16)
            is_no_show = random.random() < 0.15 # 15% no show rate
            
            writer.writerow([
                f"APT-{i+1:05d}",
                age,
                random.choice(['M', 'F']),
                dept,
                f"DOC-{random.randint(1, 15)}",
                random.randint(1, 5), # Mon-Fri
                hour,
                random.choice(['checkup', 'followup', 'consultation']),
                random.choice(['low', 'medium', 'high']),
                random.choice([15, 30, 45, 60]),
                int(not is_no_show),
                int(is_no_show),
                int(random.expovariate(1/15)) if not is_no_show else 0, # wait time avg 15 mins
                random.randint(1, 10), # doctor workload score
                random.randint(9, 16)
            ])
            
    print(f"Generated appointment history data at {out_path}")

def generate_triage_data():
    out_dir = os.path.join(DATA_DIR, 'triage')
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, 'triage_dataset.csv')
    
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'symptoms_text', 'symptom_count', 'severity_score', 'duration_hours', 'age', 
            'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 
            'temperature', 'respiratory_rate', 'oxygen_saturation', 'consciousness_level', 
            'has_chest_pain', 'has_breathing_difficulty', 'has_severe_bleeding', 
            'has_loss_of_consciousness', 'urgency_label'
        ])
        
        for i in range(2000):
            # Base generation
            age = random.randint(1, 90)
            
            # 20% Emergency, 30% High, 30% Medium, 20% Low roughly
            scenario = random.choices(['emergency', 'high', 'medium', 'low'], weights=[0.2, 0.3, 0.3, 0.2])[0]
            
            if scenario == 'emergency':
                hr = random.randint(120, 160)
                sys_bp = random.choice([random.randint(70, 85), random.randint(180, 220)])
                dia_bp = int(sys_bp * 0.6)
                temp = random.choice([random.uniform(35.0, 36.0), random.uniform(39.5, 41.0)])
                resp = random.randint(25, 40)
                spo2 = random.randint(80, 92)
                consc = random.choices(['alert', 'verbal', 'pain', 'unresponsive'], weights=[0.1, 0.3, 0.4, 0.2])[0]
                chest_pain = 1 if random.random() < 0.4 else 0
                breath = 1 if random.random() < 0.5 else 0
                bleed = 1 if random.random() < 0.2 else 0
                loc = 1 if consc != 'alert' else 0
                sev = random.randint(8, 10)
                label = 'Emergency'
            elif scenario == 'high':
                hr = random.randint(100, 120)
                sys_bp = random.randint(140, 180)
                dia_bp = int(sys_bp * 0.6)
                temp = random.uniform(38.5, 39.5)
                resp = random.randint(20, 25)
                spo2 = random.randint(93, 95)
                consc = 'alert'
                chest_pain = 1 if random.random() < 0.1 else 0
                breath = 1 if random.random() < 0.2 else 0
                bleed = 0
                loc = 0
                sev = random.randint(6, 8)
                label = 'High'
            elif scenario == 'medium':
                hr = random.randint(80, 100)
                sys_bp = random.randint(120, 140)
                dia_bp = int(sys_bp * 0.6)
                temp = random.uniform(37.5, 38.5)
                resp = random.randint(16, 20)
                spo2 = random.randint(96, 98)
                consc = 'alert'
                chest_pain = 0
                breath = 0
                bleed = 0
                loc = 0
                sev = random.randint(4, 6)
                label = 'Medium'
            else:
                hr = random.randint(60, 80)
                sys_bp = random.randint(110, 120)
                dia_bp = int(sys_bp * 0.6)
                temp = random.uniform(36.5, 37.5)
                resp = random.randint(12, 16)
                spo2 = random.randint(98, 100)
                consc = 'alert'
                chest_pain = 0
                breath = 0
                bleed = 0
                loc = 0
                sev = random.randint(1, 3)
                label = 'Low'
                
            writer.writerow([
                f"Synthetic symptom text {i}",
                random.randint(1, 5),
                sev,
                random.randint(1, 72),
                age,
                hr, sys_bp, dia_bp, round(temp, 1), resp, spo2, consc,
                chest_pain, breath, bleed, loc, label
            ])

    print(f"Generated triage dataset at {out_path}")

if __name__ == "__main__":
    print("Starting synthetic data generation...")
    generate_bed_forecasting_data()
    generate_appointment_history_data()
    generate_triage_data()
    print("All synthetic datasets generated successfully.")
