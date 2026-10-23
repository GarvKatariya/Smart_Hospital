# Testing Strategy

## Overview
The project employs `pytest` for unit and integration testing.

## Test Coverage
- **Authentication**: JWT generation, password hashing, role verification.
- **AI Services**: Model loading, preprocessing logic, inference accuracy constraints, fallback logic.
- **API Endpoints**: Request validation, proper status codes, error handling.
- **Database**: CRUD operations using an in-memory SQLite database for test isolation.

## Running Tests
Run the entire test suite from the `backend/` directory:
```bash
cd backend
pytest tests/
```

To generate a coverage report:
```bash
pytest --cov=app tests/
```

## Strategy
1. **Unit Tests**: Test individual components (e.g., hash function, symptom normalizer) in isolation.
2. **Integration Tests**: Test API endpoints using FastAPI's `TestClient`, mocking out the actual ML models and external APIs to ensure speed and stability.
3. **Model Tests**: Periodic evaluation scripts evaluate the ML models against test datasets. These are distinct from CI/CD tests due to compute requirements.
