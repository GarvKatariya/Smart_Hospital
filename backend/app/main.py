from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.db.base import create_tables
from app.core.exceptions import HospitalBaseException, hospital_exception_handler

# Import all routers
from app.api import auth, departments, doctors, appointments, beds, admin, symptoms, disease, reports, chatbot, prescriptions, triage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Hospital Management System",
    description="Backend API for Smart Hospital Management System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(HospitalBaseException, hospital_exception_handler)

# Include routers
app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(beds.router)
app.include_router(admin.router)
app.include_router(symptoms.router)
app.include_router(disease.router)
app.include_router(reports.router)
app.include_router(chatbot.router)
app.include_router(prescriptions.router)
app.include_router(triage.router)

@app.on_event("startup")
def on_startup():
    logger.info("Starting up Smart Hospital Management System")
    create_tables()
    logger.info("Database tables created")
    logger.info("AI models will load on first request (lazy loading)")
    logger.info("Startup complete")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

