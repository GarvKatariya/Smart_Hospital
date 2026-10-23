
import joblib
import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from preprocessing import load_and_preprocess

def evaluate():
    _, _, _, _, X_test, y_test = load_and_preprocess('data/synthetic/appointments/appointment_history.csv')
    
    model = joblib.load('models/appointment_recommendation/artifacts/xgb_model.pkl')
    y_pred = model.predict(X_test)
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred)
    }
    
    with open('models/appointment_recommendation/artifacts/metrics.json', 'w') as f:
        json.dump(metrics, f)

if __name__ == '__main__':
    evaluate()
