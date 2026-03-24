from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


class VerifyRequest(BaseModel):
    face_image_b64: Optional[str] = None
    voice_wav_b64: Optional[str] = None

    @field_validator("face_image_b64", "voice_wav_b64", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @model_validator(mode="after")
    def at_least_one_modality(self):
        if not self.face_image_b64 and not self.voice_wav_b64:
            raise ValueError("At least one of face_image_b64 or voice_wav_b64 must be provided.")
        return self


class VerifyResponse(BaseModel):
    decision: str
    reason: str
    identified_user: Optional[str] = None
    fusion_score: float
    face_score: float
    voice_score: float


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

    @field_validator("username", "password", "role", mode="before")
    @classmethod
    def strip_string_fields(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.username:
            raise ValueError("Username is required.")
        if not self.password:
            raise ValueError("Password is required.")
        if self.role not in {"admin", "user"}:
            raise ValueError("Role must be either 'admin' or 'user'.")
        return self


class CreateUserResponse(BaseModel):
    message: str
    user_id: int
    username: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username", "password", mode="before")
    @classmethod
    def strip_login_fields(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_login_fields(self):
        if not self.username:
            raise ValueError("Username is required.")
        if not self.password:
            raise ValueError("Password is required.")
        return self


class LoginResponse(BaseModel):
    message: str
    username: str
    role: str
    access_token: str
    token_type: str = "bearer"


class BiometricFaceSample(BaseModel):
    image_b64: str
    angle: Literal["center", "left", "right"]


class BiometricVoiceSample(BaseModel):
    voice_wav_b64: str
    prompt_text: str
    transcript_text: Optional[str] = None


class BiometricEnrollRequest(BaseModel):
    username: str
    role: str
    face_samples: list[BiometricFaceSample]
    voice_samples: list[BiometricVoiceSample]

    @field_validator("username", "role", mode="before")
    @classmethod
    def strip_enroll_fields(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_enroll_fields(self):
        if not self.username:
            raise ValueError("Username is required.")
        if not self.role:
            raise ValueError("Role is required.")
        if not self.face_samples:
            raise ValueError("At least one face sample is required.")
        if not self.voice_samples:
            raise ValueError("At least one voice sample is required.")
        return self


class BiometricEnrollResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    face_status: Optional[str] = None
    voice_status: Optional[str] = None

# Ses biyometrik kimlik doğrulama için request ve response modelleri

class VoiceIdentifyRequest(BaseModel):
    voice_b64: str
    expected_user_id: int

class VoiceIdentifyResponse(BaseModel):
    user_id: Optional[int] = None
    score: float
    passed: bool
    threshold: float
    reason: str


# ==== Precheck (Duplicate) Modelleri ====
from typing import Optional
from pydantic import BaseModel

class FacePrecheckRequest(BaseModel):
    username: str
    face_image_b64: str

class FacePrecheckResponse(BaseModel):
    duplicate: bool
    reason: str
    matched_username: Optional[str] = None
    matched_user_id: Optional[int] = None
    similarity: float = 0.0

class VoicePrecheckRequest(BaseModel):
    username: str
    voice_wav_b64: str

class VoicePrecheckResponse(BaseModel):
    duplicate: bool
    reason: str
    matched_username: Optional[str] = None
    matched_user_id: Optional[int] = None
    similarity: float = 0.0