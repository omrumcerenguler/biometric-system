from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_session
from app.api.dependencies.auth import get_current_user
from app.domain.schemas import (
    VerifyRequest,
    VerifyResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.authentication_service import AuthenticationService
from app.utils.audio_io import b64_to_wav_mono
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/auth", tags=["auth"])

_auth_service = AuthenticationService()


def _bad_request(msg: str) -> None:
    raise HTTPException(status_code=400, detail=msg)


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),
    x_client: str = Header(default="portal", alias="X-Client"),
) -> LoginResponse:
    result = await _auth_service.login_user(
        session=session,
        username=req.username,
        password=req.password,
        client=x_client,
    )

    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("message", "LOGIN_FAILED"))

    access_token = create_access_token(
        {
            "sub": result["username"],
            "role": result["role"],
            "client": x_client,
        }
    )

    return LoginResponse(
        message=result["message"],
        username=result["username"],
        role=result["role"],
        access_token=access_token,
        token_type="bearer",
    )


@router.get("/me/biometric-status")
async def get_my_biometric_status(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    face_template = await _auth_service._get_user_face_template(
        session=session,
        user_id=current_user.user_id,
    )

    voice_template = await _auth_service._get_user_voice_template(
        session=session,
        user_id=current_user.user_id,
    )

    return {
        "face_enrolled": face_template is not None,
        "voice_enrolled": voice_template is not None,
    }

@router.post("/verify", response_model=VerifyResponse)
async def verify(
    req: VerifyRequest,
    session: AsyncSession = Depends(get_session),
    x_client: str = Header(default="portal", alias="X-Client"),
) -> VerifyResponse:
    """
    Product logic:
    - face_image_b64 REQUIRED
    - voice_wav_b64 REQUIRED
    - backend does 1:N face identify first, then voice matches that user
    """

    if not req.face_image_b64:
        _bad_request("FACE_REQUIRED")
    if not req.voice_wav_b64:
        _bad_request("VOICE_REQUIRED")

    try:
        face_img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        _bad_request(f"INVALID_FACE_IMAGE: {e}")

    try:
        audio, sr = b64_to_wav_mono(req.voice_wav_b64)
    except ValueError as e:
        _bad_request(f"INVALID_VOICE_AUDIO: {e}")

    result = await _auth_service.verify(
        session=session,
        face_img=face_img,
        audio=audio,
        sr=sr,
        client=x_client,
    )

    result.setdefault("decision", "DENIED")
    result.setdefault("reason", "UNKNOWN")
    result.setdefault("identified_user", None)
    result.setdefault("fusion_score", 0.0)
    result.setdefault("face_score", 0.0)
    result.setdefault("voice_score", 0.0)
    result.setdefault("spoof_score", None)
    result.setdefault("spoof_decision", None)

    return VerifyResponse(**result)