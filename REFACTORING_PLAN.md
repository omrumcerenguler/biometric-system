# Multi-Client Biometric Service Refactoring Plan

## Executive Summary

Current system: Portal-centric monolith → Target: Service-oriented (backend service + multiple clients)

**Key Changes:**
- Backend becomes standalone authentication service (no portal assumptions)
- Client abstraction layer (API keys, client registration)
- Generic API responses (not portal-specific)
- Separate frontend apps as independent clients
- Mono-repo structure (easier deployment coordination)

---

## PHASE 1: BACKEND RESTRUCTURING

### 1.1 New Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                              # [MODIFIED] Remove CORS hardcoding
│   ├── core/
│   │   ├── config.py                        # [MODIFIED] Add client config
│   │   ├── security.py                      # [MODIFIED] Token/API key handling
│   │   └── constants.py                     # [NEW] Shared constants
│   ├── domain/
│   │   ├── schemas.py                       # [MODIFIED] Generic responses
│   │   ├── client.py                        # [NEW] Client registration schemas
│   │   └── enums.py
│   ├── db/
│   │   ├── models.py                        # [MODIFIED] Add Client model
│   │   ├── session.py
│   │   ├── repositories.py                  # [MODIFIED] Add ClientRepository
│   │   └── base.py
│   ├── api/
│   │   ├── v1/                              # [NEW] API versioning
│   │   │   ├── __init__.py
│   │   │   ├── routes_auth.py               # [MODIFIED] Service-oriented
│   │   │   ├── routes_enroll.py             # [RENAMED from routes_enrollment]
│   │   │   ├── routes_verify.py             # [RENAMED/REFACTORED from routes_identify]
│   │   │   ├── routes_admin.py              # [MODIFIED]
│   │   │   └── routes_health.py             # [NEW]
│   │   └── dependencies/
│   │       ├── auth.py                      # [MODIFIED] Client auth
│   │       └── client.py                    # [NEW] Client dependency
│   ├── services/
│   │   ├── authentication_service.py        # [EXISTING - no changes]
│   │   ├── face_processor.py                # [EXISTING - no changes]
│   │   ├── voice_processor.py               # [EXISTING - no changes]
│   │   ├── client_service.py                # [NEW] Client registration/keys
│   │   └── ... (other services)
│   └── utils/
│       └── ... (existing)
├── requirements.txt
├── alembic/                                 # [NEW] Database migrations
└── .env.example                             # [NEW]
```

---

### 1.2 Database Schema Changes

**File: `app/db/models.py`**

**ADD:**
```python
class Client(Base):
    __tablename__ = "client"
    
    client_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)  # e.g. "portal", "banking-app"
    api_key: Mapped[str] = mapped_column(String(256), unique=True, index=True)  # secure random key
    secret: Mapped[str] = mapped_column(String(256), nullable=False)  # for HMAC signing
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Scope/permissions (set of capabilities)
    scopes: Mapped[str] = mapped_column(String, default="enroll,verify")

    # Allow this client to manage users?
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Rate limit settings (tokens per minute)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=1000)
```

**MODIFY `User` model:**
```python
class User(Base):
    # ... existing fields ...
    
    # Which client registered this user? (NULL = system user)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"), nullable=True)
    client = relationship("Client")
```

---

### 1.3 Configuration Changes

**File: `app/core/config.py`**

**ADD:**
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Client Management
    ALLOW_DYNAMIC_CLIENT_REGISTRATION: bool = False  # Admin-only by default
    API_KEY_HEADER: str = "X-API-Key"
    API_SECRET_HEADER: str = "X-API-Secret"
    
    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5500"]
    )
    
    # API Versioning
    API_VERSION: str = "v1"
    DEPRECATE_V0: bool = False  # When True, old endpoints return deprecation warning
```

---

### 1.4 Authentication & Authorization Layer

**File: `app/api/dependencies/client.py` [NEW]**

```python
from fastapi import Depends, HTTPException, Header, Security
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.db.models import Client
from sqlalchemy import select
from app.core.config import settings

async def get_client_from_api_key(
    session: AsyncSession = Depends(get_session),
    api_key: str = Header(..., alias=settings.API_KEY_HEADER),
) -> Client:
    """Extract and validate client from API key."""
    result = await session.execute(
        select(Client).where(Client.api_key == api_key, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=401, detail="INVALID_API_KEY")
    
    return client

async def client_can(permission: str):
    """Check if client has specific permission."""
    async def check_permission(client: Client = Depends(get_client_from_api_key)) -> Client:
        if permission not in client.scopes.split(","):
            raise HTTPException(status_code=403, detail="INSUFFICIENT_PERMISSIONS")
        return client
    return check_permission
```

**File: `app/core/security.py` [MODIFIED]**

```python
# [ADD] Support for client tokens
def create_token_for_user(
    data: dict,
    client_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT token tied to a specific client."""
    to_encode = data.copy()
    to_encode["client_id"] = client_id
    to_encode["iat"] = datetime.utcnow()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode["exp"] = expire
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token_for_client(token: str, client_id: int) -> dict:
    """Verify JWT and ensure it belongs to expected client."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    if payload.get("client_id") != client_id:
        raise HTTPException(status_code=401, detail="TOKEN_CLIENT_MISMATCH")
    
    return payload
```

---

### 1.5 Generic Response Schemas

**File: `app/domain/schemas.py` [MODIFIED]**

```python
from typing import Any, Optional, Generic, TypeVar

T = TypeVar("T")

# [NEW] Generic API response wrapper
class ServiceResponse(BaseModel, Generic[T]):
    """Standard response wrapper for all endpoints."""
    success: bool
    code: str  # e.g. "OK", "INVALID_INPUT", "AUTHENTICATION_FAILED"
    message: str
    data: Optional[T] = None
    debug: Optional[dict] = None  # Only in dev mode

# [NEW] Standardized error response
class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str

# [REFACTORED] Keep existing schemas but make them generic

class EnrollmentRequest(BaseModel):
    """Enrollment input - client-agnostic."""
    username: str
    face_samples: list[str]  # base64
    voice_samples: list[str]  # base64

class VerifyRequest(BaseModel):
    """Verification input - generic."""
    face_image_b64: Optional[str] = None
    voice_wav_b64: Optional[str] = None

# [NEW] Response should NOT include client/portal-specific fields
class VerifyResponse(BaseModel):
    """Generic verification result."""
    decision: str  # "ACCEPTED" / "REJECTED"
    confidence: float  # 0-1
    matched_user_id: Optional[int] = None  # System ID, safe to expose
    reason: str
    
    # Debug info (omitted in production)
    debug_trace: Optional[dict] = None
```

---

### 1.6 API Endpoint Refactoring

**File: `app/api/v1/routes_verify.py` [NEW - renamed from routes_identify]**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.client import get_client_from_api_key
from app.api.dependencies.auth import get_current_user
from app.db.models import Client, User
from app.domain.schemas import VerifyRequest, ServiceResponse
from app.services.authentication_service import AuthenticationService

router = APIRouter(prefix="/verify", tags=["verify"])

@router.post("/", response_model=ServiceResponse[dict])
async def verify(
    req: VerifyRequest,
    session: AsyncSession = Depends(get_session),
    client: Client = Depends(get_client_from_api_key),
    token: str = Header(..., alias="Authorization"),
) -> ServiceResponse[dict]:
    """
    Verify user using face/voice.
    
    **Required:**
    - X-API-Key: Client API key
    - Authorization: Bearer {JWT token from /auth/verify}
    """
    try:
        # Parse Bearer token
        scheme, credentials = token.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="INVALID_AUTH_SCHEME")
        
        payload = verify_token_for_client(credentials, client.client_id)
        user_id = payload.get("sub")
        
        # Convert inputs
        img = None if not req.face_image_b64 else b64_to_bgr_image(req.face_image_b64)
        audio, sr = None, None if not req.voice_wav_b64 else b64_to_wav_mono(req.voice_wav_b64)
        
        # Call existing service
        result = await _auth_service.verify_multimodal(
            session=session,
            user_id=user_id,
            face_img=img,
            audio=audio,
            sr=sr,
        )
        
        return ServiceResponse(
            success=result["decision"] == "ACCEPTED",
            code="OK" if result["decision"] == "ACCEPTED" else "VERIFICATION_FAILED",
            message="User verified successfully" if result["decision"] == "ACCEPTED" else "Verification failed",
            data={
                "decision": result["decision"],
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", ""),
            },
            debug=result.get("debug") if settings.DEBUG else None,
        )
    
    except Exception as e:
        return ServiceResponse(
            success=False,
            code="SERVER_ERROR",
            message=str(e),
        )
```

**File: `app/api/v1/routes_auth.py` [MODIFIED]**

```python
@router.post("/verify", response_model=ServiceResponse[dict])
async def auth_verify(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),
    client: Client = Depends(get_client_from_api_key),
) -> ServiceResponse[dict]:
    """
    Authenticate user and get JWT token for verification endpoints.
    
    **Returns:** JWT token valid for {ACCESS_TOKEN_EXPIRE_MINUTES} minutes
    """
    result = await _auth_service.login_user(
        session=session,
        username=req.username,
        password=req.password,
    )
    
    if not result.get("success"):
        return ServiceResponse(
            success=False,
            code="AUTHENTICATION_FAILED",
            message=result.get("message"),
        )
    
    user = await session.execute(select(User).where(User.username == req.username))
    user_obj = user.scalar_one_or_none()
    
    token = create_token_for_user(
        data={"sub": user_obj.user_id, "username": req.username},
        client_id=client.client_id,
    )
    
    return ServiceResponse(
        success=True,
        code="OK",
        message="Authentication successful",
        data={"token": token, "user_id": user_obj.user_id},
    )
```

---

### 1.7 Client Management Endpoints

**File: `app/api/v1/routes_admin.py` [MODIFIED]**

```python
# [ADD] Client registration endpoint (admin only)

@router.post("/clients", response_model=ServiceResponse[dict])
async def register_client(
    req: ClientRegistrationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> ServiceResponse[dict]:
    """
    Register a new client application.
    Only callable by admin users.
    """
    api_key = secrets.token_urlsafe(32)
    secret = secrets.token_urlsafe(32)
    
    new_client = Client(
        name=req.name,
        api_key=api_key,
        secret=secret,
        scopes=",".join(req.scopes or ["enroll", "verify"]),
        can_manage_users=req.can_manage_users or False,
    )
    
    session.add(new_client)
    await session.commit()
    
    return ServiceResponse(
        success=True,
        code="OK",
        message="Client registered",
        data={
            "client_id": new_client.client_id,
            "api_key": api_key,
            "secret": secret,
            "name": new_client.name,
        },
    )
```

---

### 1.8 Main App Changes

**File: `app/main.py` [MODIFIED]**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="Biometric Authentication Service",
    version=settings.API_VERSION,
    description="Multi-modal biometric verification service",
)

# [MODIFIED] Flexible CORS from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# [NEW] API Versioning
app.include_router(router_v1_auth)
app.include_router(router_v1_verify)
app.include_router(router_v1_enroll)
app.include_router(router_v1_admin)
app.include_router(router_v1_health)

# [ADD] Deprecation warning for v0 endpoints (if DEPRECATE_V0)
@app.deprecated(response=None)
@app.get("/v0/")
async def v0_deprecated():
    return {
        "error": "API v0 is deprecated",
        "upgrade_to": "/v1/",
    }
```

---

## PHASE 2: FRONTEND DECOUPLING

### 2.1 New Frontend Structure

```
frontend/
├── shared/                                   # [NEW] Shared utilities
│   ├── api-client.js                        # [NEW] Generic HTTP wrapper
│   ├── config.js                            # [MODIFIED] Environment config
│   └── constants.js                         # [NEW] App constants
├── portal/                                   # Portal app
│   ├── config.js                            # [NEW] Portal-specific config
│   ├── main.html
│   ├── js/
│   │   ├── app.js                           # [NEW] Main entry
│   │   ├── auth.js                          # [MODIFIED]
│   │   ├── verify.js                        # [MODIFIED]
│   │   └── enroll.js                        # [MODIFIED]
│   └── assets/
├── banking-app/                              # [NEW] Example 2nd client
│   ├── config.js
│   └── ...
└── admin-panel/                              # [NEW] Example 3rd client
    ├── config.js
    └── ...
```

### 2.2 API Client Abstraction

**File: `frontend/shared/api-client.js` [NEW]**

```javascript
/**
 * Generic HTTP client for biometric service
 * Handles authentication, error handling, retries
 */
export class BiometricServiceClient {
    constructor(config) {
        this.baseURL = config.API_BASE;
        this.apiKey = config.API_KEY;
        this.apiSecret = config.API_SECRET;
        this.token = null;
        this.version = config.VERSION || "v1";
    }

    async request(method, endpoint, body = null, headers = {}) {
        const url = `${this.baseURL}/${this.version}${endpoint}`;
        
        const defaultHeaders = {
            "X-API-Key": this.apiKey,
            "Content-Type": "application/json",
            ...headers,
        };
        
        if (this.token) {
            defaultHeaders["Authorization"] = `Bearer ${this.token}`;
        }
        
        try {
            const response = await fetch(url, {
                method,
                headers: defaultHeaders,
                body: body ? JSON.stringify(body) : null,
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (err) {
            throw {
                code: "HTTP_ERROR",
                message: err.message,
                endpoint,
            };
        }
    }

    async authenticate(username, password) {
        const result = await this.request("POST", "/auth/verify", {
            username,
            password,
        });
        
        if (result.success) {
            this.token = result.data.token;
            return result.data;
        } else {
            throw result;
        }
    }

    async verify(faceB64, voiceB64) {
        return this.request("POST", "/verify", {
            face_image_b64: faceB64,
            voice_wav_b64: voiceB64,
        });
    }

    async enroll(username, faceSamples, voiceSamples) {
        return this.request("POST", "/enroll/biometric", {
            username,
            face_samples: faceSamples,
            voice_samples: voiceSamples,
        });
    }
}
```

### 2.3 Portal Configuration

**File: `frontend/portal/config.js` [NEW]**

```javascript
export const PORTAL_CONFIG = {
  APP_NAME: "Biometric Portal",
  APP_VERSION: "1.0.0",
  
  // Service connection
  API_BASE: process.env.REACT_APP_API_BASE || "http://localhost:8000",
  API_VERSION: "v1",
  
  // Client credentials (from backend registration)
  API_KEY: process.env.REACT_APP_API_KEY || "portal-api-key-here",
  API_SECRET: process.env.REACT_APP_API_SECRET || "",
  
  // UI behavior
  FACE_CAPTURE_TIMEOUT_MS: 30000,
  VOICE_CAPTURE_TIMEOUT_MS: 5000,
};
```

### 2.4 Portal App Entry Point

**File: `frontend/portal/js/app.js` [NEW]**

```javascript
import { BiometricServiceClient } from "../../shared/api-client.js";
import { PORTAL_CONFIG } from "../config.js";

// Single instance for entire app
export const biometricClient = new BiometricServiceClient(PORTAL_CONFIG);

// Initialize app
document.addEventListener("DOMContentLoaded", async () => {
    console.log("Portal initialized");
    console.log("Service:", PORTAL_CONFIG.API_BASE);
});
```

---

## PHASE 3: SECURITY MODEL

### 3.1 Authentication Flow

**Portal (or any client):**
1. Client registers with backend (admin action):
   ```
   POST /admin/clients
   → Returns: API_KEY, API_SECRET
   ```

2. Portal stores API_KEY in frontend code (or `.env`)

3. User logs in:
   ```
   POST /auth/verify
   Headers: X-API-Key: {API_KEY}
   Body: {username, password}
   → Returns: JWT token
   ```

4. Portal uses JWT for subsequent requests:
   ```
   POST /verify
   Headers: 
     X-API-Key: {API_KEY}
     Authorization: Bearer {JWT}
   ```

### 3.2 Client Isolation

Each client gets:
- Unique `API_KEY` (for identification)
- `API_SECRET` (unused in v1, for HMAC in v2)
- Scopes (e.g., "enroll,verify" or "verify-only")
- Rate limiting (e.g., 1000 req/min)
- User ownership rules (users registered by Client A visible only to Client A)

**Database Query Enforces Client Boundary:**
```python
# Only see users owned by this client
users = await session.execute(
    select(User).where(User.client_id == client.client_id)
)
```

---

## PHASE 4: MIGRATION STRATEGY (ZERO DOWNTIME)

### 4.1 Step 1: Create New API (v1) Alongside Old (v0)

**File: `app/api/v0/routes_identify.py`**
```python
# Keep OLD endpoints as-is, mark deprecated
# These call same services but with hardcoded portal behavior
```

**File: `app/api/v1/routes_verify.py`**
```python
# New generic endpoints with client abstraction
```

Both exist simultaneously.

### 4.2 Step 2: Run Dual Systems

**backend/app/main.py:**
```python
# Include both v0 and v1
app.include_router(v0_routes, prefix="/v0")  # OLD (unchanged)
app.include_router(v1_routes, prefix="/v1")  # NEW (service-oriented)
```

### 4.3 Step 3: Migrate Portal to v1 (Gradual)

1. Create new `portal.v1.js` that uses v1 API
2. Test v1 in staging
3. Portal uses `v1` by default (v0 fallback)
4. Monitor error rates

### 4.4 Step 4: Deprecate v0 (After 3 months)

```python
if settings.DEPRECATE_V0:
    @app.get("/v0/")
    async def v0_deprecated():
        return {"error": "v0 deprecated", "migrate_to": "/v1"}
```

---

## PHASE 5: PROJECT STRUCTURE

### 5.1 Mono-Repo Layout (Recommended)

```
biometric-system/
├── backend/                          # Backend service
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── shared/                       # Common code
│   ├── portal/                       # Portal client
│   ├── banking-app/                  # Banking client (example)
│   ├── package.json
│   └── .env.example
├── docs/
│   ├── API.md                        # API documentation
│   ├── SETUP.md
│   └── ARCHITECTURE.md
├── docker-compose.yml                # Run everything locally
└── README.md
```

### 5.2 Deployment Structure

**Docker Compose:**
```yaml
version: '3'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db/biometric
      - CORS_ALLOWED_ORIGINS=["http://portal:5500", "http://banking:5501"]
  
  portal:
    build: ./frontend/portal
    ports: ["5500:5500"]
    environment:
      - REACT_APP_API_BASE=http://backend:8000
      - REACT_APP_API_KEY=portal-key
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=biometric
```

---

## PHASE 6: IMPLEMENTATION CHECKLIST

### Backend Changes:
- [ ] Create `app/db/models.py::Client` model
- [ ] Create `app/core/security.py::create_token_for_user()` 
- [ ] Create `app/api/dependencies/client.py`
- [ ] Create `app/api/v1/` folder structure
- [ ] Refactor endpoints to use `ServiceResponse` wrapper
- [ ] Update `app/main.py` for routing
- [ ] Add `.env` support
- [ ] Create database migration script

### Frontend Changes:
- [ ] Create `frontend/shared/api-client.js`
- [ ] Create `frontend/portal/config.js`
- [ ] Refactor `portal/js/*.js` to use new client
- [ ] Remove hardcoded API URLs
- [ ] Test with new v1 endpoints
- [ ] Create `.env.example`

### DevOps:
- [ ] Create `docker-compose.yml`
- [ ] Update backend `Dockerfile`
- [ ] Create frontend `Dockerfile`
- [ ] Document API in `docs/API.md`

---

## PHASE 7: FILE MODIFICATIONS SUMMARY

### Critical Core Changes:

| File | Change | Priority |
|------|--------|----------|
| `app/db/models.py` | Add `Client` model | HIGH |
| `app/core/config.py` | Add client config | HIGH |
| `app/core/security.py` | Add client token logic | HIGH |
| `app/api/dependencies/client.py` | NEW | HIGH |
| `app/main.py` | Add routing, flexible CORS | HIGH |
| `app/domain/schemas.py` | Add `ServiceResponse` generic | MEDIUM |
| `frontend/shared/api-client.js` | NEW abstraction layer | HIGH |
| `frontend/portal/config.js` | NEW environment config | HIGH |

### Safe (Non-Breaking) Changes:

- All NEW files listed above can be added without touching existing code
- Existing services (`AuthenticationService`, etc.) remain unchanged
- v0 API can coexist with v1
- Portal can gradually migrate endpoints one by one

---

## QUICK START (After Refactoring)

**1. Register a new client app (as admin):**
```bash
curl -X POST http://localhost:8000/v1/admin/clients \
  -H "Authorization: Bearer {admin_token}" \
  -d '{"name":"my-app"}'
# Returns: API_KEY, API_SECRET
```

**2. Portal uses it:**
```javascript
const client = new BiometricServiceClient({
    API_BASE: "http://localhost:8000",
    API_KEY: "returned-api-key",
    VERSION: "v1",
});
```

**3. Login and verify:**
```javascript
await client.authenticate(username, password);
const result = await client.verify(faceB64, voiceB64);
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing portal | Keep v0 endpoints, gradual migration |
| Database migration failures | Test in staging first, maintain backups |
| API key exposure | Store in env files, never in code |
| Client cross-contamination | Enforce `client_id` in all queries |
| Token theft | Use short expiry (15 min), refresh tokens in v2 |

---

