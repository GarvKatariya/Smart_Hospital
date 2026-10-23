# Datasets Documentation

## 1. UCI Heart Disease (Cleveland)
- **Source:** UCI Machine Learning Repository
- **URL:** https://archive.ics.uci.edu/ml/datasets/heart+disease
- **License:** CC BY 4.0
- **Records:** 303
- **Features:** 14 (age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal)
- **Target:** Presence of heart disease (binary)
- **Preprocessing:** Handle missing values, scaling of numerical features, encode categoricals.
- **Split:** 80/20 train/test
- **Limitations:** Small dataset size.
- **Synthetic Disclaimer:** Real clinical dataset.

## 2. Symptom-Disease Dataset
- **Source:** Kaggle Public Dataset
- **URL:** https://www.kaggle.com/datasets/kaushil268/disease-prediction-using-machine-learning
- **License:** Public Domain
- **Records:** ~4,920
- **Features:** Various symptoms (one-hot encoded)
- **Target:** Disease prognosis
- **Preprocessing:** One-hot encoding, text normalization.
- **Split:** 80/20 train/test
- **Limitations:** Synthetic nature of some symptom combinations.
- **Synthetic Disclaimer:** Partially synthetic/aggregated.

## 3. Synthetic Hospital Operations
- **Source:** Self-generated script
- **URL:** N/A (Internal)
- **License:** MIT
- **Records:** ~730 days of daily records
- **Features:** Date, Total Beds, Occupied Beds, Admissions, Discharges
- **Target:** Bed occupancy forecasting
- **Preprocessing:** Time-series formatting.
- **Split:** Chronological split (e.g., last 30 days for test)
- **Limitations:** Does not capture real-world unpredictable events (e.g., pandemics).
- **Synthetic Disclaimer:** Completely generated for simulation purposes.

## 4. Synthetic Appointments
- **Source:** Self-generated script
- **URL:** N/A (Internal)
- **License:** MIT
- **Records:** ~5,000
- **Features:** Patient ID, Doctor ID, Timestamp, Department, Status
- **Target:** N/A (Used for recommendation engine)
- **Preprocessing:** Normalization of timestamps.
- **Split:** N/A
- **Limitations:** Limited variance in patient behavior.
- **Synthetic Disclaimer:** Completely generated for simulation.

## 5. Synthetic Triage
- **Source:** Self-generated script
- **URL:** N/A (Internal)
- **License:** MIT
- **Records:** ~2,000
- **Features:** Vitals (HR, BP, SpO2, Temp), Age, Symptom severity
- **Target:** Priority level (1-5)
- **Preprocessing:** Feature scaling.
- **Split:** 80/20 train/test
- **Limitations:** May not fully encompass complex multi-trauma scenarios.
- **Synthetic Disclaimer:** Completely generated for simulation based on general triage rules.

## 6. Hospital Knowledge Base
- **Source:** Self-authored / Scraped fictional data
- **URL:** N/A (Internal)
- **License:** MIT
- **Records:** ~20 documents (Markdown/Text)
- **Features:** Text content (FAQs, policies, general medical info)
- **Target:** N/A (For RAG)
- **Preprocessing:** Chunking, embedding generation.
- **Split:** N/A
- **Limitations:** Limited scope.
- **Synthetic Disclaimer:** Fictional hospital data; medical info for educational use only.
