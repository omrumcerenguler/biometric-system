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


# ✅ IMPORTANT: singleton service (state machine / sessions should persist)
_auth_service = AuthenticationService()


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, session: AsyncSession = Depends(get_session)):
    # We keep session ready for future DB use,
    # but the service instance is singleton for liveness state continuity.

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
            # NOTE: frontend MediaRecorder usually sends WEBM/OGG, not WAV.
            # This function expects WAV base64.
            audio, sr = b64_to_wav_mono(req.voice_wav_b64)
        except ValueError as e:
            _bad_request(
                "INVALID_VOICE_AUDIO: expected WAV base64. "
                "Browser MediaRecorder often produces WEBM; "
                "either upload WAV or update backend to decode WEBM. "
                f"Details: {e}"
            )

    # 2) Require at least one modality
    if face_img is None and audio is None:
        _bad_request("NO_INPUT: provide face_image_b64 and/or voice_wav_b64")

    # 3) Run verification with available modalities
    result = await _auth_service.verify(
        username=req.username,
        face_img=face_img,
        audio=audio,
        sr=sr,
    )

    return VerifyResponse(**result)
