# Architecture

## High-Level System Architecture
```mermaid
graph TD
    Client[Frontend: Next.js + React] -->|REST / HTTP| API[Backend: FastAPI]
    API --> Services[Business Logic & AI Services]
    Services --> DB[(PostgreSQL / SQLite)]
    Services --> LLM[Google Gemini API]
    Services --> ML[Local ML Models / FAISS]
```

## Data Flow Diagram
```mermaid
graph LR
    User -->|Input Data| UI[Frontend]
    UI -->|API Call| BE[FastAPI Backend]
    BE -->|Query| DB[(Database)]
    BE -->|Inference| AI[AI Modules]
    AI --> BE
    DB --> BE
    BE --> UI
    UI --> User
```

## AI Modules Interaction
```mermaid
graph TD
    BE[FastAPI Backend] --> M1[Symptom Checker]
    BE --> M2[Report Summarizer]
    BE --> M3[Medical Chatbot]
    BE --> M4[Disease Prediction]
    BE --> M5[Bed Forecasting]
    BE --> M6[Appointment Recommendation]
    BE --> M7[Prescription OCR]
    BE --> M8[Triage System]
```

## Authentication Flow
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant DB

    User->>Frontend: Enter credentials
    Frontend->>Backend: POST /api/login
    Backend->>DB: Verify user & hash
    DB-->>Backend: Return User Object
    Backend-->>Frontend: Return JWT Token
    Frontend-->>User: Redirect to Dashboard
```

## AI Module Pipeline Flows

### 1. Symptom Checker & 4. Disease Prediction
```mermaid
graph LR
    Input[Symptoms] --> Preprocess[One-hot Encoding]
    Preprocess --> Model[ML Classifier]
    Model --> Output[Disease Prediction & Confidence]
```

### 2. Medical Report Summarizer & 7. Prescription OCR
```mermaid
graph LR
    File[PDF/Image] --> OCR[OCR Extraction]
    OCR --> LLM[LLM Processing]
    LLM --> Structured[Structured Summary/Items]
```

### 3. Medical Chatbot (RAG)
```mermaid
graph LR
    Query[User Question] --> Embed[Embedding Model]
    Embed --> FAISS[Vector Search]
    FAISS --> Context[Retrieved Docs]
    Context --> LLM[Gemini LLM]
    Query --> LLM
    LLM --> Answer[Final Response]
```

### 5. Bed Occupancy Forecasting
```mermaid
graph LR
    Hist[Historical Data] --> TS[Time Series Model]
    TS --> Forecast[Future Bed Availability]
```

### 6. Appointment Recommendation
```mermaid
graph LR
    Pref[Patient Preferences] --> Match[Matching Algorithm]
    Avail[Doctor Schedules] --> Match
    Match --> Slots[Recommended Slots]
```

### 8. Triage System
```mermaid
graph LR
    Vitals[Vitals & Symptoms] --> Scoring[Severity Scorer Model]
    Scoring --> Priority[Priority Level 1-5]
```
