from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

import numpy as np
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

REQUIRED_FACE_ANGLES = ("center", "left", "right")
REQUIRED_FACE_SAMPLES_PER_ANGLE = 5
REQUIRED_TOTAL_VOICE_SAMPLES = 5


async def _require_existing_user(session: AsyncSession, username: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    return user


def _normalize_vector(vec: np.ndarray) -> np.ndarray:
    return vec / (np.linalg.norm(vec) + 1e-9)


@router.post("/biometric", response_model=BiometricEnrollResponse)
async def enroll_biometric(
    req: BiometricEnrollRequest,
    session: AsyncSession = Depends(get_session),
):
    username = (req.username or "").strip()
    role = (req.role or "").strip()
    face_samples = req.face_samples or []
    voice_samples = req.voice_samples or []

    if not username:
        return BiometricEnrollResponse(success=False, message="USERNAME_EMPTY")

    if not role:
        return BiometricEnrollResponse(success=False, message="ROLE_EMPTY")

    if not face_samples:
        return BiometricEnrollResponse(success=False, message="FACE_SAMPLES_EMPTY")

    if not voice_samples:
        return BiometricEnrollResponse(success=False, message="VOICE_SAMPLES_EMPTY")

    await _require_existing_user(session, username)

    face_status = "not_processed"
    voice_status = "not_processed"

    # -------------------------------------------------
    # FACE PROCESSING (pose-aware, angle grouped)
    # -------------------------------------------------
    try:
        angle_embeddings: Dict[str, List[np.ndarray]] = defaultdict(list)

        for sample in face_samples:
            image_b64 = sample.image_b64
            angle = sample.angle

            if angle not in REQUIRED_FACE_ANGLES:
                return BiometricEnrollResponse(
                    success=False,
                    message=f"INVALID_FACE_ANGLE:{angle}",
                    user_id=None,
                    face_status="failed",
                    voice_status="not_processed",
                )

            img = b64_to_bgr_image(image_b64)

            # Önce pose-aware extraction varsa onu kullan
            if hasattr(_auth_service, "extract_face_embedding_and_pose"):
                emb, nose_x_ratio, yaw, bbox_size, blur_score = _auth_service.extract_face_embedding_and_pose(img)
                detected_pose = _auth_service.bucket_pose_from_nose_ratio(nose_x_ratio)
                if emb is None:
                    return BiometricEnrollResponse(
                        success=False,
                        message="FACE_EMBEDDING_FAILED",
                        user_id=None,
                        face_status="failed",
                        voice_status="not_processed",
                    )

                # Eğer backend pose label da döndürüyorsa kontrol et
                if detected_pose and detected_pose != angle:
                    return BiometricEnrollResponse(
                        success=False,
                        message=f"FACE_POSE_MISMATCH:expected={angle},detected={detected_pose}",
                        user_id=None,
                        face_status="failed",
                        voice_status="not_processed",
                    )
            else:
                emb = _auth_service.face.extract_embedding(img)
                if emb is None:
                    return BiometricEnrollResponse(
                        success=False,
                        message="FACE_EMBEDDING_FAILED",
                        user_id=None,
                        face_status="failed",
                        voice_status="not_processed",
                    )

            angle_embeddings[angle].append(emb)

        for angle in REQUIRED_FACE_ANGLES:
            if len(angle_embeddings[angle]) < REQUIRED_FACE_SAMPLES_PER_ANGLE:
                return BiometricEnrollResponse(
                    success=False,
                    message=f"INSUFFICIENT_FACE_SAMPLES_{angle.upper()}",
                    user_id=None,
                    face_status="failed",
                    voice_status="not_processed",
                )

        pose_templates: Dict[str, np.ndarray] = {}
        for angle in REQUIRED_FACE_ANGLES:
            stacked = np.stack(angle_embeddings[angle], axis=0)
            pose_templates[angle] = _normalize_vector(np.mean(stacked, axis=0))

        face_status = (
            f"processed_center_{len(angle_embeddings['center'])}_"
            f"left_{len(angle_embeddings['left'])}_"
            f"right_{len(angle_embeddings['right'])}"
        )

    except Exception as e:
        return BiometricEnrollResponse(
            success=False,
            message=f"FACE_PROCESSING_ERROR:{e}",
            user_id=None,
            face_status="failed",
            voice_status="not_processed",
        )

    # -------------------------------------------------
    # VOICE PROCESSING
    # -------------------------------------------------
    try:
        if len(voice_samples) < REQUIRED_TOTAL_VOICE_SAMPLES:
            return BiometricEnrollResponse(
                success=False,
                message="VOICE_SAMPLES_INSUFFICIENT",
                user_id=None,
                face_status=face_status,
                voice_status="failed",
            )

        voice_embeddings: List[np.ndarray] = []

        for sample in voice_samples:
            wav_b64 = sample.voice_wav_b64
            prompt_text = (sample.prompt_text or "").strip()
            transcript_text = (sample.transcript_text or "").strip()

            if not wav_b64:
                continue

            if not prompt_text:
                return BiometricEnrollResponse(
                    success=False,
                    message="VOICE_PROMPT_TEXT_EMPTY",
                    user_id=None,
                    face_status=face_status,
                    voice_status="failed",
                )

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

            # transcript_text burada sadece bilgi amaçlı tutuluyor;
            # frontend approx doğrulama yapıyor.
            _ = transcript_text

            voice_embeddings.append(emb)

        if len(voice_embeddings) < REQUIRED_TOTAL_VOICE_SAMPLES:
            return BiometricEnrollResponse(
                success=False,
                message="VOICE_SAMPLES_INVALID",
                user_id=None,
                face_status=face_status,
                voice_status="failed",
            )

        merged_voice_template = _normalize_vector(
            np.mean(np.stack(voice_embeddings, axis=0), axis=0)
        )

        voice_status = f"processed_{len(voice_embeddings)}"

    except Exception as e:
        return BiometricEnrollResponse(
            success=False,
            message=f"VOICE_PROCESSING_ERROR:{e}",
            user_id=None,
            face_status=face_status,
            voice_status="failed",
        )

    # -------------------------------------------------
    # FINAL SAVE / COMMIT
    # -------------------------------------------------
    try:
        # Eğer service içinde pose-aware save fonksiyonu varsa onu kullan
        if hasattr(_auth_service, "enroll_user_with_pose_templates") and hasattr(
            _auth_service, "save_voice_template_vector"
        ):
            face_result = await _auth_service.enroll_user_with_pose_templates(
                session=session,
                username=username,
                role=role,
                pose_templates=pose_templates,
                n_samples_by_pose={
                    "center": len(angle_embeddings["center"]),
                    "left": len(angle_embeddings["left"]),
                    "right": len(angle_embeddings["right"]),
                },
            )

            if face_result.get("reason") == "USER_NOT_FOUND":
                return BiometricEnrollResponse(
                    success=False,
                    message="USER_NOT_FOUND",
                    user_id=None,
                    face_status="failed",
                    voice_status="failed",
                )

            voice_result = await _auth_service.save_voice_template_vector(
                session=session,
                username=username,
                voice_vec=merged_voice_template,
            )

            if voice_result.get("reason") == "USER_NOT_FOUND":
                return BiometricEnrollResponse(
                    success=False,
                    message="USER_NOT_FOUND",
                    user_id=None,
                    face_status="failed",
                    voice_status="failed",
                )

            await session.commit()

            return BiometricEnrollResponse(
                success=True,
                message="Biometric enrollment completed",
                user_id=None,
                face_status=face_status,
                voice_status=voice_status,
            )

        # Fallback: service save fonksiyonları henüz hazır değilse sadece processing başarılı dön
        return BiometricEnrollResponse(
            success=True,
            message="Biometric enrollment processed (save functions not fully integrated yet)",
            user_id=None,
            face_status=face_status,
            voice_status=voice_status,
        )

    except Exception as e:
        await session.rollback()
        return BiometricEnrollResponse(
            success=False,
            message=f"BIOMETRIC_SAVE_ERROR:{e}",
            user_id=None,
            face_status="failed",
            voice_status="failed",
        )