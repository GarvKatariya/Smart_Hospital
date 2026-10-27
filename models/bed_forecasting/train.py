"""Train and evaluate the bed occupancy LSTM on a chronological holdout."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from preprocessing import DEFAULT_ARTIFACT_DIR, DEFAULT_DATA_PATH, load_and_preprocess


class BedForecastLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=16, num_layers=1, output_size=7, dropout=0.0):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])


def train_model(data_path=DEFAULT_DATA_PATH, artifact_dir=DEFAULT_ARTIFACT_DIR):
    torch.manual_seed(42)
    np.random.seed(42)
    X_train, y_train, X_val, y_val, X_test, y_test = load_and_preprocess(
        data_path, artifact_dir=artifact_dir
    )
    from joblib import load
    scaler = load(Path(artifact_dir) / 'scaler.pkl')

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32)),
        batch_size=32,
        shuffle=True,
    )
    val_x = torch.tensor(X_val, dtype=torch.float32)
    val_y = torch.tensor(y_val, dtype=torch.float32)
    model = BedForecastLSTM()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    best_loss = float('inf')
    best_state = None
    patience, patience_left = 15, 15

    for _ in range(100):
        model.train()
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(val_x), val_y).item()
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            patience_left = patience
        else:
            patience_left -= 1
            if patience_left == 0:
                break

    if best_state is None:
        raise RuntimeError('LSTM training did not produce a valid checkpoint')
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        prediction_scaled = model(torch.tensor(X_test, dtype=torch.float32)).numpy()

    last_occupancy_scaled = X_test[:, -1, 2, None]
    prediction = ((prediction_scaled + last_occupancy_scaled) - scaler.min_[2]) / scaler.scale_[2]
    y_test = ((y_test + last_occupancy_scaled) - scaler.min_[2]) / scaler.scale_[2]
    X_test_raw = scaler.inverse_transform(X_test.reshape(-1, 3)).reshape(X_test.shape)
    persistence_prediction = X_test_raw[:, -1, 2, None]

    errors = prediction - y_test
    metrics = {
        'dataset': str(Path(data_path).resolve()),
        'model': '1-layer LSTM (16 hidden units), 30-day input, 7-day output',
        'train_windows': int(len(X_train)),
        'validation_windows': int(len(X_val)),
        'test_windows': int(len(X_test)),
        'test_mae_beds': float(np.mean(np.abs(errors))),
        'test_rmse_beds': float(np.sqrt(np.mean(np.square(errors)))),
        'persistence_baseline_mae_beds': float(np.mean(np.abs(persistence_prediction - y_test))),
        'test_period_is_chronological_holdout': True,
    }

    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, artifact_dir / 'bed_lstm_v1.pt')
    (artifact_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument('--artifacts', type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    train_model(args.data, args.artifacts)
