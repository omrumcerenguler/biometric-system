from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image
from app.utils.audio_io import b64_to_wav_mono
from app.domain.schemas import BiometricEnrollRequest, BiometricEnrollResponse

router = APIRouter(prefix="/enroll", tags=["enroll"])
_auth_service = AuthenticationService()


async def _require_existing_user(session: AsyncSession, username: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    return user


@router.post("/biometric", response_model=BiometricEnrollResponse)
async def enroll_biometric(
    req: BiometricEnrollRequest,
    session: AsyncSession = Depends(get_session),
):
    username = (req.username or "").strip()
    role = (req.role or "").strip()
    face_frames = req.face_frames_b64 or []
    voice_samples = req.voice_samples or []

    if not username:
        return BiometricEnrollResponse(success=False, message="USERNAME_EMPTY")
    if not role:
        return BiometricEnrollResponse(success=False, message="ROLE_EMPTY")
    if not face_frames:
        return BiometricEnrollResponse(success=False, message="FACE_FRAMES_EMPTY")
    if not voice_samples:
        return BiometricEnrollResponse(success=False, message="VOICE_SAMPLES_EMPTY")

    await _require_existing_user(session, username)

    face_status = "not_processed"
    voice_status = "not_processed"

    try:
        face_embeddings = []
        for b64_img in face_frames:
            img = b64_to_bgr_image(b64_img)
            emb = _auth_service.face.extract_embedding(img)
            if emb is None:
                return BiometricEnrollResponse(
                    success=False,
                    message="FACE_EMBEDDING_FAILED",
                    user_id=None,
                    face_status="failed",
                    voice_status="not_processed",
                )
            face_embeddings.append(emb)

        face_status = f"processed_{len(face_embeddings)}"
    except Exception as e:
        return BiometricEnrollResponse(
            success=False,
            message=f"FACE_PROCESSING_ERROR: {e}",
            user_id=None,
            face_status="failed",
            voice_status="not_processed",
        )

    try:
        voice_embeddings = []
        for sample in voice_samples:
            wav_b64 = sample.get("voice_wav_b64")
            if not wav_b64:
                continue

            audio, sr = b64_to_wav_mono(wav_b64)
            emb = _auth_service.voice.extract_embedding(audio, sr)
            if emb is None:
                return BiometricEnrollResponse(
                    success=False,
                    message="VOICE_EMBEDDING_FAILED",
                    user_id=None,
                    face_status=face_status,
                    voice_status="failed",
                )
            voice_embeddings.append(emb)

        if not voice_embeddings:
            return BiometricEnrollResponse(
                success=False,
                message="VOICE_SAMPLES_INVALID",
                user_id=None,
                face_status=face_status,
                voice_status="failed",
            )

        voice_status = f"processed_{len(voice_embeddings)}"
    except Exception as e:
        return BiometricEnrollResponse(
            success=False,
            message=f"VOICE_PROCESSING_ERROR: {e}",
            user_id=None,
            face_status=face_status,
            voice_status="failed",
        )

    return BiometricEnrollResponse(
        success=True,
        message="Biometric enrollment completed",
        user_id=None,
        face_status=face_status,
        voice_status=voice_status,
    )