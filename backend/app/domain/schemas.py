from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class VerifyRequest(BaseModel):
    username: str
    face_image_b64: Optional[str] = None
    voice_wav_b64: Optional[str] = None

    # boş string -> None (kalıcı temizlik)
    @field_validator("face_image_b64", "voice_wav_b64", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    # en az bir modalite zorunlu
    @model_validator(mode="after")
    def at_least_one_modality(self):
        if not self.face_image_b64 and not self.voice_wav_b64:
            raise ValueError("At least one of face_image_b64 or voice_wav_b64 must be provided.")
        return self


class VerifyResponse(BaseModel):
    decision: str
    fusion_score: float
    face_score: float
    voice_score: float
    reason: str

    # ✅ optional extras (for face liveness flow)
    face_liveness_step: Optional[str] = None
    face_liveness_instruction: Optional[str] = None
    face_liveness_passed: Optional[bool] = None