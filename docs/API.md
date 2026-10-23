# API Reference

The backend exposes a RESTful API built with FastAPI. All endpoints are prefixed with `/api`.

## Authentication

### `POST /api/auth/login`
Authenticates a user and returns a JWT.
- **Request Body**: `{ "email": "user@example.com", "password": "password123" }`
- **Response**: `{ "access_token": "eyJhb...", "token_type": "bearer", "role": "patient" }`

### `POST /api/auth/register`
Registers a new user.
- **Request Body**: `{ "email": "new@example.com", "password": "pass", "role": "patient", "name": "John Doe" }`
- **Response**: `{ "id": 1, "email": "new@example.com", "role": "patient" }`

## AI Services

### `POST /api/symptoms/check`
Predicts disease based on symptoms.
- **Request Body**: 
  ```json
  {
    "symptoms_text": "I have a severe headache and continuous sneezing",
    "selected_symptoms": ["chills", "high_fever"]
  }
  ```
- **Response**:
  ```json
  {
    "predicted_condition": "Common Cold",
    "confidence": 0.95,
    "department": "General Medicine",
    "explanation": "Based on your symptoms..."
  }
  ```

### `POST /api/disease/predict`
Predicts heart disease risk.
- **Request Body**: (Heart Disease features e.g., age, sex, cp, trestbps, etc.)
- **Response**: `{ "prediction": 1, "probability": 0.82, "risk_level": "High" }`

### `POST /api/documents/upload`
Uploads a medical report/prescription for OCR and analysis.
- **Form Data**: `file` (UploadFile), `document_type` (str)
- **Response**: Extracted text, identified entities, and LLM summary.

## Appointments

### `GET /api/appointments`
Lists user's appointments.

### `POST /api/appointments`
Schedules an appointment.
