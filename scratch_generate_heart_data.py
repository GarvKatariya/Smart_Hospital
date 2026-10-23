import numpy as np
import pandas as pd
import os

np.random.seed(42)
n = 303

age = np.random.randint(29, 78, n)
sex = np.random.choice([0, 1], n, p=[0.32, 0.68])
cp = np.random.randint(0, 4, n)
trestbps = np.random.randint(94, 201, n)
chol = np.random.randint(126, 565, n)
fbs = np.random.choice([0, 1], n, p=[0.85, 0.15])
restecg = np.random.randint(0, 3, n)
thalach = np.random.randint(71, 203, n)
exang = np.random.choice([0, 1], n, p=[0.67, 0.33])
oldpeak = np.round(np.random.uniform(0, 6.2, n), 1)
slope = np.random.randint(0, 3, n)
ca = np.random.randint(0, 4, n)
thal = np.random.randint(0, 4, n)

# Generate a synthetic target that roughly makes sense with the features
target_prob = (
    (age > 55).astype(int) * 0.2 +
    (sex == 1).astype(int) * 0.1 +
    (cp > 0).astype(int) * -0.2 +
    (trestbps > 140).astype(int) * 0.1 +
    (chol > 240).astype(int) * 0.1 +
    (thalach < 140).astype(int) * 0.1 +
    (exang == 1).astype(int) * 0.2 +
    (oldpeak > 2.0).astype(int) * 0.2 +
    (ca > 0).astype(int) * 0.2 +
    (thal > 1).astype(int) * 0.2
)

# Normalize probability
target_prob = target_prob - target_prob.min()
target_prob = target_prob / target_prob.max()
# Binarize
target = (target_prob > 0.5).astype(int)

df = pd.DataFrame({
    'age': age,
    'sex': sex,
    'cp': cp,
    'trestbps': trestbps,
    'chol': chol,
    'fbs': fbs,
    'restecg': restecg,
    'thalach': thalach,
    'exang': exang,
    'oldpeak': oldpeak,
    'slope': slope,
    'ca': ca,
    'thal': thal,
    'target': target
})

output_dir = '/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system/data/raw/disease_prediction'
os.makedirs(output_dir, exist_ok=True)
df.to_csv(os.path.join(output_dir, 'heart.csv'), index=False)
print(f"Generated 303 rows to {output_dir}/heart.csv")
