# Master Roadmap

## Phase 0: Project Setup & Documentation
- **Objective:** Establish the foundation and document architecture, dataset requirements, and the roadmap.
- **Key Deliverables:** README, .env, docker-compose, Makefile, architecture and DB docs.
- **Acceptance Criteria:** All doc files created, clear architecture mapped out.
- **Status:** In Progress

## Phase 1: Database & Core Backend Setup
- **Objective:** Setup FastAPI backend and database models.
- **Key Deliverables:** FastAPI app setup, SQLAlchemy models, Alembic migrations.
- **Acceptance Criteria:** API is reachable, migrations run successfully.
- **Status:** Not Started

## Phase 2: User Authentication & Role Management
- **Objective:** Implement secure login/signup and RBAC.
- **Key Deliverables:** JWT auth, user/role management endpoints.
- **Acceptance Criteria:** Users can register and log in with specific roles (Admin, Doctor, Patient).
- **Status:** Not Started

## Phase 3: Core Hospital Modules (CRUD)
- **Objective:** Manage doctors, patients, departments.
- **Key Deliverables:** CRUD APIs for hospital entities.
- **Acceptance Criteria:** Full CRUD operations work via API.
- **Status:** Not Started

## Phase 4: Appointments & Scheduling
- **Objective:** Booking and managing appointments.
- **Key Deliverables:** Appointment booking API, schedule management.
- **Acceptance Criteria:** Patients can book appointments, doctors can view their schedules.
- **Status:** Not Started

## Phase 5: AI Module 1-3 Integration (Symptom, Chatbot, Summarizer)
- **Objective:** Implement initial AI capabilities.
- **Key Deliverables:** Integration with Gemini/ML models for symptom checking, RAG chatbot, and report summarization.
- **Acceptance Criteria:** AI APIs return correct predictions/summaries.
- **Status:** Not Started

## Phase 6: AI Module 4-5 Integration (Disease Predict, Bed Forecast)
- **Objective:** Predictive analytics models.
- **Key Deliverables:** Scikit-learn/PyTorch models for disease and bed forecasting.
- **Acceptance Criteria:** APIs return accurate forecasts based on datasets.
- **Status:** Not Started

## Phase 7: AI Module 6-8 Integration (Appt Recommender, OCR, Triage)
- **Objective:** Advanced AI operations.
- **Key Deliverables:** Recommendation system, OCR pipeline, triage priority assignment.
- **Acceptance Criteria:** OCR reads prescriptions, triage correctly prioritizes.
- **Status:** Not Started

## Phase 8: Frontend Foundation (Next.js)
- **Objective:** Setup React/Next.js frontend.
- **Key Deliverables:** Next.js setup, Tailwind UI components, routing.
- **Acceptance Criteria:** UI shell is responsive and navigable.
- **Status:** Not Started

## Phase 9: Frontend - User Dashboards
- **Objective:** Build dashboards for Patients, Doctors, Admins.
- **Key Deliverables:** Role-specific views and data binding.
- **Acceptance Criteria:** Users see relevant data on their dashboard.
- **Status:** Not Started

## Phase 10: Frontend - AI Module Integration
- **Objective:** Connect UI to AI APIs.
- **Key Deliverables:** Chat UI, forms for symptom checker, report upload views.
- **Acceptance Criteria:** Users can interact with all 8 AI modules via UI.
- **Status:** Not Started

## Phase 11: Testing & Refinement
- **Objective:** Ensure system stability and performance.
- **Key Deliverables:** Unit tests, integration tests, bug fixes.
- **Acceptance Criteria:** High test coverage, critical bugs resolved.
- **Status:** Not Started

## Phase 12: Deployment & Final Presentation
- **Objective:** Deploy the system and prepare for project defense.
- **Key Deliverables:** Dockerized deployment, presentation slides, final report.
- **Acceptance Criteria:** System is accessible online, presentation materials are ready.
- **Status:** Not Started
