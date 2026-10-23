# Model Registry

| Module | Model | Dataset | Task | Metric | Result | Limitations |
|--------|-------|---------|------|--------|--------|-------------|
| Disease Prediction | XGBoost | UCI Heart Disease (Cleveland) | Binary Classification | Accuracy | 93% | Small dataset (303 samples), single-center |
| Symptom Checker | GRU (PyTorch) | Symptom-Disease (augmented) | Multi-class (40 diseases) | Val Accuracy | 98.3% | Augmented from 40 original samples, limited symptom vocabulary |
| Bed Forecasting | LSTM (PyTorch) | Synthetic Hospital Ops | Time-series Regression | Trained | ✅ | Synthetic data only, no real hospital validation |
| Appointment Recommendation | XGBoost | Synthetic Appointments | Binary Classification | Accuracy | 84.8% | Synthetic data, limited feature set |
| Prescription NER | Rule-based + Patterns | N/A | Entity Extraction | N/A | Demo | Rule-based, not fine-tuned BERT |
| Triage | GRU (PyTorch) | Synthetic Triage | Multi-class (4 levels) | Pending | Pending | Synthetic labels, not clinically validated |
| Hospital Chatbot | RAG + LLM | Hospital Knowledge Base | Q&A | N/A | Grounded | Depends on knowledge base completeness |
| Report Summarizer | OCR + RAG + LLM | N/A | Summarization | N/A | LLM-dependent | OCR quality varies |

## Model Details

### Disease Prediction
- **Architecture**: XGBoost Classifier (Tree-based ensemble)
- **Hyperparameters**: `max_depth=5`, `learning_rate=0.1`, `n_estimators=100`
- **Training Procedure**: K-fold cross-validation, optimized for F1-score and accuracy.
- **How to Retrain**: Run `python3 models/disease_prediction/train.py`

### Symptom Checker
- **Architecture**: PyTorch GRU (Embedding -> GRU(2 layers, 128 hidden) -> Dropout(0.3) -> Linear)
- **Hyperparameters**: Batch size 32, learning rate 0.001, early stopping patience 15.
- **Training Procedure**: Uses multi-hot encoded symptom vectors. Stratified split (70/15/15).
- **How to Retrain**: Run `python3 models/symptom_checker/train.py`

### Bed Forecasting
- **Architecture**: PyTorch LSTM (Sequence-to-sequence)
- **Hyperparameters**: 30-day lookback window, 1 LSTM layer.
- **Training Procedure**: Mean Squared Error (MSE) loss with Adam optimizer.
- **How to Retrain**: Run `python3 models/bed_forecasting/train.py`

### Appointment Recommendation
- **Architecture**: XGBoost Classifier
- **Training Procedure**: Engineered features based on patient history and doctor availability.
- **How to Retrain**: Run `python3 models/appointment_recommendation/train.py`

### Triage
- **Architecture**: PyTorch GRU
- **Training Procedure**: Sequential vital sign and textual symptom inputs. CrossEntropyLoss.
- **How to Retrain**: Run `python3 models/triage/train.py`
