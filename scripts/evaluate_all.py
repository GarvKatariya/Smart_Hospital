"""Evaluate all ML models for the Smart Hospital Management System."""
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS = [
    ('Disease Prediction (XGBoost)', 'models/disease_prediction', 'evaluate.py'),
    ('Symptom Checker (GRU)', 'models/symptom_checker', 'evaluate.py'),
    ('Bed Forecasting (LSTM)', 'models/bed_forecasting', 'evaluate.py'),
    ('Appointment Recommendation (XGBoost)', 'models/appointment_recommendation', 'evaluate.py'),
    ('Triage (GRU)', 'models/triage', 'evaluate.py'),
    ('Prescription NER', 'models/prescription', 'evaluate.py'),
]

def evaluate_all():
    for name, directory, script in MODELS:
        print(f'\n{"="*60}')
        print(f'Evaluating: {name}')
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
            print(f'✅ {name} evaluated successfully')
            print(result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
        else:
            print(f'❌ {name} evaluation failed')
            print(result.stderr[-300:] if len(result.stderr) > 300 else result.stderr)

if __name__ == '__main__':
    evaluate_all()
