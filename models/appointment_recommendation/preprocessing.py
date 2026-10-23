"""
Appointment Recommendation - Data Preprocessing
Matches the synthetic appointment_history.csv schema.
"""
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os

def load_and_preprocess(data_path, output_dir='artifacts'):
    """Load and preprocess appointment history data."""
    df = pd.read_csv(data_path)
    
    # Encode categorical features
    dept_encoder = LabelEncoder()
    type_encoder = LabelEncoder()
    
    df['department_encoded'] = dept_encoder.fit_transform(df['department'])
    df['appointment_type_encoded'] = type_encoder.fit_transform(df['appointment_type'])
    df['urgency_encoded'] = df['urgency'].map({'low': 0, 'medium': 1, 'high': 2, 'emergency': 3}).fillna(1).astype(int)
    df['gender_encoded'] = df['patient_gender'].map({'M': 1, 'F': 0}).fillna(0).astype(int)
    
    features = [
        'department_encoded', 'day_of_week', 'hour', 
        'appointment_type_encoded', 'urgency_encoded',
        'doctor_workload', 'patient_age', 'gender_encoded',
        'duration_minutes'
    ]
    
    X = df[features].values
    y = df['was_completed'].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(output_dir, 'scaler.pkl'))
    joblib.dump(dept_encoder, os.path.join(output_dir, 'dept_encoder.pkl'))
    joblib.dump(type_encoder, os.path.join(output_dir, 'type_encoder.pkl'))
    
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_scaled, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    return X_train, y_train, X_val, y_val, X_test, y_test

if __name__ == '__main__':
    X_train, y_train, _, _, _, _ = load_and_preprocess(
        '../../data/synthetic/appointments/appointment_history.csv'
    )
    print(f'Training samples: {len(X_train)}, Features: {X_train.shape[1]}')
