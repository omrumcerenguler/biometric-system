# Advanced Implementation Guide - Logging, Error Handling, Testing & Deployment

---

## PART 1: ERROR HANDLING & RESPONSE STANDARDIZATION

### 1.1 Error Response Pattern

All errors should return `ServiceResponse` with appropriate status codes:

```python
# backend/app/api/v1/routes_verify.py - Error handling example

from enum import Enum

class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    # Authentication
    INVALID_API_KEY = "INVALID_API_KEY"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_MISMATCH = "TOKEN_MISMATCH"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # Validation
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_IMAGE = "INVALID_IMAGE"
    INVALID_AUDIO = "INVALID_AUDIO"
    
    # Business Logic
    USER_NOT_FOUND = "USER_NOT_FOUND"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    ENROLLMENT_FAILED = "ENROLLMENT_FAILED"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    
    # System
    SERVER_ERROR = "SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

# HTTP status code mapping
ERROR_CODE_TO_HTTP = {
    ErrorCode.INVALID_API_KEY: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_MISMATCH: 403,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.SERVER_ERROR: 500,
}

def error_response(
    code: ErrorCode,
    message: str,
    status_code: int = None,
    debug_info: dict = None,
) -> tuple[ServiceResponse, int]:
    """Generate standard error response."""
    if status_code is None:
        status_code = ERROR_CODE_TO_HTTP.get(code, 500)
    
    return (
        ServiceResponse(
            success=False,
            code=code.value,
            message=message,
            debug=debug_info if settings.DEBUG else None,
        ),
        status_code,
    )
```

### 1.2 Exception Handling Middleware

```python
# backend/app/middleware/exception_handler.py [NEW]

from fastapi import Request
from fastapi.responses import JSONResponse
from app.domain.schemas import ServiceResponse
from app.core.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    
    # Generate request ID for correlation
    request_id = str(uuid.uuid4())
    
    # Log full exception
    logger.exception(
        f"Unhandled exception [request_id={request_id}]",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else "unknown",
        }
    )
    
    # Return generic error response (don't expose internal details)
    response = ServiceResponse(
        success=False,
        code="SERVER_ERROR",
        message="An unexpected error occurred" if not settings.DEBUG else str(exc),
        debug={"request_id": request_id} if settings.DEBUG else None,
    )
    
    return JSONResponse(
        status_code=500,
        content=response.dict(),
        headers={"X-Request-ID": request_id}
    )
```

### 1.3 Request Context & Correlation IDs

```python
# backend/app/middleware/request_context.py [NEW]

from fastapi import Request
from contextvars import ContextVar
from uuid import uuid4
import time
import logging

# Context variables
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
client_id_ctx: ContextVar[int] = ContextVar("client_id", default=0)
user_id_ctx: ContextVar[int] = ContextVar("user_id", default=0)

logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Add request context and tracking."""
    
    # Generate request ID
    request_id = str(uuid4())
    request_id_ctx.set(request_id)
    
    # Extract client from header (if available)
    client_id = request.headers.get("X-Client-ID", "0")
    if client_id != "0":
        client_id_ctx.set(int(client_id))
    
    # Track timing
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log request
        duration = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "client_id": client_id_ctx.get(),
                "status": response.status_code,
                "duration_ms": int(duration * 1000),
            }
        )
        
        return response
    
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            f"{request.method} {request.url.path} - Exception",
            extra={
                "request_id": request_id,
                "duration_ms": int(duration * 1000),
            },
            exc_info=True
        )
        raise
```

### 1.4 Add Middleware to Main App

```python
# backend/app/main.py [ADD to imports]

from app.middleware.request_context import add_request_context
from app.middleware.exception_handler import global_exception_handler

# [ADD after CORS middleware]
app.middleware("http")(add_request_context)
```

---

## PART 2: STRUCTURED LOGGING

### 2.1 Logging Configuration

```python
# backend/app/core/logging_config.py [NEW]

import logging
import logging.config
import json
from pythonjsonlogger import jsonlogger
from app.core.config import settings
import sys

class ContextualFilter(logging.Filter):
    """Add request context to log records."""
    
    def filter(self, record):
        from app.middleware.request_context import request_id_ctx, client_id_ctx, user_id_ctx
        
        record.request_id = request_id_ctx.get()
        record.client_id = client_id_ctx.get()
        record.user_id = user_id_ctx.get()
        return True

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s %(client_id)s",
        },
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s"
        }
    },
    "filters": {
        "context": {
            "()": ContextualFilter,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "formatter": "standard" if settings.DEBUG else "json",
            "stream": sys.stdout,
            "filters": ["context"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/api.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "filters": ["context"],
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/errors.log",
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "json",
            "level": "ERROR",
            "filters": ["context"],
        },
    },
    "loggers": {
        "app": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "handlers": ["console", "file", "error_file"],
        }
    }
}

# Setup
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")
```

### 2.2 Usage Examples

```python
# In any module:
import logging
from app.middleware.request_context import request_id_ctx

logger = logging.getLogger(__name__)

# Standard logging with automatic context injection
logger.info("User login attempt", extra={
    "username": username,
    "source": "portal",
})

logger.warning("Face image quality low", extra={
    "quality_score": quality,
    "user_id": user_id,
})

logger.error("Verification failed", extra={
    "reason": "insufficient_samples",
    "user_id": user_id,
    "debug": verification_details,
})

# Output (JSON):
# {
#   "timestamp": "2024-04-04T10:30:45.123Z",
#   "level": "INFO",
#   "name": "app.services.authentication_service",
#   "message": "User login attempt",
#   "username": "john",
#   "source": "portal",
#   "request_id": "550e8400-e29b-41d4-a716-446655440000",
#   "client_id": "1"
# }
```

---

## PART 3: RATE LIMITING

### 3.1 Per-Client Rate Limiting

```python
# backend/app/middleware/rate_limit.py [NEW]

from datetime import datetime, timedelta
from collections import defaultdict
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """In-memory rate limiter (for single instance; use Redis for distributed)."""
    
    def __init__(self):
        self.requests = defaultdict(list)  # client_id -> [(timestamp, endpoint), ...]
    
    def is_allowed(self, client_id: int, rate_limit_rpm: int = 1000) -> bool:
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if ts > one_minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= rate_limit_rpm:
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={"client_id": client_id}
            )
            return False
        
        # Record request
        self.requests[client_id].append(now)
        return True

_rate_limiter = RateLimiter()

from fastapi import Depends, HTTPException, status

async def check_rate_limit(client: Client = Depends(get_client_from_api_key)) -> Client:
    """Rate limiting dependency."""
    if not _rate_limiter.is_allowed(client.client_id, client.rate_limit_rpm):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )
    return client
```

**Usage in routes:**
```python
@router.post("/verify/")
async def verify(
    request: VerifyRequest,
    session: AsyncSession = Depends(get_session),
    client: Client = Depends(check_rate_limit),  # [ADD]
    authorization: str = Header(...),
):
    # ... rest of implementation
```

---

## PART 4: TESTING STRATEGY

### 4.1 Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # [NEW] Fixtures
│   ├── test_auth.py                   # [NEW]
│   ├── test_verify.py                 # [NEW]
│   ├── test_enroll.py                 # [NEW]
│   ├── test_admin.py                  # [NEW]
│   ├── integration/
│   │   ├── test_auth_flow.py          # [NEW]
│   │   └── test_verify_flow.py        # [NEW]
│   └── fixtures/
│       ├── sample_images/
│       └── sample_audio/
```

### 4.2 Test Fixtures

```python
# backend/tests/conftest.py [NEW]

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_session
from app.db.models import Client, User
from app.core.config import settings
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db():
    """Create in-memory test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def get_test_session():
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_session] = get_test_session
    yield async_session
    
    await engine.dispose()

@pytest.fixture
async def test_client(db):
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_client_obj(db) -> Client:
    """Create test client database object."""
    async_session = db
    async with async_session() as session:
        client = Client(
            name="Test Portal",
            api_key="test-api-key-123",
            secret="test-secret",
            scopes="enroll,verify",
            is_active=True,
        )
        session.add(client)
        await session.commit()
        await session.refresh(client)
        return client

@pytest.fixture
async def test_user(db, test_client_obj) -> User:
    """Create test user."""
    async_session = db
    async with async_session() as session:
        user = User(
            username="testuser",
            password_hash="hashed_password",
            email="test@example.com",
            client_id=test_client_obj.client_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
```

### 4.3 Example Tests

```python
# backend/tests/test_auth.py [NEW]

import pytest
from app.domain.schemas import LoginRequest

@pytest.mark.asyncio
async def test_auth_verify_success(test_client, test_client_obj, test_user):
    """Test successful authentication."""
    response = await test_client.post(
        "/v1/auth/verify",
        json={
            "username": "testuser",
            "password": "test_password",
        },
        headers={
            "X-API-Key": "test-api-key-123",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["code"] == "OK"
    assert "token" in data["data"]

@pytest.mark.asyncio
async def test_auth_verify_invalid_client(test_client):
    """Test with invalid API key."""
    response = await test_client.post(
        "/v1/auth/verify",
        json={
            "username": "testuser",
            "password": "password",
        },
        headers={
            "X-API-Key": "invalid-api-key",
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["success"] == False
    assert data["code"] == "INVALID_API_KEY"

@pytest.mark.asyncio
async def test_auth_verify_missing_client_header(test_client):
    """Test missing API key header."""
    response = await test_client.post(
        "/v1/auth/verify",
        json={
            "username": "testuser",
            "password": "password",
        }
    )
    
    assert response.status_code == 422  # Validation error
```

### 4.4 Integration Tests

```python
# backend/tests/integration/test_auth_flow.py [NEW]

@pytest.mark.asyncio
async def test_complete_auth_verify_flow(test_client, test_client_obj, test_user):
    """Test complete login → verify flow."""
    
    # Step 1: Login
    login_response = await test_client.post(
        "/v1/auth/verify",
        json={
            "username": "testuser",
            "password": "test_password",
        },
        headers={"X-API-Key": "test-api-key-123"},
    )
    
    assert login_response.status_code == 200
    token = login_response.json()["data"]["token"]
    
    # Step 2: Verify (with token)
    verify_response = await test_client.post(
        "/v1/verify/",
        json={
            "face_image_b64": "fake_image_data",  # Would be real base64 in production
            "voice_wav_b64": None,
        },
        headers={
            "X-API-Key": "test-api-key-123",
            "Authorization": f"Bearer {token}",
        }
    )
    
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert "decision" in data["data"]
```

### 4.5 Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest backend/tests -v

# Run specific test file
pytest backend/tests/test_auth.py -v

# Run with coverage
pytest backend/tests --cov=app --cov-report=html
```

---

## PART 5: DEPLOYMENT & DOCKER

### 5.1 Backend Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/')"

# Run migrations and start app
CMD bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### 5.2 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile

FROM node:18-alpine AS builder

WORKDIR /app

# Copy source
COPY . .

# No build step for vanilla JS
# If using React/Vue, add: RUN npm install && npm run build

EXPOSE 5500

# Simple HTTP server for static files
CMD ["npx", "http-server", "portal", "-p", "5500", "--gzip"]
```

### 5.3 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  # Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: biometric_user
      POSTGRES_PASSWORD: biometric_password
      POSTGRES_DB: biometric
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U biometric_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://biometric_user:biometric_password@db/biometric
      DEBUG: "false"
      SECRET_KEY: change-this-in-production
      CORS_ALLOWED_ORIGINS: '["http://localhost:5500", "http://portal:5500"]'
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend Portal
  portal:
    build: ./frontend
    environment:
      REACT_APP_API_BASE: http://backend:8000
      REACT_APP_API_KEY: portal-api-key
      REACT_APP_DEBUG: "false"
    ports:
      - "5500:5500"
    depends_on:
      - backend

  # (Optional) Additional clients
  banking-app:
    build:
      context: ./frontend/banking-app
      dockerfile: Dockerfile
    environment:
      REACT_APP_API_BASE: http://backend:8000
      REACT_APP_API_KEY: banking-api-key
    ports:
      - "5501:5500"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 5.4 Production Deployment (Kubernetes)

```yaml
# k8s/backend-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: biometric-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: biometric-backend
  template:
    metadata:
      labels:
        app: biometric-backend
    spec:
      containers:
      - name: api
        image: my-registry/biometric-backend:v2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: connection-string
        - name: DEBUG
          value: "false"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

## PART 6: MONITORING & OBSERVABILITY

### 6.1 Prometheus Metrics (Optional)

```python
# backend/app/middleware/metrics.py [NEW]

from prometheus_client import Counter, Histogram
import time

# Metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

verification_count = Counter(
    'biometric_verifications_total',
    'Total verification attempts',
    ['decision']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    return generate_latest()
```

### 6.2 Logs Analysis

```python
# Useful log queries (using ELK or similar):

# Failed verifications in last 24 hours
{
    "query": {
        "bool": {
            "must": [
                {"term": {"message": "VERIFICATION_FAILED"}},
                {"range": {"timestamp": {"gte": "now-24h"}}}
            ]
        }
    }
}

# API errors by client
{
    "aggs": {
        "by_client": {
            "terms": {
                "field": "client_id"
            },
            "aggs": {
                "errors": {
                    "filter": {"term": {"level": "error"}}
                }
            }
        }
    }
}

# Slow requests
{
    "query": {
        "range": {
            "duration_ms": {"gte": 1000}
        }
    }
}
```

---

## PART 7: MIGRATION CHECKLIST

### Pre-Migration
- [ ] Backup production database
- [ ] Create staging environment matching production
- [ ] Test all changes in staging
- [ ] Prepare rollback plan
- [ ] Notify all client apps about downtime window (if needed)

### Migration Steps
- [ ] Run database migrations (Alembic)
- [ ] Deploy new backend code with v1 routes
- [ ] Verify v0 still works (backward compatibility)
- [ ] Create test client via /admin/clients
- [ ] Test all v1 endpoints manually
- [ ] Update portal to use v1 (gradual testing)
- [ ] Monitor error rates and logs
- [ ] Migrate other clients one-by-one

### Post-Migration
- [ ] Verify all clients connected successfully
- [ ] Check audit logs for any anomalies
- [ ] Performance testing (load, latency)
- [ ] Security audit (CORS, auth flow)
- [ ] Document any manual steps taken
- [ ] Update API documentation

### Rollback Plan
- [ ] Restore database from backup
- [ ] Deploy previous backend version
- [ ] Revert client code to v0 API calls
- [ ] Test all functionality

---

## PART 8: EXAMPLE: ADDING A NEW CLIENT (BANKING APP)

### Step 1: Register Client (One-time)

```bash
# As admin, curl:
curl -X POST http://localhost:8000/v1/admin/clients \
  -H "Authorization: Bearer {admin_token}" \
  -H "X-API-Key: admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Banking App",
    "scopes": ["verify"],
    "can_manage_users": false
  }'

# Response:
{
  "success": true,
  "code": "OK",
  "message": "Client registered successfully",
  "data": {
    "client_id": 2,
    "name": "Banking App",
    "api_key": "banking-api-key-here",
    "secret": "banking-secret-here",
    "scopes": ["verify"]
  }
}
```

### Step 2: Create Banking App Config

```javascript
// frontend/banking-app/config.js

export const BANKING_CONFIG = {
    APP_NAME: "Banking Authentication",
    API_BASE: "https://api.example.com",  // Production
    API_KEY: "banking-api-key-here",  // From step 1
    VERSION: "v1",
    DEBUG: false,
};
```

### Step 3: Banking App Uses Service

```javascript
// frontend/banking-app/js/auth.js

import { BiometricServiceClient } from "../../shared/api-client.js";
import { BANKING_CONFIG } from "../config.js";

const biometricService = new BiometricServiceClient(BANKING_CONFIG);

async function loginWithBiometrics(username, faceImage) {
    try {
        // Authenticate user
        const authResult = await biometricService.authenticate(username, "pin-or-initial-auth");
        
        // Verify face
        const verifyResult = await biometricService.verify(faceImage, null);
        
        if (verifyResult.data.decision === "ACCEPTED") {
            // Grant access
            grantBankingAccess(authResult.user_id);
        } else {
            showError("Face verification failed");
        }
    } catch (err) {
        console.error("Authentication failed", err);
    }
}
```

---

## CONCLUSION

This architecture provides:

✅ **Scalability** - Multiple clients can use same backend
✅ **Security** - Client isolation, audit logging, rate limiting
✅ **Maintainability** - Generic APIs, clear separation of concerns
✅ **Observability** - Structured logging, metrics, correlation IDs
✅ **Testability** - Comprehensive test fixtures and integration tests
✅ **Deployability** - Docker, Kubernetes-ready, rollback plan

Key files to implement (in priority order):
1. Database models + migrations
2. Core security + client authentication
3. v1 API routes
4. Frontend client abstraction
5. Logging + error handling
6. Tests + Docker
7. Monitoring + documentation

