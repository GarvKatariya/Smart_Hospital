"""
Disease Prediction - XGBoost Training
"""
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
import json
import joblib
import os
import numpy as np
from datetime import datetime
from preprocessing import load_and_preprocess

def train_model(data_path: str, output_dir: str = 'artifacts'):
    os.makedirs(output_dir, exist_ok=True)
    
    print("Starting preprocessing...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler, features = load_and_preprocess(
        data_path=data_path, output_dir=output_dir
    )
    
    # Define model
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        random_state=42,
        eval_metric='logloss'
    )
    
    # Hyperparameter grid
    param_grid = {
        'max_depth': [3, 5, 7],
        'n_estimators': [100, 200],
        'learning_rate': [0.01, 0.1],
        'subsample': [0.8, 1.0]
    }
    
    print("Starting Grid Search...")
    grid_search = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=5,
        scoring='roc_auc',
        n_jobs=-1,
        verbose=1
    )
    
    # Train
    grid_search.fit(X_train, y_train)
    
    best_model = grid_search.best_estimator_
    print(f"Best parameters found: {grid_search.best_params_}")
    
    # Save model
    model_path = os.path.join(output_dir, 'disease_xgboost_v1.joblib')
    joblib.dump(best_model, model_path)
    
    # Save config
    config = {
        "best_params": grid_search.best_params_,
        "training_date": datetime.now().isoformat(),
        "model_version": "v1",
        "features": features
    }
    with open(os.path.join(output_dir, 'training_config.json'), 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"Model saved to {model_path}")
    return best_model

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    data_path = os.path.join(project_root, 'data', 'raw', 'disease_prediction', 'heart.csv')
    artifacts_dir = os.path.join(script_dir, 'artifacts')
    
    train_model(data_path=data_path, output_dir=artifacts_dir)
