"""
Disease Prediction - Model Evaluation
"""
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, confusion_matrix,
                            classification_report)
import json
import os
import joblib
import pandas as pd
from datetime import datetime
from preprocessing import load_and_preprocess

def evaluate_model(model_path: str, data_path: str, output_dir: str = 'artifacts'):
    print(f"Loading data from {data_path}...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler, features = load_and_preprocess(
        data_path=data_path, output_dir=None
    )
    
    print(f"Loading model from {model_path}...")
    model = joblib.load(model_path)
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba))
    }
    
    conf_matrix = confusion_matrix(y_test, y_pred).tolist()
    
    # Feature importance
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        feature_importance = {feat: float(imp) for feat, imp in zip(features, importances)}
    else:
        feature_importance = {}
        
    # Build evaluation report
    report = {
        "model_name": "disease-xgboost-v1",
        "dataset": "UCI Heart Disease (Cleveland)",
        "task": "binary_classification",
        "metrics": metrics,
        "confusion_matrix": conf_matrix,
        "feature_importance": feature_importance,
        "evaluation_date": datetime.now().isoformat(),
        "test_size": len(y_test),
        "limitations": "Small dataset (303 samples), single-center data"
    }
    
    # Save to JSON
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(report, f, indent=4)
        
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    print(f"Evaluation results saved to {os.path.join(output_dir, 'metrics.json')}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    data_path = os.path.join(project_root, 'data', 'raw', 'disease_prediction', 'heart.csv')
    artifacts_dir = os.path.join(script_dir, 'artifacts')
    model_path = os.path.join(artifacts_dir, 'disease_xgboost_v1.joblib')
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}. Run train.py first.")
    else:
        evaluate_model(model_path, data_path, artifacts_dir)
