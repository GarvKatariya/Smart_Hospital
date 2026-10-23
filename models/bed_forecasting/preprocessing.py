
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

def load_and_preprocess(data_path, window_size=30):
    df = pd.read_csv(data_path)
    # Assuming daily data, sum across departments if necessary, or just use as is
    # We will aggregate to total occupied_beds, admissions, discharges
    daily = df.groupby('date').agg({
        'admissions': 'sum',
        'discharges': 'sum',
        'occupied_beds': 'sum'
    }).reset_index()
    daily = daily.sort_values('date')
    
    features = daily[['admissions', 'discharges', 'occupied_beds']].values
    target = daily['occupied_beds'].values
    
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(features)
    
    X, y = [], []
    for i in range(len(scaled_features) - window_size - 7):
        X.append(scaled_features[i:i+window_size])
        y.append(target[i+window_size:i+window_size+7]) # 7 days ahead
        
    X = np.array(X)
    y = np.array(y)
    
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]
    
    os.makedirs('models/bed_forecasting/artifacts', exist_ok=True)
    joblib.dump(scaler, 'models/bed_forecasting/artifacts/scaler.pkl')
    
    return X_train, y_train, X_val, y_val, X_test, y_test
