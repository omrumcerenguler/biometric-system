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

@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, session: AsyncSession = Depends(get_session)):
    svc = AuthenticationService()

    # 1) Decode only if provided
    face_img = None
    if req.face_image_b64:
        try:
            face_img = b64_to_bgr_image(req.face_image_b64)
        except ValueError as e:
            _bad_request(str(e))

    audio = None
    sr = None
    if req.voice_wav_b64:
        try:
            audio, sr = b64_to_wav_mono(req.voice_wav_b64)
        except ValueError as e:
            _bad_request(str(e))

    # 2) Run verification with available modalities
    result = await svc.verify(username=req.username, face_img=face_img, audio=audio, sr=sr)

    return VerifyResponse(**result)
