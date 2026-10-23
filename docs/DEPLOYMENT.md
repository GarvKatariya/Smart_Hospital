# Deployment Guide

## Prerequisites
- Docker & Docker Compose
- 4GB+ RAM (for local ML models)
- External API Keys (Gemini, Database URIs if not local)

## Local Deployment (Docker Compose)
1. Clone the repository.
2. Create `backend/.env` based on `backend/.env.example`.
3. Build and run:
   ```bash
   docker-compose up --build -d
   ```
4. Services:
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`
   - Database: PostgreSQL on port 5432

## Manual Setup
1. **Database**: Start PostgreSQL and configure `DATABASE_URL`.
2. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run start
   ```

## Production Considerations
- **HTTPS**: Configure an Nginx reverse proxy with SSL (Let's Encrypt).
- **Model Hosting**: Consider moving heavy ML models (OCR, GRU) to dedicated GPU microservices or Triton Inference Server.
- **Database Backups**: Schedule automated pg_dump scripts.
