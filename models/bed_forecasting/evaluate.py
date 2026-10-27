"""Recompute held-out metrics for the trained bed occupancy model."""

import json
from pathlib import Path

import numpy as np
import torch
import joblib

from preprocessing import DEFAULT_ARTIFACT_DIR, DEFAULT_DATA_PATH, load_and_preprocess
from train import BedForecastLSTM


def evaluate(data_path=DEFAULT_DATA_PATH, artifact_dir=DEFAULT_ARTIFACT_DIR):
    _, _, _, _, X_test, y_test = load_and_preprocess(data_path, artifact_dir=artifact_dir)
    model = BedForecastLSTM()
    model.load_state_dict(torch.load(Path(artifact_dir) / 'bed_lstm_v1.pt', map_location='cpu'))
    model.eval()
    with torch.no_grad():
        prediction = model(torch.tensor(X_test, dtype=torch.float32)).numpy()
    scaler = joblib.load(Path(artifact_dir) / 'scaler.pkl')
    baseline = X_test[:, -1, 2, None]
    prediction = ((prediction + baseline) - scaler.min_[2]) / scaler.scale_[2]
    y_test = ((y_test + baseline) - scaler.min_[2]) / scaler.scale_[2]
    errors = prediction - y_test
    metrics = {
        'dataset': str(Path(data_path).resolve()),
        'test_mae_beds': float(np.mean(np.abs(errors))),
        'test_rmse_beds': float(np.sqrt(np.mean(np.square(errors)))),
        'test_windows': int(len(X_test)),
        'test_period_is_chronological_holdout': True,
    }
    (Path(artifact_dir) / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == '__main__':
    evaluate()
