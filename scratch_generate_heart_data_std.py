import random
import csv
import os

random.seed(42)
n = 303

output_dir = '/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system/data/raw/disease_prediction'
os.makedirs(output_dir, exist_ok=True)
filepath = os.path.join(output_dir, 'heart.csv')

with open(filepath, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['age','sex','cp','trestbps','chol','fbs','restecg','thalach','exang','oldpeak','slope','ca','thal','target'])
    
    for _ in range(n):
        age = random.randint(29, 77)
        sex = 1 if random.random() < 0.68 else 0
        cp = random.randint(0, 3)
        trestbps = random.randint(94, 200)
        chol = random.randint(126, 564)
        fbs = 1 if random.random() < 0.15 else 0
        restecg = random.randint(0, 2)
        thalach = random.randint(71, 202)
        exang = 1 if random.random() < 0.33 else 0
        oldpeak = round(random.uniform(0, 6.2), 1)
        slope = random.randint(0, 2)
        ca = random.randint(0, 3)
        thal = random.randint(0, 3)
        
        target_prob = (
            (1 if age > 55 else 0) * 0.2 +
            (sex * 0.1) -
            ((1 if cp > 0 else 0) * 0.2) +
            ((1 if trestbps > 140 else 0) * 0.1) +
            ((1 if chol > 240 else 0) * 0.1) +
            ((1 if thalach < 140 else 0) * 0.1) +
            (exang * 0.2) +
            ((1 if oldpeak > 2.0 else 0) * 0.2) +
            ((1 if ca > 0 else 0) * 0.2) +
            ((1 if thal > 1 else 0) * 0.2)
        )
        
        target = 1 if target_prob > 0.5 else 0
        writer.writerow([age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal, target])

print(f"Generated 303 rows to {filepath}")
