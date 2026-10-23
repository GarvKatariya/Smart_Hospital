"""
Symptom Checker - GRU Model Training
A GRU-based classifier that takes multi-hot symptom vectors and predicts diseases.
"""
import torch
import torch.nn as nn
import numpy as np
import json
import os
from datetime import datetime
from preprocessing import load_and_preprocess

class SymptomGRU(nn.Module):
    """GRU-based symptom classifier.
    
    Architecture:
    - Embedding layer to project multi-hot vector
    - GRU recurrent layer
    - Fully connected output layer
    - Softmax for class probabilities
    """
    def __init__(self, input_size, hidden_size=128, num_layers=2, num_classes=41, dropout=0.3):
        super().__init__()
        self.embedding = nn.Linear(input_size, hidden_size)
        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        # x: (batch, input_size) - multi-hot vector
        x = self.embedding(x)  # (batch, hidden_size)
        x = x.unsqueeze(1)  # (batch, 1, hidden_size) - single time step
        gru_out, _ = self.gru(x)  # (batch, 1, hidden_size)
        gru_out = gru_out[:, -1, :]  # Take last output
        gru_out = self.dropout(gru_out)
        out = self.fc(gru_out)
        return out

def train_model(data_path, output_dir='artifacts', epochs=100, batch_size=32, lr=0.001):
    # Load and preprocess
    X_train, X_val, X_test, y_train, y_val, y_test, symptom_vocab, diseases = \
        load_and_preprocess(data_path, output_dir)
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_val_t = torch.FloatTensor(X_val)
    y_val_t = torch.LongTensor(y_val)
    
    # Create data loaders
    train_dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Model
    model = SymptomGRU(
        input_size=len(symptom_vocab),
        hidden_size=128,
        num_layers=2,
        num_classes=len(diseases),
        dropout=0.3
    )
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    # Training with early stopping
    best_val_loss = float('inf')
    patience = 15
    patience_counter = 0
    best_model_state = None
    history = {'train_loss': [], 'val_loss': [], 'val_accuracy': []}
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        avg_train_loss = total_loss / len(train_loader)
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_t)
            val_loss = criterion(val_outputs, y_val_t).item()
            val_preds = val_outputs.argmax(dim=1)
            val_accuracy = (val_preds == y_val_t).float().mean().item()
        
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(val_loss)
        history['val_accuracy'].append(val_accuracy)
        
        if (epoch + 1) % 10 == 0:
            print(f'Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} - Val Loss: {val_loss:.4f} - Val Acc: {val_accuracy:.4f}')
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f'Early stopping at epoch {epoch+1}')
                break
    
    # Load best model
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    # Save model
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, 'symptom_gru_v1.pt')
    torch.save({
        'model_state_dict': model.state_dict(),
        'model_config': {
            'input_size': len(symptom_vocab),
            'hidden_size': 128,
            'num_layers': 2,
            'num_classes': len(diseases),
            'dropout': 0.3
        }
    }, model_path)
    
    # Save training config
    config = {
        'model_name': 'symptom-gru-v1',
        'training_date': datetime.now().isoformat(),
        'epochs_trained': epoch + 1,
        'batch_size': batch_size,
        'learning_rate': lr,
        'best_val_loss': best_val_loss,
        'best_val_accuracy': max(history['val_accuracy']),
        'num_symptoms': len(symptom_vocab),
        'num_diseases': len(diseases),
        'dataset': data_path
    }
    with open(os.path.join(output_dir, 'training_config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    # Save history
    with open(os.path.join(output_dir, 'training_history.json'), 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f'Model saved to {model_path}')
    print(f'Best validation accuracy: {max(history["val_accuracy"]):.4f}')
    return model, history

if __name__ == '__main__':
    train_model(
        data_path='../../data/raw/symptom_checker/symptom_disease.csv',
        output_dir='artifacts',
        epochs=100,
        batch_size=32
    )
