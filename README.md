# Smart Hospital Management System

## Description
An AI-powered hospital platform featuring 8 specialized AI modules designed for a B.Tech Project.

## Technology Stack
| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, Tailwind CSS |
| Backend | FastAPI, Python |
| Database | PostgreSQL (Docker), SQLite (Dev) |
| Machine Learning | Scikit-learn, PyTorch, FAISS |
| LLM | Google Gemini |

## AI Modules
1. **Symptom Checker**: Predicts possible diseases based on user symptoms.
2. **Medical Report Summarizer**: Extracts key information from medical reports using LLM.
3. **Medical Chatbot**: RAG-based chatbot for hospital queries and basic assistance.
4. **Disease Prediction**: Predicts diseases from clinical datasets.
5. **Bed Occupancy Forecasting**: Forecasts hospital bed availability.
6. **Appointment Recommendation**: Recommends appropriate doctors and times.
7. **Prescription OCR**: Extracts text and items from scanned handwritten/printed prescriptions.
8. **Triage System**: Prioritizes patients based on emergency severity.

## Quick Start
```bash
git clone <repo-url>
cd smart-hospital-management-system
cp .env.example .env
docker-compose up -d
make setup
make db-seed
make train-all
make run-all
```

## Project Structure
```
.
├── backend/
├── frontend/
├── models/
├── rag/
├── docs/
├── docker-compose.yml
├── Makefile
├── README.md
```

## Demo Credentials
- Patient: patient@demo.com
- Doctor: doctor@demo.com
- Admin: admin@demo.com
- Password: Demo@123

## License
MIT License

## Disclaimer
This project is for educational purposes only. It is not intended to provide real medical advice, diagnosis, or treatment.
