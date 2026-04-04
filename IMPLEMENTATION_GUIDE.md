# Detailed Implementation Guide - Phase 1 & 2

This document provides copy-paste ready code for the refactoring.

---

## PHASE 1: DATABASE SCHEMA

### Step 1: Update Models

**File: `backend/app/db/models.py`**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base

# [ADD] New Client model
class Client(Base):
    __tablename__ = "client"
    
    client_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    api_key: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    secret: Mapped[str] = mapped_column(String(256), nullable=False)
    scopes: Mapped[str] = mapped_column(String(500), default="enroll,verify")
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)
    
    # Relationships
    users = relationship("User", back_populates="client")
    audit_logs = relationship("AuditLog", back_populates="client")
    
    def __repr__(self):
        return f"<Client(name='{self.name}', api_key='{self.api_key[:8]}...')>"

# [MODIFY] Update User model
class User(Base):
    __tablename__ = "user"
    
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # [NEW] Client relationship
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"), nullable=True, index=True)
    client = relationship("Client", back_populates="users")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    biometric_data = relationship("BiometricData", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    __table_args__ = (
        # [MODIFIED] Unique constraint now includes client_id
        # This allows same username in different clients
        # UniqueConstraint("client_id", "username", name="uq_client_username"),
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', client_id={self.client_id})>"

# [MODIFY] Update AuditLog model
class AuditLog(Base):
    __tablename__ = "audit_log"
    
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=True, index=True)
    user = relationship("User", back_populates="audit_logs")
    
    # [NEW] Track which client made this request
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"), nullable=True, index=True)
    client = relationship("Client", back_populates="audit_logs")
    
    # [NEW] Additional context
    request_id: Mapped[str] = mapped_column(String(100), index=True, nullable=True)  # Correlation ID
    action: Mapped[str] = mapped_column(String(50), index=True)  # "enroll", "verify", "login_attempt"
    status: Mapped[str] = mapped_column(String(50))  # "success", "failure"
    source: Mapped[str] = mapped_column(String(50), nullable=True)  # "web_portal", "banking_app", "mobile"
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    
    details: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string with debug info
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', status='{self.status}', timestamp={self.timestamp})>"
```

### Step 2: Create Alembic Migration

**File: `backend/alembic/env.py`** (if not exists)

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.db.base import Base
from app.core.config import settings

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**File: `backend/alembic/versions/001_add_client_model.py`**

```python
"""Add Client model and client_id to User/AuditLog"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create Client table
    op.create_table(
        'client',
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('api_key', sa.String(length=256), nullable=False),
        sa.Column('secret', sa.String(length=256), nullable=False),
        sa.Column('scopes', sa.String(length=500), server_default='enroll,verify'),
        sa.Column('can_manage_users', sa.Boolean(), server_default=sa.false()),
        sa.Column('rate_limit_rpm', sa.Integer(), server_default='1000'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('client_id'),
        sa.UniqueConstraint('api_key', name='uq_client_api_key'),
    )
    op.create_index('ix_client_api_key', 'client', ['api_key'])
    op.create_index('ix_client_is_active', 'client', ['is_active'])
    op.create_index('ix_client_created_at', 'client', ['created_at'])
    
    # Add client_id to user table
    op.add_column('user', sa.Column('client_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_client_id', 'user', 'client', ['client_id'], ['client_id'])
    op.create_index('ix_user_client_id', 'user', ['client_id'])
    
    # Add client_id to audit_log table
    op.add_column('audit_log', sa.Column('client_id', sa.Integer(), nullable=True))
    op.add_column('audit_log', sa.Column('request_id', sa.String(100), nullable=True))
    op.add_column('audit_log', sa.Column('source', sa.String(50), nullable=True))
    op.add_column('audit_log', sa.Column('ip_address', sa.String(50), nullable=True))
    
    op.create_foreign_key('fk_audit_log_client_id', 'audit_log', 'client', ['client_id'], ['client_id'])
    op.create_index('ix_audit_log_client_id', 'audit_log', ['client_id'])
    op.create_index('ix_audit_log_request_id', 'audit_log', ['request_id'])

def downgrade():
    op.drop_index('ix_audit_log_request_id', 'audit_log')
    op.drop_index('ix_audit_log_client_id', 'audit_log')
    op.drop_constraint('fk_audit_log_client_id', 'audit_log', type_='foreignkey')
    op.drop_column('audit_log', 'ip_address')
    op.drop_column('audit_log', 'source')
    op.drop_column('audit_log', 'request_id')
    op.drop_column('audit_log', 'client_id')
    
    op.drop_index('ix_user_client_id', 'user')
    op.drop_constraint('fk_user_client_id', 'user', type_='foreignkey')
    op.drop_column('user', 'client_id')
    
    op.drop_index('ix_client_created_at', 'client')
    op.drop_index('ix_client_is_active', 'client')
    op.drop_index('ix_client_api_key', 'client')
    op.drop_table('client')
```

Run migration:
```bash
cd backend
alembic upgrade head
```

---

## PHASE 1: CORE APPLICATION CHANGES

### Step 3: Update Configuration

**File: `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Biometric Authentication Service"
    API_VERSION: str = "v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./biometric.db"
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Configuration
    API_KEY_HEADER: str = "X-API-Key"
    API_SECRET_HEADER: str = "X-API-Secret"
    
    # CORS - Now configurable
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    
    # Client Management
    ALLOW_DYNAMIC_CLIENT_REGISTRATION: bool = os.getenv("ALLOW_DYNAMIC_CLIENT_REGISTRATION", "false").lower() == "true"
    
    # Biometric Thresholds (these can be overridden per-client later)
    FACE_IDENTIFICATION_THRESHOLD: float = 0.67
    FACE_POSE_IDENTITY_THRESHOLD: float = 0.60
    VOICE_IDENTIFICATION_THRESHOLD: float = 0.70
    SPOOF_ENABLED: bool = False
    SPOOF_THRESHOLD: float = 0.5
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

**File: `backend/.env.example`**

```env
# Application
DEBUG=false

# Database
DATABASE_URL=sqlite+aiosqlite:///./biometric.db
# For PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:password@localhost/biometric

# Security
SECRET_KEY=your-very-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Origins (comma-separated or JSON array)
CORS_ALLOWED_ORIGINS=["http://localhost:5500","http://portal:5500"]

# Client Management
ALLOW_DYNAMIC_CLIENT_REGISTRATION=false

# Biometric Thresholds
FACE_IDENTIFICATION_THRESHOLD=0.67
FACE_POSE_IDENTITY_THRESHOLD=0.60
VOICE_IDENTIFICATION_THRESHOLD=0.70
```

### Step 4: Security Module Updates

**File: `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException
from app.core.config import settings

def create_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    client_id: Optional[int] = None,
) -> str:
    """Create JWT token with optional client binding."""
    to_encode = data.copy()
    
    # Add client context
    if client_id:
        to_encode["client_id"] = client_id
    
    # Set timestamps
    to_encode["iat"] = datetime.utcnow()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode["exp"] = expire
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_token_for_client(token: str, client_id: int) -> Dict[str, Any]:
    """Verify token and ensure it belongs to the client."""
    payload = verify_token(token)
    
    token_client_id = payload.get("client_id")
    if token_client_id and token_client_id != client_id:
        raise HTTPException(
            status_code=403,
            detail="Token client mismatch"
        )
    
    return payload
```

### Step 5: New Dependencies

**File: `backend/app/api/dependencies/client.py`** [NEW]

```python
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import Client
from app.core.config import settings
from typing import Optional

async def get_client_from_api_key(
    session: AsyncSession = Depends(get_session),
    api_key: str = Header(
        ...,
        alias=settings.API_KEY_HEADER,
        description="API key for client identification"
    ),
) -> Client:
    """
    Extract and validate client from API key header.
    
    Raises:
        HTTPException: If API key is invalid or client is inactive
    """
    result = await session.execute(
        select(Client).where(
            Client.api_key == api_key,
            Client.is_active == True
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return client

def require_client_scope(required_scope: str):
    """Factory for scope-based permission checking."""
    async def check_scope(client: Client = Depends(get_client_from_api_key)) -> Client:
        scopes = [s.strip() for s in client.scopes.split(",")]
        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Client missing required scope: {required_scope}"
            )
        return client
    return check_scope
```

### Step 6: Generic Response Schema

**File: `backend/app/domain/schemas.py`** [UPDATE]

```python
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, Any, List
from datetime import datetime

T = TypeVar("T")

# [NEW] Generic response wrapper
class ServiceResponse(BaseModel, Generic[T]):
    """Standard API response for all endpoints."""
    success: bool = Field(..., description="Operation success status")
    code: str = Field(..., description="Machine-readable status code")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(None, description="Response payload")
    debug: Optional[dict] = Field(None, description="Debug info (dev mode only)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# [NEW] Standardized error detail
class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str

# [KEEP EXISTING] Authentication Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# [KEEP EXISTING] Enrollment Schemas
class EnrollmentRequest(BaseModel):
    username: str
    face_samples: List[str] = Field(..., description="Base64-encoded face images")
    voice_samples: List[str] = Field(..., description="Base64-encoded voice samples")

# [NEW] Verification Schemas
class VerifyRequest(BaseModel):
    face_image_b64: Optional[str] = Field(None, description="Base64-encoded face image")
    voice_wav_b64: Optional[str] = Field(None, description="Base64-encoded voice WAV")

class VerifyResponse(BaseModel):
    decision: str = Field(..., description="ACCEPTED or REJECTED")
    confidence: float = Field(..., ge=0, le=1, description="Match confidence 0-1")
    matched_user_id: Optional[int] = Field(None, description="System user ID if matched")
    reason: str = Field(..., description="Why accepted/rejected")

# [NEW] Client Management
class ClientRegistrationRequest(BaseModel):
    name: str = Field(..., description="Client application name")
    scopes: List[str] = Field(
        default=["enroll", "verify"],
        description="Capabilities: enroll, verify, admin"
    )
    can_manage_users: bool = Field(
        False,
        description="Allow client to create/manage users"
    )

class ClientRegistrationResponse(BaseModel):
    client_id: int
    name: str
    api_key: str
    secret: str
    scopes: List[str]
```

### Step 7: Updated Main App

**File: `backend/app/main.py`** [MODIFIED]

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# [NEW] Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.API_VERSION}")
    logger.info(f"CORS allowed origins: {settings.CORS_ALLOWED_ORIGINS}")
    yield
    # Shutdown
    logger.info("Shutting down application")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="Multi-modal biometric authentication service",
    lifespan=lifespan,
)

# [MODIFIED] Dynamic CORS from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# [NEW] Security headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
)

# [NEW] Include v1 routes
from app.api.v1 import routes_auth, routes_verify, routes_enroll, routes_admin, routes_health

app.include_router(
    routes_auth.router,
    tags=["Authentication"]
)
app.include_router(
    routes_verify.router,
    tags=["Verification"]
)
app.include_router(
    routes_enroll.router,
    tags=["Enrollment"]
)
app.include_router(
    routes_admin.router,
    tags=["Administration"]
)
app.include_router(
    routes_health.router,
    tags=["Health"]
)

# [OPTIONAL] Keep v0 routes for backward compatibility (deprecated)
# app.include_router(
#     routes_v0.router,
#     prefix="/v0",
#     tags=["Legacy v0 - DEPRECATED"]
# )

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown event")

@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }
```

---

## PHASE 1: NEW v1 API ROUTES

### Step 8: Authentication Routes (v1)

**File: `backend/app/api/v1/__init__.py`** [NEW]

```python
"""v1 API endpoints"""
```

**File: `backend/app/api/v1/routes_auth.py`** [NEW]

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.db.session import get_session
from app.db.models import User, Client
from app.domain.schemas import (
    LoginRequest, TokenResponse, ServiceResponse, ClientRegistrationRequest
)
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.client import get_client_from_api_key
from app.core.security import create_token, verify_token
from app.core.config import settings
from app.services.authentication_service import AuthenticationService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/verify", response_model=ServiceResponse[dict])
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
    client: Client = Depends(get_client_from_api_key),
) -> ServiceResponse[dict]:
    """
    Authenticate user with username/password and receive JWT token.
    
    The returned token can be used for /verify endpoint.
    
    **Required Headers:**
    - X-API-Key: Client API key
    
    **Returns:**
    - JWT token valid for {ACCESS_TOKEN_EXPIRE_MINUTES} minutes
    """
    try:
        # Get user from database
        result = await session.execute(
            select(User).where(
                User.username == request.username,
                User.client_id == client.client_id  # [CLIENT-SCOPED QUERY]
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Login failed: user '{request.username}' not found for client {client.client_id}")
            return ServiceResponse(
                success=False,
                code="USER_NOT_FOUND",
                message="Invalid username or password"
            )
        
        # [TODO] Verify password hash
        # if not verify_password(request.password, user.password_hash):
        #     return ServiceResponse(...)
        
        # Generate JWT token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        token = create_token(
            data={"sub": str(user.user_id), "username": user.username},
            expires_delta=access_token_expires,
            client_id=client.client_id
        )
        
        logger.info(f"User '{user.username}' authenticated successfully via client {client.name}")
        
        return ServiceResponse(
            success=True,
            code="OK",
            message="Authentication successful",
            data={
                "token": token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
                "user_id": user.user_id,
            }
        )
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return ServiceResponse(
            success=False,
            code="SERVER_ERROR",
            message="Authentication service error"
        )

@router.get("/me", response_model=ServiceResponse[dict])
async def get_current_user_info(
    user: User = Depends(get_current_user),
) -> ServiceResponse[dict]:
    """Get current authenticated user info."""
    return ServiceResponse(
        success=True,
        code="OK",
        message="User retrieved",
        data={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
    )
```

### Step 9: Verification Routes (v1)

**File: `backend/app/api/v1/routes_verify.py`** [NEW]

```python
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User, Client
from app.domain.schemas import VerifyRequest, ServiceResponse, VerifyResponse
from app.api.dependencies.client import get_client_from_api_key, require_client_scope
from app.core.security import verify_token_for_client
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_array
from app.utils.audio_io import b64_to_wav_mono
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verify", tags=["verification"])

_auth_service = AuthenticationService()

@router.post("/", response_model=ServiceResponse[VerifyResponse])
async def verify(
    request: VerifyRequest,
    session: AsyncSession = Depends(get_session),
    client: Client = Depends(require_client_scope("verify")),
    authorization: str = Header(...),
) -> ServiceResponse[VerifyResponse]:
    """
    Verify user using face and/or voice biometrics.
    
    **Required Headers:**
    - X-API-Key: Client API key
    - Authorization: Bearer {{jwt_token}} (from /auth/verify)
    
    **Body:**
    - face_image_b64: Optional base64-encoded face image
    - voice_wav_b64: Optional base64-encoded voice WAV file
    
    **Returns:**
    - decision: ACCEPTED or REJECTED
    - confidence: 0-1 confidence score
    """
    try:
        # Parse authorization header
        scheme, credentials = authorization.split(maxsplit=1)
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme"
            )
        
        # Verify token and extract user
        payload = verify_token_for_client(credentials, client.client_id)
        user_id = int(payload.get("sub"))
        
        # Get user
        result = await session.execute(
            select(User).where(
                User.user_id == user_id,
                User.client_id == client.client_id
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return ServiceResponse(
                success=False,
                code="USER_NOT_FOUND",
                message="User not found",
                data=VerifyResponse(
                    decision="REJECTED",
                    confidence=0.0,
                    reason="User not found in system"
                )
            )
        
        # Convert inputs
        face_img = None
        if request.face_image_b64:
            try:
                face_img = b64_to_bgr_array(request.face_image_b64)
            except Exception as e:
                logger.error(f"Face image decode error: {e}")
                return ServiceResponse(
                    success=False,
                    code="INVALID_IMAGE",
                    message="Could not decode face image",
                    data=VerifyResponse(
                        decision="REJECTED",
                        confidence=0.0,
                        reason="Invalid face image format"
                    )
                )
        
        audio = None
        sr = None
        if request.voice_wav_b64:
            try:
                audio, sr = b64_to_wav_mono(request.voice_wav_b64)
            except Exception as e:
                logger.error(f"Voice decode error: {e}")
                return ServiceResponse(
                    success=False,
                    code="INVALID_AUDIO",
                    message="Could not decode voice",
                    data=VerifyResponse(
                        decision="REJECTED",
                        confidence=0.0,
                        reason="Invalid voice format"
                    )
                )
        
        # [EXISTING SERVICE - no changes needed]
        # Call authentication service for actual verification
        result = await _auth_service.verify_multimodal(
            session=session,
            user_id=user_id,
            face_img=face_img,
            audio=audio,
            sr=sr,
        )
        
        decision = result.get("decision", "REJECTED")
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "Verification failed")
        
        return ServiceResponse(
            success=decision == "ACCEPTED",
            code="OK" if decision == "ACCEPTED" else "VERIFICATION_FAILED",
            message="User verified" if decision == "ACCEPTED" else "Verification failed",
            data=VerifyResponse(
                decision=decision,
                confidence=confidence,
                matched_user_id=user_id if decision == "ACCEPTED" else None,
                reason=reason
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Verification error: {e}")
        return ServiceResponse(
            success=False,
            code="SERVER_ERROR",
            message="Verification service error",
            data=VerifyResponse(
                decision="REJECTED",
                confidence=0.0,
                reason="System error"
            )
        )
```

### Step 10: Admin Routes (v1)

**File: `backend/app/api/v1/routes_admin.py`** [NEW]

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User, Client
from app.domain.schemas import (
    ServiceResponse, ClientRegistrationRequest, ClientRegistrationResponse
)
from app.api.dependencies.auth import get_current_admin_user
from app.core.config import settings
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["administration"])

@router.post("/clients", response_model=ServiceResponse[ClientRegistrationResponse])
async def register_client(
    request: ClientRegistrationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
) -> ServiceResponse[ClientRegistrationResponse]:
    """
    Register a new client application.
    
    **Requires:**
    - Admin role
    - JWT token via Authorization header
    
    **Returns:**
    - api_key: Use this in X-API-Key header
    - secret: Reserved for future use (HMAC signing)
    """
    try:
        # Generate secure credentials
        api_key = secrets.token_urlsafe(32)
        secret = secrets.token_urlsafe(32)
        
        # Create client
        new_client = Client(
            name=request.name,
            api_key=api_key,
            secret=secret,
            scopes=",".join(request.scopes or ["enroll", "verify"]),
            can_manage_users=request.can_manage_users or False,
            is_active=True,
        )
        
        session.add(new_client)
        await session.commit()
        await session.refresh(new_client)
        
        logger.info(f"New client registered: {new_client.name} (id={new_client.client_id})")
        
        return ServiceResponse(
            success=True,
            code="OK",
            message="Client registered successfully",
            data=ClientRegistrationResponse(
                client_id=new_client.client_id,
                name=new_client.name,
                api_key=api_key,
                secret=secret,
                scopes=new_client.scopes.split(","),
            )
        )
    
    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register client"
        )

@router.get("/clients", response_model=ServiceResponse[list])
async def list_clients(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
) -> ServiceResponse[list]:
    """List all registered clients (admin only)."""
    result = await session.execute(select(Client))
    clients = result.scalars().all()
    
    return ServiceResponse(
        success=True,
        code="OK",
        message=f"Found {len(clients)} clients",
        data=[
            {
                "client_id": c.client_id,
                "name": c.name,
                "is_active": c.is_active,
                "scopes": c.scopes.split(","),
                "created_at": c.created_at.isoformat(),
            }
            for c in clients
        ]
    )
```

### Step 11: Health Check Route

**File: `backend/app/api/v1/routes_health.py`** [NEW]

```python
from fastapi import APIRouter
from app.core.config import settings
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION,
        "service": settings.APP_NAME,
    }

@router.get("/ready")
async def readiness_check():
    """Service readiness check (includes DB connection test)."""
    # [TODO] Add database connectivity test
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

---

## PHASE 2: FRONTEND REFACTORING

### Step 12: Frontend API Client

**File: `frontend/shared/api-client.js`** [NEW]

```javascript
/**
 * Generic HTTP client for biometric authentication service
 * Encapsulates all API communication logic
 */

export class BiometricServiceClient {
    constructor(config) {
        this.baseURL = config.API_BASE || "http://localhost:8000";
        this.apiKey = config.API_KEY || "";
        this.apiSecret = config.API_SECRET || "";
        this.version = config.VERSION || "v1";
        this.token = null;
        this.tokenExpiry = null;
        this.debug = config.DEBUG || false;
    }

    // ============ Authentication ============
    
    async authenticate(username, password) {
        const response = await this.request("POST", "/auth/verify", {
            username,
            password,
        });

        if (response.success) {
            this.token = response.data.token;
            // Store expiry time
            const expiresIn = response.data.expires_in || 1800;
            this.tokenExpiry = Date.now() + (expiresIn * 1000);
            
            if (this.debug) console.log("Token set, expires in", expiresIn, "seconds");
            return response.data;
        } else {
            throw new Error(response.message || "Authentication failed");
        }
    }

    async getCurrentUser() {
        return this.request("GET", "/auth/me");
    }

    isTokenExpired() {
        if (!this.tokenExpiry) return true;
        return Date.now() >= this.tokenExpiry;
    }

    // ============ Verification ============
    
    async verify(faceB64, voiceB64) {
        if (this.isTokenExpired()) {
            throw new Error("Token expired. Please login again.");
        }

        return this.request("POST", "/verify/", {
            face_image_b64: faceB64,
            voice_wav_b64: voiceB64,
        });
    }

    // ============ Enrollment ============
    
    async enrollUser(username, faceSamples, voiceSamples) {
        return this.request("POST", "/enroll/biometric", {
            username,
            face_samples: faceSamples,
            voice_samples: voiceSamples,
        });
    }

    async preCheckFace(faceB64) {
        return this.request("POST", "/enroll/precheck/face", {
            face_image_b64: faceB64,
        });
    }

    async preCheckVoice(voiceB64) {
        return this.request("POST", "/enroll/precheck/voice", {
            voice_wav_b64: voiceB64,
        });
    }

    // ============ HTTP Layer ============
    
    async request(method, endpoint, body = null, customHeaders = {}) {
        const url = `${this.baseURL}/${this.version}${endpoint}`;

        const headers = {
            "X-API-Key": this.apiKey,
            "Content-Type": "application/json",
            ...customHeaders,
        };

        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }

        if (this.debug) {
            console.log(`[${method}] ${url}`, body);
        }

        try {
            const response = await fetch(url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : null,
            });

            if (!response.ok) {
                const errorBody = await response.json().catch(() => ({}));
                throw new Error(
                    errorBody.message || `HTTP ${response.status}`
                );
            }

            const data = await response.json();

            if (this.debug) {
                console.log(`Response:`, data);
            }

            return data;
        } catch (err) {
            console.error(`Request failed: ${method} ${endpoint}`, err);
            throw {
                code: "REQUEST_FAILED",
                message: err.message,
                endpoint,
            };
        }
    }

    clearToken() {
        this.token = null;
        this.tokenExpiry = null;
    }
}
```

### Step 13: Portal Configuration

**File: `frontend/portal/config.js`** [NEW]

```javascript
/**
 * Portal-specific configuration
 * Environment variables take precedence
 */

export const PORTAL_CONFIG = {
    // Application identity
    APP_NAME: "Biometric Portal",
    APP_VERSION: "2.0.0",

    // Service connection
    API_BASE: process.env.REACT_APP_API_BASE || "http://localhost:8000",
    API_VERSION: "v1",

    // Client credentials (set via .env)
    API_KEY: process.env.REACT_APP_API_KEY || "",
    API_SECRET: process.env.REACT_APP_API_SECRET || "",

    // UI configuration
    UI_THEME: process.env.REACT_APP_THEME || "light",
    DEBUG: process.env.REACT_APP_DEBUG === "true",

    // Biometric capture settings
    FACE_CAPTURE_TIMEOUT_MS: 30000,
    VOICE_CAPTURE_TIMEOUT_MS: 5000,
    VOICE_CHALLENGE_LOCALE: "tr", // Turkish by default

    // Feature flags
    ALLOW_VOICE_CAPTURE: true,
    ALLOW_FACE_CAPTURE: true,
    REQUIRE_LIVENESS_CHECK: true,
};

// Validate required config
if (!PORTAL_CONFIG.API_KEY) {
    console.warn("API_KEY not configured. Set REACT_APP_API_KEY environment variable.");
}
```

**File: `frontend/portal/.env.example`**

```
# API Configuration
REACT_APP_API_BASE=http://localhost:8000
REACT_APP_API_KEY=your-portal-api-key
REACT_APP_API_SECRET=

# UI
REACT_APP_THEME=light
REACT_APP_DEBUG=false
```

### Step 14: Portal Main Entry

**File: `frontend/portal/js/app.js`** [NEW]

```javascript
import { BiometricServiceClient } from "../../shared/api-client.js";
import { PORTAL_CONFIG } from "../config.js";

// Create single client instance for entire application
export const biometricClient = new BiometricServiceClient({
    API_BASE: PORTAL_CONFIG.API_BASE,
    API_KEY: PORTAL_CONFIG.API_KEY,
    VERSION: PORTAL_CONFIG.API_VERSION,
    DEBUG: PORTAL_CONFIG.DEBUG,
});

// Application initialization
document.addEventListener("DOMContentLoaded", async () => {
    console.log("============================================");
    console.log(`${PORTAL_CONFIG.APP_NAME} v${PORTAL_CONFIG.APP_VERSION}`);
    console.log("============================================");
    console.log("Service:", PORTAL_CONFIG.API_BASE);
    console.log("Debug Mode:", PORTAL_CONFIG.DEBUG);

    // Initialize UI modules
    initializeApp();
});

function initializeApp() {
    // Setup navigation
    setupNavigation();
    
    // Setup authentication
    setupAuthentication();
    
    console.log("✓ App initialized");
}

function setupAuthentication() {
    // Check if already authenticated
    const token = localStorage.getItem("auth_token");
    if (token) {
        biometricClient.token = token;
        console.log("✓ Token restored from localStorage");
    }
}

function setupNavigation() {
    // Setup routing logic
    console.log("✓ Navigation initialized");
}
```

### Step 15: Portal Auth Module (Updated)

**File: `frontend/portal/js/auth.js`** [MODIFIED]

```javascript
import { biometricClient } from "./app.js";

export async function loginUser(username, password) {
    try {
        const result = await biometricClient.authenticate(username, password);
        
        // Store token
        localStorage.setItem("auth_token", result.token);
        localStorage.setItem("user_id", result.user_id);
        
        console.log("✓ Login successful");
        return result;
    } catch (err) {
        console.error("✗ Login failed:", err.message);
        throw err;
    }
}

export function logoutUser() {
    // Clear local storage
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_id");
    
    // Clear client token
    biometricClient.clearToken();
    
    console.log("✓ Logout successful");
}

export function isAuthenticated() {
    return !!localStorage.getItem("auth_token");
}

export function getCurrentUserId() {
    return localStorage.getItem("user_id");
}
```

### Step 16: Portal Verify Module (Updated)

**File: `frontend/portal/js/verify.js`** [MODIFIED]

```javascript
import { biometricClient } from "./app.js";

export async function verifyUser(faceBase64, voiceBase64) {
    try {
        const result = await biometricClient.verify(faceBase64, voiceBase64);
        
        return {
            success: result.success,
            decision: result.data?.decision,
            confidence: result.data?.confidence,
            message: result.message,
        };
    } catch (err) {
        console.error("✗ Verification failed:", err);
        throw err;
    }
}

export async function performLivenessCheck(faceBase64) {
    // [TODO] Call liveness-specific endpoint when ready
    return verifyUser(faceBase64, null);
}
```

---

## SUMMARY OF REQUIRED FILES TO CREATE

```
backend/
├── app/core/security.py                   # [MODIFY] Add client token logic
├── app/core/config.py                     # [MODIFY] Add config variables
├── app/db/models.py                       # [MODIFY] Add Client model
├── app/main.py                            # [MODIFY] Update CORS, add v1 routes
├── app/api/dependencies/client.py         # [NEW]
├── app/api/v1/__init__.py                # [NEW]
├── app/api/v1/routes_auth.py             # [NEW]
├── app/api/v1/routes_verify.py           # [NEW]
├── app/api/v1/routes_admin.py            # [NEW]
├── app/api/v1/routes_health.py           # [NEW]
├── app/domain/schemas.py                  # [MODIFY] Add ServiceResponse
├── alembic/versions/001_add_client_model.py  # [NEW]
└── .env.example                           # [NEW]

frontend/
├── shared/api-client.js                   # [NEW]
├── portal/config.js                       # [NEW]
├── portal/js/app.js                       # [NEW]
├── portal/js/auth.js                      # [MODIFY]
├── portal/js/verify.js                    # [MODIFY]
├── portal/.env.example                    # [NEW]
```

