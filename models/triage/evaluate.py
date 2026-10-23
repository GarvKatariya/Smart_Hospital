"""Evaluation script for Triage GRU Model."""
import torch
from sklearn.metrics import classification_report, accuracy_score
import json
import os
from preprocessing import load_and_preprocess
from train import TriageGRU

def evaluate_model():
    data_path = os.path.join('..', 'data', 'synthetic', 'triage', 'triage_dataset.csv')
    artifacts_dir = 'artifacts'
    
    _, _, (X_test, y_test), input_size = load_and_preprocess(data_path, artifacts_dir)
    
    model = TriageGRU(input_size=input_size)
    model.load_state_dict(torch.load(os.path.join(artifacts_dir, 'triage_gru_v1.pt')))
    model.eval()
    
    inputs = torch.FloatTensor(X_test)
    with torch.no_grad():
        outputs = model(inputs)
        _, preds = outputs.max(1)
        
    y_pred = preds.numpy()
    
    target_names = ['Emergency', 'High', 'Medium', 'Low']
    report = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)
    acc = accuracy_score(y_test, y_pred)
    
    metrics = {
        'accuracy': acc,
        'classification_report': report
    }
    
    with open(os.path.join(artifacts_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Evaluation complete. Accuracy: {acc:.4f}. Metrics saved to {artifacts_dir}/metrics.json")

if __name__ == '__main__':
    evaluate_model()
