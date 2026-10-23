"""Data preprocessing for Triage GRU Model."""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os

def load_and_preprocess(data_path: str, artifacts_dir: str):
    df = pd.read_csv(data_path)
    
    # Numeric features
    num_cols = ['symptom_count', 'severity_score', 'duration_hours', 'age', 
                'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 
                'temperature', 'respiratory_rate', 'oxygen_saturation']
    
    scaler = StandardScaler()
    num_features = scaler.fit_transform(df[num_cols])
    
    # Categorical
    le_consc = LabelEncoder()
    consc_encoded = le_consc.fit_transform(df['consciousness_level']).reshape(-1, 1)
    
    # Binary
    bin_cols = ['has_chest_pain', 'has_breathing_difficulty', 'has_severe_bleeding', 'has_loss_of_consciousness']
    bin_features = df[bin_cols].values
    
    # Combine features
    X = np.hstack([num_features, consc_encoded, bin_features])
    
    # Target
    target_map = {'Emergency': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    y = df['urgency_label'].map(target_map).values
    
    # Save scalers/encoders
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(artifacts_dir, 'scaler.joblib'))
    joblib.dump(le_consc, os.path.join(artifacts_dir, 'le_consc.joblib'))
    
    # Split
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.1765, random_state=42) # 0.85 * 0.1765 = 0.15
    
    return (X_train, y_train), (X_val, y_val), (X_test, y_test), X.shape[1]
