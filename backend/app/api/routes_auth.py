from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.schemas import VerifyRequest, VerifyResponse
from app.services.authentication_service import AuthenticationService
from app.utils.audio_io import b64_to_wav_mono
from app.utils.image_io import b64_to_bgr_image

import numpy as np


router = APIRouter(prefix="/auth", tags=["auth"])


# ✅ Singleton service (state machine continuity)
_auth_service = AuthenticationService()


# =========================
# REQUEST MODELS
# =========================

class LivenessStartIn(BaseModel):
    username: str


class LivenessUpdateIn(BaseModel):
    username: str
    face_b64: str  # base64 JPEG/PNG (data-url olabilir)


# =========================
# HELPERS
# =========================

def _bad_request(msg: str):
    raise HTTPException(status_code=400, detail=msg)


# =========================
# LIVENESS ENDPOINTS
# =========================

@router.post("/liveness/start")
async def liveness_start(payload: LivenessStartIn):
    res = _auth_service.start_face_liveness(payload.username)

    return {
        "status": "IN_PROGRESS",
        "step": res["step"],
        "instruction": res["instruction"],
    }


@router.post("/liveness/update")
async def liveness_update(payload: LivenessUpdateIn):
    try:
        img = b64_to_bgr_image(payload.face_b64)
    except ValueError as e:
        _bad_request(f"INVALID_FACE_IMAGE: {e}")

    result = _auth_service.update_face_liveness(payload.username, img)
    return result


# =========================
# FINAL VERIFY
# =========================

@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, session: AsyncSession = Depends(get_session)):

    face_img = None
    if req.face_image_b64:
        try:
            face_img = b64_to_bgr_image(req.face_image_b64)
        except ValueError as e:
            _bad_request(f"INVALID_FACE_IMAGE: {e}")

    audio = None
    sr = None
    if req.voice_wav_b64:
        try:
            audio, sr = b64_to_wav_mono(req.voice_wav_b64)
        except ValueError as e:
            _bad_request(
                "INVALID_VOICE_AUDIO: expected WAV base64. "
                "Browser MediaRecorder often produces WEBM; "
                "either upload WAV or update backend to decode WEBM. "
                f"Details: {e}"
            )

    if face_img is None and audio is None:
        _bad_request("NO_INPUT: provide face_image_b64 and/or voice_wav_b64")

    result = await _auth_service.verify(
        username=req.username,
        face_img=face_img,
        audio=audio,
        sr=sr,
    )

    return VerifyResponse(**result)
