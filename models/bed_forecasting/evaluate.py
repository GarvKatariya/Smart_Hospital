
import torch
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from preprocessing import load_and_preprocess
from .train import BedForecastLSTM

def evaluate():
    _, _, _, _, X_test, y_test = load_and_preprocess('data/synthetic/beds/daily_occupancy.csv')
    model = BedForecastLSTM()
    model.load_state_dict(torch.load('models/bed_forecasting/artifacts/bed_lstm_v1.pt'))
    model.eval()
    
    with torch.no_grad():
        y_pred = model(torch.tensor(X_test, dtype=torch.float32)).numpy()
        
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # avoid division by zero
    y_test_safe = np.where(y_test == 0, 1e-9, y_test)
    mape = mean_absolute_percentage_error(y_test_safe, y_pred)
    
    metrics = {'mae': mae, 'rmse': rmse, 'mape': mape}
    with open('models/bed_forecasting/artifacts/metrics.json', 'w') as f:
        json.dump(metrics, f)

if __name__ == '__main__':
    evaluate()
