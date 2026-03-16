from __future__ import annotations

from typing import Optional
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
        return None if v is None else v

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


class BiometricVoiceSample(BaseModel):
    voice_wav_b64: str
    transcript_text: Optional[str] = None


class BiometricEnrollRequest(BaseModel):
    username: str
    role: str
    face_frames_b64: list[str]
    voice_samples: list[BiometricVoiceSample]


class BiometricEnrollResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    face_status: Optional[str] = None
    voice_status: Optional[str] = None