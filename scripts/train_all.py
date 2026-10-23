"""Train all ML models for the Smart Hospital Management System."""
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS = [
    ('Disease Prediction (XGBoost)', 'models/disease_prediction', 'train.py'),
    ('Symptom Checker (GRU)', 'models/symptom_checker', 'train.py'),
    ('Bed Forecasting (LSTM)', 'models/bed_forecasting', 'train.py'),
    ('Appointment Recommendation (XGBoost)', 'models/appointment_recommendation', 'train.py'),
    ('Triage (GRU)', 'models/triage', 'train.py'),
    ('Prescription NER', 'models/prescription', 'train.py'),
]

def train_all():
    for name, directory, script in MODELS:
        print(f'\n{"="*60}')
        print(f'Training: {name}')
        print(f'{"="*60}')
        model_dir = os.path.join(PROJECT_ROOT, directory)
        
        # Check if directory and script exist
        if not os.path.exists(os.path.join(model_dir, script)):
            print(f'⚠️ Skipping {name}: Script {script} not found in {directory}')
            continue
            
        result = subprocess.run(
            [sys.executable, script],
            cwd=model_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f'✅ {name} trained successfully')
            print(result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
        else:
            print(f'❌ {name} training failed')
            print(result.stderr[-300:] if len(result.stderr) > 300 else result.stderr)

if __name__ == '__main__':
    train_all()
