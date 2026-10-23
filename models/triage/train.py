"""Training script for Triage GRU Model."""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import os
import sys

from preprocessing import load_and_preprocess

class TriageGRU(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=4, dropout=0.3):
        super().__init__()
        self.embedding = nn.Linear(input_size, hidden_size)
        self.gru = nn.GRU(hidden_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = self.embedding(x)
        x = x.unsqueeze(1) # sequence length 1
        out, _ = self.gru(x)
        out = self.dropout(out[:, -1, :])
        return self.fc(out)

def train_model():
    data_path = os.path.join('..', '..', 'data', 'synthetic', 'triage', 'triage_dataset.csv')
    artifacts_dir = 'artifacts'
    
    if not os.path.exists(data_path):
        print(f"Data not found at {data_path}. Run generate_synthetic_data.py first.")
        return
        
    (X_train, y_train), (X_val, y_val), _, input_size = load_and_preprocess(data_path, artifacts_dir)
    
    train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train))
    val_dataset = TensorDataset(torch.FloatTensor(X_val), torch.LongTensor(y_val))
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)
    
    model = TriageGRU(input_size=input_size)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    best_val_loss = float('inf')
    
    for epoch in range(50): # Simple run for demo
        model.train()
        train_loss = 0
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        val_loss = 0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                
        val_loss /= len(val_loader)
        accuracy = 100. * correct / total
        
        print(f"Epoch {epoch+1} | Train Loss: {train_loss/len(train_loader):.4f} | Val Loss: {val_loss:.4f} | Val Acc: {accuracy:.2f}%")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), os.path.join(artifacts_dir, 'triage_gru_v1.pt'))
            
    print("Training complete. Best model saved.")

if __name__ == '__main__':
    train_model()
