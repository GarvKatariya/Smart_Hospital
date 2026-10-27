
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / 'data/real/beds/hero_dmc_daily.csv'
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / 'artifacts'


def load_and_preprocess(data_path=DEFAULT_DATA_PATH, window_size=30, artifact_dir=DEFAULT_ARTIFACT_DIR):
    df = pd.read_csv(data_path)
    daily = df.groupby('date').agg({
        'admissions': 'sum',
        'discharges': 'sum',
        'occupied_beds': 'sum'
    }).reset_index()
    daily = daily.sort_values('date')

    if daily['date'].duplicated().any():
        raise ValueError('Bed occupancy training data must have one row per date after aggregation')
    if daily[['admissions', 'discharges', 'occupied_beds']].isna().any().any():
        raise ValueError('Bed occupancy training data contains missing feature values')
    if (daily[['admissions', 'discharges', 'occupied_beds']] < 0).any().any():
        raise ValueError('Bed occupancy training data cannot contain negative counts')
    
    features = daily[['admissions', 'discharges', 'occupied_beds']].values
    target = daily['occupied_beds'].values

    horizon = 7
    sample_count = len(daily) - window_size - horizon + 1
    if sample_count < 10:
        raise ValueError(f'Need at least {window_size + horizon + 9} daily rows; found {len(daily)}')
    train_cut = int(len(daily) * 0.7)
    val_cut = int(len(daily) * 0.85)

    # Fit normalization only on the chronological training window to avoid
    # leaking validation/test information into model training.
    scaler = MinMaxScaler()
    scaler.fit(features[:train_cut])
    scaled_features = scaler.transform(features)
    scaled_target = scaled_features[:, 2]

    X, y = [], []
    for i in range(sample_count):
        X.append(scaled_features[i:i + window_size])
        baseline = scaled_features[i + window_size - 1, 2]
        y.append(scaled_target[i + window_size:i + window_size + horizon] - baseline)
        
    X = np.array(X)
    y = np.array(y)

    # Keep every 7-day target entirely within its chronological split. The
    # short gaps between splits prevent train targets from leaking into the
    # validation/test target periods.
    train_stop = max(0, train_cut - window_size - horizon + 1)
    val_start = max(0, train_cut - window_size)
    val_stop = max(val_start, val_cut - window_size - horizon + 1)
    test_start = max(val_stop, val_cut - window_size)
    X_train, y_train = X[:train_stop], y[:train_stop]
    X_val, y_val = X[val_start:val_stop], y[val_start:val_stop]
    X_test, y_test = X[test_start:], y[test_start:]

    if not len(X_train) or not len(X_val) or not len(X_test):
        raise ValueError('Training data is too short for chronological train/validation/test splits')

    os.makedirs(artifact_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(artifact_dir, 'scaler.pkl'))
    
    return X_train, y_train, X_val, y_val, X_test, y_test
