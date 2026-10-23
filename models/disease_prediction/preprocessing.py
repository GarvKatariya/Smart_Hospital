"""
Disease Prediction - Data Preprocessing
Dataset: UCI Heart Disease (Cleveland)
Task: Binary classification (heart disease presence)
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import json
import os
import joblib
from typing import Tuple, List

def load_and_preprocess(data_path: str, output_dir: str = None) -> Tuple:
    """
    Load UCI Heart Disease dataset and preprocess for training.
    
    Steps:
    1. Load CSV
    2. Handle missing values (? -> NaN -> median impute)
    3. Validate feature ranges
    4. Split into train/val/test (70/15/15)
    5. Scale features with StandardScaler
    6. Save scaler and split info
    
    Returns: X_train, X_val, X_test, y_train, y_val, y_test, scaler, feature_names
    """
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Handle missing values (assuming '?' might be present from original UCI dataset)
    df = df.replace('?', np.nan)
    
    # Define features and target
    target_col = 'target'
    features = [col for col in df.columns if col != target_col]
    
    # Impute missing with median
    for col in features:
        if df[col].isnull().any():
            df[col] = df[col].astype(float).fillna(df[col].median())
    
    # Convert all features to float for consistency
    X = df[features].astype(float)
    y = df[target_col].astype(int)
    
    # Train (70%), Val (15%), Test (15%) split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    
    # Calculate relative validation size from the remaining 85%
    val_size_relative = 0.15 / 0.85
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_size_relative, random_state=42, stratify=y_train_val
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # Re-apply column names to scaled data
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=features)
    X_val_scaled = pd.DataFrame(X_val_scaled, columns=features)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=features)
    
    # Save artifacts if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        scaler_path = os.path.join(output_dir, 'scaler.joblib')
        joblib.dump(scaler, scaler_path)
        
        feature_info = {
            "features": features,
            "target": target_col,
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_test": len(X_test)
        }
        with open(os.path.join(output_dir, 'feature_info.json'), 'w') as f:
            json.dump(feature_info, f, indent=4)
            
        print(f"Artifacts saved to {output_dir}")
        
    return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, scaler, features
