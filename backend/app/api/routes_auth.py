from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.schemas import VerifyRequest, VerifyResponse
from app.services.authentication_service import AuthenticationService
from app.utils.audio_io import b64_to_wav_mono
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/auth", tags=["auth"])

# ✅ singleton (her request'te yeniden yaratma)
_auth_service = AuthenticationService()


def _bad_request(msg: str) -> None:
    raise HTTPException(status_code=400, detail=msg)


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, session: AsyncSession = Depends(get_session)) -> VerifyResponse:
    """
    Product logic:
    - face_image_b64 REQUIRED
    - voice_wav_b64 REQUIRED
    - backend does 1:N face identify first, then voice matches that user
    """

    # 1) Require inputs (product requirement)
    if not req.face_image_b64:
        _bad_request("FACE_REQUIRED")
    if not req.voice_wav_b64:
        _bad_request("VOICE_REQUIRED")

    # 2) Decode face
    try:
        face_img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        _bad_request(f"INVALID_FACE_IMAGE: {e}")

    # 3) Decode voice
    try:
        audio, sr = b64_to_wav_mono(req.voice_wav_b64)
    except ValueError as e:
        _bad_request(f"INVALID_VOICE_AUDIO: {e}")

    # 4) Run verification (1:N face identify + voice identity match)
    result = await _auth_service.verify(
        session=session,
        face_img=face_img,
        audio=audio,
        sr=sr,
    )

    # 5) Safety: make sure required keys exist (avoid Pydantic errors)
    # (Service zaten reason döndürüyor ama "garanti" koyalım)
    result.setdefault("decision", "DENIED")
    result.setdefault("reason", "UNKNOWN")
    result.setdefault("identified_user", None)
    result.setdefault("fusion_score", 0.0)
    result.setdefault("face_score", 0.0)
    result.setdefault("voice_score", 0.0)

    return VerifyResponse(**result)