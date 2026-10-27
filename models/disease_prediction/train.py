"""Train the heart disease Random Forest classifier."""
import json
import joblib
import os
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from preprocessing import load_and_preprocess

def train_model(data_path: str, output_dir: str = 'artifacts'):
    os.makedirs(output_dir, exist_ok=True)
    
    print("Starting preprocessing...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler, features = load_and_preprocess(
        data_path=data_path, output_dir=output_dir
    )
    
    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=7,
        min_samples_leaf=2,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1,
    )
    print("Training Random Forest on the training split...")
    model.fit(X_train, y_train)
    joblib.dump(model, os.path.join(output_dir, 'disease_random_forest_v1.joblib'))
    joblib.dump(scaler, os.path.join(output_dir, 'scaler_v3.joblib'))

    test_predictions = model.predict(X_test)
    test_probabilities = model.predict_proba(X_test)[:, 1]
    metrics = {
        "model_name": "disease-random-forest-v1",
        "dataset": "UCI Heart Disease (Cleveland)",
        "task": "binary_classification",
        "metrics": {
            "accuracy": float(accuracy_score(y_test, test_predictions)),
            "precision": float(precision_score(y_test, test_predictions, zero_division=0)),
            "recall": float(recall_score(y_test, test_predictions, zero_division=0)),
            "f1": float(f1_score(y_test, test_predictions, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, test_probabilities)),
        },
        "confusion_matrix": confusion_matrix(y_test, test_predictions).tolist(),
        "evaluation_date": datetime.now().isoformat(),
        "test_size": int(len(y_test)),
        "limitations": "Small dataset (303 samples), single-center data; educational use only.",
    }
    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=4)
    
    # Save config
    config = {
        "model_params": model.get_params(),
        "training_date": datetime.now().isoformat(),
        "model_version": "random-forest-v1",
        "features": features
    }
    with open(os.path.join(output_dir, 'training_config.json'), 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"Random Forest model saved to {os.path.join(output_dir, 'disease_random_forest_v1.joblib')}")
    return model

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    data_path = os.path.join(project_root, 'data', 'raw', 'disease_prediction', 'heart.csv')
    artifacts_dir = os.path.join(script_dir, 'artifacts')
    
    train_model(data_path=data_path, output_dir=artifacts_dir)
