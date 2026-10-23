"""
Appointment Recommendation - XGBoost Training
Predicts appointment completion likelihood to score and rank slots.
"""
import xgboost as xgb
import joblib
import json
import os
from datetime import datetime
from preprocessing import load_and_preprocess

def train_model(data_path='../../data/synthetic/appointments/appointment_history.csv',
                output_dir='artifacts'):
    """Train XGBoost model for appointment slot scoring."""
    print("Loading and preprocessing data...")
    X_train, y_train, X_val, y_val, X_test, y_test = load_and_preprocess(data_path, output_dir)
    
    print(f"Training samples: {len(X_train)}, Validation: {len(X_val)}, Test: {len(X_test)}")
    
    model = xgb.XGBClassifier(
        max_depth=5,
        n_estimators=200,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        early_stopping_rounds=10,
        eval_metric='logloss',
        random_state=42,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, 'appointment_xgb_v1.joblib')
    joblib.dump(model, model_path)
    
    # Save training config
    config = {
        'model_name': 'appointment-xgboost-v1',
        'training_date': datetime.now().isoformat(),
        'n_estimators': 200,
        'max_depth': 5,
        'learning_rate': 0.1,
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'test_samples': len(X_test),
    }
    with open(os.path.join(output_dir, 'training_config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Model saved to {model_path}")
    
    # Quick accuracy check
    from sklearn.metrics import accuracy_score
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {acc:.4f}")

if __name__ == '__main__':
    train_model()
