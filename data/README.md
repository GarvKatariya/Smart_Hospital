# Synthetic Data Sets

This directory contains purely synthetic datasets generated for the purpose of training machine learning models and demonstrating the system's capabilities in demo mode. 

**NO REAL PATIENT DATA IS PRESENT IN THIS REPOSITORY.**

## Structure

* `synthetic/beds/`: Data for hospital bed occupancy forecasting models.
* `synthetic/appointments/`: Historical appointment records for prediction models.
* `synthetic/triage/`: Triage records containing vital signs and symptoms to train the urgency prediction model.

You can regenerate these datasets using the `scripts/generate_synthetic_data.py` script.
