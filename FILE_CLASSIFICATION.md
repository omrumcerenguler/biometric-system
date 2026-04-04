# FILE CLASSIFICATION

## 1. Backend (Service Layer)

These files/folders are strictly backend service logic (API, domain, database, biometric processing, security, and backend runtime assets):

- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/api/routes_admin.py`
- `backend/app/api/routes_auth.py`
- `backend/app/api/routes_enrollment.py`
- `backend/app/api/routes_identify.py`
- `backend/app/api/dependencies/auth.py`
- `backend/app/core/`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/db/`
- `backend/app/db/base.py`
- `backend/app/db/models.py`
- `backend/app/db/repositories.py`
- `backend/app/db/session.py`
- `backend/app/domain/`
- `backend/app/domain/enums.py`
- `backend/app/domain/schemas.py`
- `backend/app/services/`
- `backend/app/services/aasist_model.py`
- `backend/app/services/audit_logger.py`
- `backend/app/services/authentication_service.py`
- `backend/app/services/eye_state_detector.py`
- `backend/app/services/face_liveness_state_machine.py`
- `backend/app/services/face_processor.py`
- `backend/app/services/fusion.py`
- `backend/app/services/liveness_detector.py`
- `backend/app/services/voice_processor.py`
- `backend/app/services/voice_spoof_detector.py`
- `backend/app/utils/`
- `backend/app/utils/audio_io.py`
- `backend/app/utils/image_io.py`
- `backend/app/__init__.py`
- `backend/alembic/`
- `backend/alembic/versions/`
- `backend/requirements.txt`
- `backend/tests/`
- `backend/tests/test_fusion.py`
- `backend/models/`
- `backend/models/AASIST.pth`
- `backend/logs/`
- `backend/logs/audit.log.jsonl`
- `backend/sample_data/`

## 2. Frontend (Client Layer)

These files/folders are strictly portal/client UI and browser-side application behavior:

- `frontend/portal/`
- `frontend/portal/login_portal.html`
- `frontend/portal/office_login.html`
- `frontend/portal/dashboard_portal.html`
- `frontend/biometric/`
- `frontend/biometric/enroll.html`
- `frontend/biometric/identify.html`
- `frontend/assets/css/`
- `frontend/assets/css/portal.css`
- `frontend/assets/css/dashboard.css`
- `frontend/assets/css/style.css`
- `frontend/assets/js/camera.js`
- `frontend/assets/js/dom.js`
- `frontend/assets/js/index.js`
- `frontend/assets/js/navigation.js`
- `frontend/assets/js/portal.js`
- `frontend/assets/js/dashboard.js`
- `frontend/assets/js/voice.js`

## 3. Mixed / Needs Refactoring

These files currently mix client concerns with service/business concerns and should be refactored for cleaner separation:

- `frontend/assets/js/api.js`
  - Mixes a frontend API helper with backend contract details (hardcoded endpoint paths and auth token header behavior).
- `frontend/assets/js/config.js`
  - Contains client runtime config and service-level verification thresholds in the same place (`fusionThreshold`, challenge limits).
- `frontend/assets/js/enroll.js`
  - Mixes UI flow/control with biometric enrollment business rules (sample targets, angle order, phrase scoring, duplicate-check orchestration).
- `frontend/assets/js/identify.js`
  - Mixes page UI logic with liveness/auth decision workflow (challenge sequence policy, retry strategy, step ordering).
- `backend/app/main.py`
  - Service bootstrap includes portal-specific CORS origins (`localhost:5500`), which couples backend deployment to one client.
- `backend/app/services/authentication_service.py`
  - Contains client-specific login assumptions (explicit "Portal Login" section and response shape tailored to current portal flow).

## 4. Summary

Current separation quality is **partial**.

- Good: backend codebase is already organized into API/core/db/domain/services modules.
- Good: portal UI files are physically separated under `frontend/`.
- Gap: key browser files still embed service/business workflow logic, and backend still carries portal-specific coupling points.
- Result: architecture is close to service-client separation, but not yet fully client-agnostic.