import torch
import json
import os
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from preprocessing import load_and_preprocess
from train import SymptomGRU

def evaluate_model(data_path, output_dir='artifacts'):
    # Load Data
    X_train, X_val, X_test, y_train, y_val, y_test, symptom_vocab, diseases = \
        load_and_preprocess(data_path, output_dir=None)

    # Load Model
    checkpoint = torch.load(
        os.path.join(output_dir, 'symptom_gru_v1.pt'),
        map_location='cpu',
        weights_only=False
    )
    config = checkpoint['model_config']
    model = SymptomGRU(**config)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Predict
    X_test_t = torch.FloatTensor(X_test)
    with torch.no_grad():
        outputs = model(X_test_t)
        predictions = outputs.argmax(dim=1).numpy()

    # Metrics
    acc = accuracy_score(y_test, predictions)
    prec_macro = precision_score(y_test, predictions, average='macro', zero_division=0)
    rec_macro = recall_score(y_test, predictions, average='macro', zero_division=0)
    f1_macro = f1_score(y_test, predictions, average='macro', zero_division=0)
    f1_weighted = f1_score(y_test, predictions, average='weighted', zero_division=0)

    report = classification_report(y_test, predictions, target_names=diseases, zero_division=0, output_dict=True)
    report_str = classification_report(y_test, predictions, target_names=diseases, zero_division=0)
    print(report_str)

    metrics = {
        'accuracy': acc,
        'precision_macro': prec_macro,
        'recall_macro': rec_macro,
        'f1_macro': f1_macro,
        'f1_weighted': f1_weighted,
        'report': report
    }

    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)

    return metrics

if __name__ == '__main__':
    evaluate_model('../../data/raw/symptom_checker/symptom_disease.csv', 'artifacts')
