from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.schemas import VerifyRequest, VerifyResponse
from app.services.authentication_service import AuthenticationService
from app.utils.audio_io import b64_to_wav_mono
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/auth", tags=["auth"])


def _bad_request(msg: str):
    raise HTTPException(status_code=400, detail=msg)


# ✅ singleton (her request'te yeniden yaratma)
_auth_service = AuthenticationService()


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, session: AsyncSession = Depends(get_session)):

    # 1) Decode only if provided
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
            _bad_request(f"INVALID_VOICE_AUDIO: {e}")

    # 2) Require at least one modality
    if face_img is None and audio is None:
        _bad_request("NO_INPUT: provide face_image_b64 and/or voice_wav_b64")

    # 3) Run verification (✅ username yok, 1:N identification var)
    result = await _auth_service.verify(
        session=session,
        face_img=face_img,
        audio=audio,
        sr=sr,
    )
     # ✅ Pydantic ValidationError fix: reason her zaman gelsin
    if "reason" not in result or result["reason"] is None:
        # decision varsa ona göre default üret
        decision = result.get("decision", "UNKNOWN")
        result["reason"] = "OK" if decision == "ACCEPTED" else "DENIED"


    return VerifyResponse(**result)
