# Security Documentation

## Authentication Flow
1. User submits credentials to `/api/auth/login`.
2. Backend verifies password hash and generates a stateless JSON Web Token (JWT).
3. The JWT is returned and must be included in the `Authorization: Bearer <token>` header of subsequent requests.

## Password Storage
- Passwords are never stored in plain text.
- `bcrypt` is used for cryptographic hashing with a high work factor.

## JWT Details
- **Algorithm**: HS256
- **Expiration**: Access tokens expire in 30 minutes.
- **Payload**: Contains `sub` (email) and `role` (patient/doctor/admin) for fast authorization without DB hits on every request.

## API Key Management
- Third-party API keys (e.g., Google Gemini, SendGrid) are managed strictly via environment variables (`.env`).
- They are never hardcoded in the repository.

## File Validation
- Uploaded files are verified via MIME type and extension before processing.
- Files are stored in secure directories and sanitized to prevent path traversal attacks.

## Role-Based Access Control (RBAC)
- FastAPI dependencies (`get_current_user`, `get_current_admin`) enforce endpoint restrictions.
- Patients can only view their own data.
- Doctors can view assigned patients.
- Admins have global access.
