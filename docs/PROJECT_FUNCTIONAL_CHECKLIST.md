# Project Functionality Checklist

This checklist tracks the user-visible and backend functionality in Smart Hospital Management System. Items are marked from repository inspection and available automated checks; an item is not considered passed until its end-to-end behavior has been exercised.

## Status key

- [ ] Not verified
- [x] Verified working
- [!] Fails or is incomplete; fix required
- [~] Deferred by user or blocked by environment
- [>] In progress

## 1. Run, configuration, and data

- [ ] Backend starts and health endpoint reports service/database status.
- [ ] Frontend starts, loads, and reaches the backend using configured API URL.
- [ ] Environment configuration has safe defaults and clear required secrets.
- [ ] Database schema initializes and persists records across restarts.
- [ ] PostgreSQL/Docker setup works; development SQLite setup works.
- [ ] Seed/demo data is documented and can be recreated.
- [ ] Upload storage has size/type limits, safe filenames, and cleanup behavior.

## 2. Authentication, identity, and access control

- [>] Public registration now creates patient accounts only; inactive accounts are rejected during login and token validation. API tests pass; browser session behavior still needs verification.
- [x] Public users cannot self-assign staff roles; doctor creation remains in the admin workflow.
- [>] Doctor creation is administrator-only and department-linked; API permissions and edge cases still need dedicated coverage.
- [>] Auth API tests cover registration-role restriction and inactive login; expired token, malformed input, and cross-role matrix need broader verification.
- [>] Core role checks are present on patient, doctor, and admin APIs; continue auditing every route and frontend route.
- [ ] Users can only access their own medical records, appointments, and chat sessions.
- [>] Profile details and password change now have API and UI; end-to-end authenticated workflow still needs browser verification.
- [ ] Login and registration work with useful loading, validation, and error states.

## 3. Hospital directory and administration

- [>] Department list/create/update/archive/restore UI and API are implemented; exercise through authenticated browser.
- [>] Doctor directory and admin creation exist; schedule ownership/validation has been tightened. Full lifecycle and availability UI remain to verify.
- [>] Admin dashboard statistics now use database data; browser refresh/empty-state behavior remains to verify.
- [>] Patient directory and audit-log screens consume protected admin APIs; audit events are now recorded for department, doctor, appointment, triage, and queue mutations. Verify visibility and actor details in a running app.
- [>] AI model status screen now reports artifact and database status; validate model paths against deployed runtime.
- [ ] Empty, loading, error, and success states are present on admin screens.

## 4. Appointments and scheduling

- [>] Appointment endpoints now scope doctors/admins/patients by role and reject invalid dates, schedule slots, and conflicts; API/browser scenarios remain to verify.
- [>] Booking rejects past dates, unavailable doctors, invalid schedule times, and occupied slots; concurrency/race behavior still needs verification.
- [>] Doctor appointment listing now scopes to their own schedule; browser verification remains.
- [>] Schedule creation validates day/time ranges and doctor ownership/admin access; exercise endpoints.
- [>] Recommendation generation uses configured doctor schedules; verify returned slots are bookable under concurrent requests.
- [ ] Recommendation booking handles races when another user takes a slot.
- [ ] Appointment status changes are available to authorized staff where required.

## 5. AI and clinical support modules

- [>] Symptom checker API/model tests pass; input validation, history ownership, user-facing limitations, and browser flow remain to verify.
- [>] Heart-disease endpoint now validates clinical feature ranges and patient role; model-availability reporting needs a full runtime check.
- [>] Chat now resumes the latest owned session and loads persisted messages; test history isolation and behavior when RAG/LLM services are unavailable.
- [>] Bed status uses authenticated live inventory; sparse occupancy history now falls back to the observed trend instead of applying the synthetic-data model. Forecast chart starts at today's live count and distinguishes it from forecast values; verify with richer production history.
- [>] Triage safety overrides, atomic triage/queue persistence, protected staff queue, and staff call/complete/cancel actions are implemented and covered by focused service tests.
- [~] Medical report scanning/OCR and report summarization are deferred while the user asks to leave OCR aside.
- [~] Prescription OCR, medication extraction, and pharmacist explanation are deferred while the user asks to leave OCR aside.

## 6. Frontend experience

- [>] Patient, doctor, and admin dashboard data is role-specific and uses live APIs; browser verification remains.
- [>] Sidebar navigation exposes admin patient/audit tools, Bed Availability for patient and doctor roles, and hides staff queue from patients; doctor Reports access is permitted by the shared route guard. Browser verification remains pending.
- [>] Doctor appointment list has visible loading and error states. Demo doctor API inspection returned 3 appointments (2 scheduled, dated before 2026-10-24) and 0 appointments today; reconcile the user's live dashboard count and browser data before marking the doctor workflow verified.
- [>] Core visible profile, department, admin model, appointment, and queue actions are connected to APIs; continue checking remaining screens.
- [>] Core forms now validate and surface API errors; full UX/browser coverage remains.
- [ ] Screens remain usable on mobile and desktop; keyboard and labels are accessible.
- [>] Targeted lint for audited non-OCR screens passes with no errors; full lint remains blocked by pre-existing OCR/report/prescription screen issues.
- [x] TypeScript no-emit check and frontend production build pass.

## 7. Quality, security, and delivery

- [>] Backend collection and current core suite: 275 passed; three failures remain in deferred report-parser/OCR tests.
- [>] Unit coverage now includes auth restrictions, bed occupancy fallback, symptom model output, and triage overrides. API integration and cross-user authorization coverage need expansion.
- [ ] Authorization tests cover cross-user access and role escalation.
- [>] Audited non-OCR frontend lint, TypeScript, and production build pass; full lint still reports existing issues in deferred OCR/report/prescription screens.
- [ ] API errors do not expose secrets or internal exception details.
- [ ] Deployment configuration starts successfully from documented instructions.
- [ ] Documentation reflects implemented behavior and known deferred work.

## Initial evidence

- Repository inspection on 2026-10-24 found eight AI-related screens/APIs, though the report and prescription OCR paths are deferred above.
- Initial inspection found placeholder admin department/model screens, nonfunctional profile controls, and public staff-role registration; these were replaced with working API-backed workflows.
- Doctor schedule listing is not scoped to doctor users, and the appointment list filters only on patient_id.
- Initial inspection found unprotected triage queue/bed endpoints and a fixed 400/500 bed forecast; both are now protected and use database inventory.
- Latest backend suite: 275 passed, 3 failed; all three failures are report-parser tests in the user-deferred OCR/report-processing scope.
- Latest targeted lint and TypeScript checks pass for audited non-OCR screens. Full lint still includes existing deferred OCR/report/prescription screen errors.
- Auth unit tests verify non-patient registration is denied and disabled accounts cannot log in.
- Chatbot now resumes a user's latest saved session and exposes owner-scoped history retrieval.
- Admin patient directory and audit-history screens use protected APIs; selected high-value mutations now write audit records in the same transaction.
- Doctor queue reads are restricted to the doctor's own department and include patient names for staff workflow; queue changes are recorded in audit history.
- Bed Availability was previously linked only for administrators; patient and doctor sidebar links are now present. Doctor Reports was previously blocked by a patient-only route guard; the guard now allows doctors as well.
- Active appointment slots now have a database uniqueness constraint, so concurrent bookings receive a conflict response.
- Frontend production build generated all dashboard and admin routes successfully.
- The initial service probe found no response on ports 3000/8000. The backend was then started at `http://localhost:8000`; the frontend process was already active at `http://localhost:3000`. Browser origin access was declined, so UI flows could not be exercised.
- Do not overwrite or revert pre-existing local changes. In particular, OCR and report-processing files are intentionally excluded from edits in this pass.
