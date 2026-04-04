from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

import logging
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, BiometricData
from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image
from app.utils.audio_io import b64_to_wav_mono
from app.domain.schemas import (
    BiometricEnrollRequest,
    BiometricEnrollResponse,
    FacePrecheckRequest,
    FacePrecheckResponse,
    VoicePrecheckRequest,
    VoicePrecheckResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enroll", tags=["enroll"])
_auth_service = AuthenticationService()

REQUIRED_FACE_ANGLES = ("center", "left", "right")
REQUIRED_FACE_SAMPLES_PER_ANGLE = 5
REQUIRED_TOTAL_VOICE_SAMPLES = 10


async def _require_existing_user(session: AsyncSession, username: str, client: str = "portal") -> User:
    result = await session.execute(select(User).where(User.username == username, User.client == client))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    return user


def _normalize_vector(vec: np.ndarray) -> np.ndarray:
    return vec / (np.linalg.norm(vec) + 1e-9)


@router.post("/precheck/face", response_model=FacePrecheckResponse)
async def precheck_face_duplicate(
    req: FacePrecheckRequest,
    session: AsyncSession = Depends(get_session),
    x_client: str = Header(default="portal", alias="X-Client"),
):
    username = (req.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")

    await _require_existing_user(session, username, x_client)

    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="FACE_IMAGE_DECODE_ERROR")

    if hasattr(_auth_service, "extract_face_embedding_and_pose"):
        emb, *_ = _auth_service.extract_face_embedding_and_pose(img)
    else:
        emb = _auth_service.face.extract_embedding(img)

    if emb is None:
        return FacePrecheckResponse(
            duplicate=False,
            reason="FACE_EMBEDDING_FAILED",
            matched_username=None,
            matched_user_id=None,
            similarity=0.0,
        )

    emb = _normalize_vector(np.asarray(emb, dtype=np.float32).reshape(-1))
    result = await _auth_service.precheck_face_duplicate(session, username, emb, x_client)
    return FacePrecheckResponse(**result)


@router.post("/precheck/voice", response_model=VoicePrecheckResponse)
async def precheck_voice_duplicate(
    req: VoicePrecheckRequest,
    session: AsyncSession = Depends(get_session),
    x_client: str = Header(default="portal", alias="X-Client")
):
    username = (req.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")

    await _require_existing_user(session, username,x_client)

    try:
        audio, sr = b64_to_wav_mono(req.voice_wav_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="VOICE_AUDIO_DECODE_ERROR")

    emb = _auth_service.voice.extract_embedding(audio, sr)
    if emb is None:
        return VoicePrecheckResponse(
            duplicate=False,
            reason="VOICE_EMBEDDING_FAILED",
            matched_username=None,
            matched_user_id=None,
            similarity=0.0,
        )

    emb = _normalize_vector(np.asarray(emb, dtype=np.float32).reshape(-1))
    result = await _auth_service.precheck_voice_duplicate(session, username, emb,x_client)
    return VoicePrecheckResponse(**result)


@router.post("/biometric", response_model=BiometricEnrollResponse)
async def enroll_biometric(
    req: BiometricEnrollRequest,
    session: AsyncSession = Depends(get_session),
     x_client: str = Header(default="portal", alias="X-Client"),
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

    user = await _require_existing_user(session, username, x_client)



    face_status = "not_processed"
    voice_status = "not_processed"

    # -------------------------------------------------
    # FACE PROCESSING
    # -------------------------------------------------
    try:
        angle_embeddings: Dict[str, List[np.ndarray]] = defaultdict(list)

        for idx, sample in enumerate(face_samples):
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
                client=x_client,
            )

            if face_result.get("reason") == "USER_NOT_FOUND":
                await session.rollback()
                return BiometricEnrollResponse(
                    success=False,
                    message="USER_NOT_FOUND",
                    user_id=None,
                    face_status="failed",
                    voice_status="failed",
                )

            if face_result.get("status") == "FACE_ALREADY_REGISTERED_OTHER_USER":
                await session.rollback()
                return BiometricEnrollResponse(
                    success=False,
                    message=(
                        "FACE_ALREADY_REGISTERED_OTHER_USER:"
                        f"username={face_result.get('other_username')},"
                        f"similarity={float(face_result.get('similarity', 0.0)):.4f}"
                    ),
                    user_id=face_result.get("other_user_id"),
                    face_status="duplicate_face",
                    voice_status="not_processed",
                )

            voice_result = await _auth_service.save_voice_template_vector(
                session=session,
                username=username,
                voice_vec=merged_voice_template,
                client=x_client,
            )

            if voice_result.get("reason") == "USER_NOT_FOUND":
                await session.rollback()
                return BiometricEnrollResponse(
                    success=False,
                    message="USER_NOT_FOUND",
                    user_id=None,
                    face_status="failed",
                    voice_status="failed",
                )

            if voice_result.get("status") == "VOICE_ALREADY_REGISTERED_OTHER_USER":
                await session.rollback()
                return BiometricEnrollResponse(
                    success=False,
                    message=(
                        "VOICE_ALREADY_REGISTERED_OTHER_USER:"
                        f"username={voice_result.get('other_username')},"
                        f"similarity={float(voice_result.get('similarity', 0.0)):.4f}"
                    ),
                    user_id=voice_result.get("other_user_id"),
                    face_status=face_status,
                    voice_status="duplicate_voice",
                )

            await session.commit()

            return BiometricEnrollResponse(
                success=True,
                message="Biometric enrollment completed",
                user_id=user.user_id,
                face_status=face_status,
                voice_status=voice_status,
            )

        return BiometricEnrollResponse(
            success=True,
            message="Biometric enrollment processed (save functions not fully integrated yet)",
            user_id=user.user_id,
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