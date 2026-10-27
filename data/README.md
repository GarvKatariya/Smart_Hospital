# Synthetic Data Sets

This directory contains synthetic demo data and explicitly documented, aggregated public datasets used for model training. The real bed dataset is provided under its own source and derived-data license in `real/beds/README.md`.

No patient-level records or direct identifiers from the Kaggle bed dataset are stored here; only daily aggregate counts are retained.

## Structure

* `synthetic/beds/`: Data for hospital bed occupancy forecasting models.
* `synthetic/appointments/`: Historical appointment records for prediction models.
* `synthetic/triage/`: Triage records containing vital signs and symptoms to train the urgency prediction model.
* `real/beds/`: De-identified daily admission, discharge, and occupancy aggregates derived from a public Kaggle dataset.

You can regenerate these datasets using the `scripts/generate_synthetic_data.py` script.
