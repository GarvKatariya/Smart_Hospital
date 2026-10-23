"""
Symptom Checker - Data Preprocessing
Converts symptom-disease CSV into multi-hot encoded vectors for GRU training.
"""
import pandas as pd
import numpy as np
import json
import os
from typing import Tuple, List, Dict

def load_and_preprocess(data_path: str, output_dir: str = None):
    """
    Load symptom-disease dataset and preprocess.
    
    Steps:
    1. Load CSV with Disease + Symptom columns
    2. Build symptom vocabulary (unique symptoms)
    3. Build disease label mapping
    4. Create multi-hot symptom vectors
    5. Split train/val/test (70/15/15)
    6. Save vocabularies and mappings
    
    Returns: X_train, X_val, X_test, y_train, y_val, y_test, symptom_vocab, disease_labels
    """
    # Load data
    df = pd.read_csv(data_path)
    
    # Collect all unique symptoms (strip whitespace, lowercase, replace spaces with underscore)
    all_symptoms = set()
    symptom_columns = [c for c in df.columns if c.startswith('Symptom')]
    for col in symptom_columns:
        symptoms = df[col].dropna().str.strip().str.lower().str.replace(' ', '_')
        all_symptoms.update(symptoms)
    all_symptoms.discard('')
    symptom_vocab = sorted(list(all_symptoms))
    symptom_to_idx = {s: i for i, s in enumerate(symptom_vocab)}
    
    # Disease labels
    diseases = sorted(df['Disease'].unique().tolist())
    disease_to_idx = {d: i for i, d in enumerate(diseases)}
    
    # Multi-hot encoding
    X = np.zeros((len(df), len(symptom_vocab)), dtype=np.float32)
    y = np.zeros(len(df), dtype=np.int64)
    
    for i, row in df.iterrows():
        for col in symptom_columns:
            symptom = str(row[col]).strip().lower().replace(' ', '_') if pd.notna(row[col]) else ''
            if symptom in symptom_to_idx:
                X[i, symptom_to_idx[symptom]] = 1.0
        y[i] = disease_to_idx[row['Disease']]
    
    # Augment dataset - duplicate each sample multiple times with slight noise
    # since we only have ~40 samples (one per disease)
    augmented_X = [X]
    augmented_y = [y]
    np.random.seed(42)
    for _ in range(19):  # Create 20x data = ~800 samples
        noise = np.random.binomial(1, 0.05, X.shape).astype(np.float32)  # 5% chance to flip a symptom
        X_noisy = np.clip(X + noise - 2 * X * noise, 0, 1)  # XOR-like noise
        augmented_X.append(X_noisy)
        augmented_y.append(y.copy())
    
    X = np.vstack(augmented_X)
    y = np.concatenate(augmented_y)
    
    # Shuffle
    perm = np.random.permutation(len(X))
    X = X[perm]
    y = y[perm]
    
    # Split (no stratify needed since we augmented)
    from sklearn.model_selection import train_test_split
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.176, random_state=42)
    
    # Save artifacts
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'symptom_vocab.json'), 'w') as f:
            json.dump(symptom_vocab, f, indent=2)
        with open(os.path.join(output_dir, 'disease_labels.json'), 'w') as f:
            json.dump(diseases, f, indent=2)
        with open(os.path.join(output_dir, 'symptom_to_idx.json'), 'w') as f:
            json.dump(symptom_to_idx, f, indent=2)
        with open(os.path.join(output_dir, 'disease_to_idx.json'), 'w') as f:
            json.dump(disease_to_idx, f, indent=2)
    
    return X_train, X_val, X_test, y_train, y_val, y_test, symptom_vocab, diseases

def normalize_symptoms(text: str, symptom_vocab: List[str]) -> List[str]:
    """Extract symptoms from free text by matching against vocabulary."""
    text_lower = text.lower().replace(',', ' ').replace('.', ' ')
    words = text_lower.split()
    found = []
    for symptom in symptom_vocab:
        # Check if symptom (with underscores replaced by spaces) appears in text
        symptom_text = symptom.replace('_', ' ')
        if symptom_text in text_lower:
            found.append(symptom)
    # Also check individual word matches
    for word in words:
        word_clean = word.strip()
        if word_clean in symptom_vocab and word_clean not in found:
            found.append(word_clean)
    return found if found else []
