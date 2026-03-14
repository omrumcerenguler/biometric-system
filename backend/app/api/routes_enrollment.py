from __future__ import annotations

import random
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import uuid4
from time import time
from typing import Dict, List

import numpy as np

from app.db.models import User
from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image
from app.utils.audio_io import b64_to_wav_mono

router = APIRouter(prefix="/enroll", tags=["enroll"])
_auth_service = AuthenticationService()
VOICE_MIN_SAMPLES = 5


# =====================================================
# ================ LEGACY (DISABLED) ==================
# =====================================================
class EnrollRequest(BaseModel):
    username: str
    role: str
    face_image_b64: str


@router.post("/")
async def enroll(req: EnrollRequest, session: AsyncSession = Depends(get_session)):
    """
    Legacy single-shot enroll endpoint is intentionally disabled.
    Product flow uses session-based face enrollment + voice enrollment.
    """
    raise HTTPException(
        status_code=410,
        detail="LEGACY_ENROLL_DISABLED_USE_SESSION_BASED_FLOW",
    )


# =====================================================
# ===================== HELPERS =======================
# =====================================================
async def _require_existing_user(session: AsyncSession, username: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    return user


# =====================================================
# ================== VOICE ENROLL =====================
# =====================================================
class EnrollVoiceRequest(BaseModel):
    username: str
    role: str
    voice_wav_b64: str
    challenge_id: str = ""
    challenge_answer_text: str = ""


class VoiceSampleRequest(BaseModel):
    voice_wav_b64: str
    challenge_id: str
    challenge_answer_text: str = ""


class EnrollVoiceBatchRequest(BaseModel):
    username: str
    role: str
    samples: List[VoiceSampleRequest]


VOICE_ENROLL_PHRASES = [
    {
        "id": "phrase-hello",
        "prompt": "Metni oku: Merhaba, ben {username}.",
    },
    {
        "id": "phrase-name",
        "prompt": "Metni oku: Benim adim {username}.",
    },
    {
        "id": "phrase-register",
        "prompt": "Metni oku: {username} olarak sisteme kayit yapiyorum.",
    },
    {
        "id": "phrase-auth",
        "prompt": "Metni oku: Kimlik dogrulamasi icin ses ornegi veriyorum.",
    },
    {
        "id": "phrase-session",
        "prompt": "Metni oku: Bu ses kaydi bugunku oturum icindir.",
    },
    {
        "id": "phrase-biometric",
        "prompt": "Metni oku: Biyometrik erisim icin konusuyorum.",
    },
    {
        "id": "phrase-clear",
        "prompt": "Metni oku: Simdi mikrofona normal tonda konusuyorum.",
    },
    {
        "id": "phrase-template",
        "prompt": "Metni oku: Bu ornek ses sablonu olusturmak icindir.",
    },
]


class VoiceChallengeResponse(BaseModel):
    challenge_id: str
    prompt: str


@router.get("/voice/challenge", response_model=VoiceChallengeResponse)
async def get_voice_challenge(
    exclude_ids: list[str] | None = Query(default=None),
    username: str | None = Query(default=None),
):
    excluded = {value.strip() for value in (exclude_ids or []) if value and value.strip()}
    available = [challenge for challenge in VOICE_ENROLL_PHRASES if challenge["id"] not in excluded]

    if not available:
        available = VOICE_ENROLL_PHRASES

    challenge = random.choice(available)
    safe_username = (username or "kullanici").strip() or "kullanici"
    prompt = challenge["prompt"].replace("{username}", safe_username)
    return VoiceChallengeResponse(
        challenge_id=challenge["id"],
        prompt=prompt,
    )


@router.post("/voice")
async def enroll_voice(req: EnrollVoiceRequest, session: AsyncSession = Depends(get_session)):
    """
    Save/update voice template for an EXISTING user only.
    """
    username = (req.username or "").strip()
    role = (req.role or "").strip()

    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")
    if not role:
        raise HTTPException(status_code=400, detail="ROLE_EMPTY")
    if not req.voice_wav_b64 or not req.voice_wav_b64.strip():
        raise HTTPException(status_code=400, detail="VOICE_EMPTY")

    # mevcut kullanıcı zorunlu
    await _require_existing_user(session, username)

    try:
        audio, sr = b64_to_wav_mono(req.voice_wav_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_VOICE_AUDIO: {e}")

    result = await _auth_service.enroll_voice(
        session=session,
        username=username,
        role=role,
        audio=audio,
        sr=sr,
    )

    if result.get("reason") == "USER_NOT_FOUND":
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    # Commit staged face template only after voice succeeds.
    status = str(result.get("status", "")).upper()
    if status in {"VOICE_ENROLLED", "VOICE_UPDATED", "VOICE_ALREADY_REGISTERED"}:
        pending = PENDING_FACE_TEMPLATES.get(username)
        if pending:
            face_result = await _auth_service.enroll_user_with_pose_templates(
                session=session,
                username=username,
                role=role,
                pose_templates=pending.get("pose_templates", {}),
                n_samples_by_pose=pending.get("samples_by_pose", {}),
            )
            if face_result.get("reason") != "USER_NOT_FOUND":
                PENDING_FACE_TEMPLATES.pop(username, None)

    return result


@router.post("/voice/batch")
async def enroll_voice_batch(req: EnrollVoiceBatchRequest, session: AsyncSession = Depends(get_session)):
    username = (req.username or "").strip()
    role = (req.role or "").strip()

    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")
    if not role:
        raise HTTPException(status_code=400, detail="ROLE_EMPTY")
    if not req.samples or len(req.samples) < VOICE_MIN_SAMPLES:
        raise HTTPException(status_code=400, detail=f"VOICE_SAMPLES_MIN_{VOICE_MIN_SAMPLES}")

    await _require_existing_user(session, username)

    vectors: List[np.ndarray] = []
    for sample in req.samples:
        if not sample.voice_wav_b64 or not sample.voice_wav_b64.strip():
            raise HTTPException(status_code=400, detail="VOICE_EMPTY")
        if not sample.challenge_id or not sample.challenge_id.strip():
            raise HTTPException(status_code=400, detail="VOICE_CHALLENGE_EMPTY")

        try:
            audio, sr = b64_to_wav_mono(sample.voice_wav_b64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"INVALID_VOICE_AUDIO: {e}")

        vec = _auth_service.extract_voice_embedding(audio, sr)
        if vec is None:
            return {
                "status": "FAILED",
                "reason": "VOICE_EMBEDDING_FAILED",
                "detail": {
                    "sample_index": len(vectors) + 1,
                    "hint": "Speak at least 1 second per question",
                },
            }
        vectors.append(vec)

    merged = np.mean(np.stack(vectors, axis=0), axis=0)
    merged = merged / (np.linalg.norm(merged) + 1e-9)

    result = await _auth_service.save_voice_template_vector(
        session=session,
        username=username,
        voice_vec=merged,
    )

    if result.get("reason") == "USER_NOT_FOUND":
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    # Commit staged face template only after voice succeeds.
    status = str(result.get("status", "")).upper()
    if status in {"VOICE_ENROLLED", "VOICE_UPDATED", "VOICE_ALREADY_REGISTERED"}:
        pending = PENDING_FACE_TEMPLATES.get(username)
        if pending:
            face_result = await _auth_service.enroll_user_with_pose_templates(
                session=session,
                username=username,
                role=role,
                pose_templates=pending.get("pose_templates", {}),
                n_samples_by_pose=pending.get("samples_by_pose", {}),
            )
            if face_result.get("reason") != "USER_NOT_FOUND":
                PENDING_FACE_TEMPLATES.pop(username, None)

    return {
        **result,
        "samples_used": len(vectors),
    }


# =====================================================
# ============ SESSION-BASED FACE ENROLL =============
# =====================================================
TARGET_SAMPLES = 15
TARGET_PER_ANGLE = 5
SESSION_TTL_SECONDS = 120  # 2 minutes
ENROLL_SESSIONS: Dict[str, dict] = {}
PENDING_FACE_TEMPLATES: Dict[str, dict] = {}


ANGLE_SEQUENCE = ["center", "left", "right"]


def _bucket_nose_ratio(nose_x_ratio: float | None) -> str | None:
    if nose_x_ratio is None:
        return None

    if nose_x_ratio < 0.44:
        return "left"
    if nose_x_ratio > 0.56:
        return "right"
    return "center"


def _get_session_or_404(session_id: str) -> dict:
    s = ENROLL_SESSIONS.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")

    if time() - s["created_at"] > SESSION_TTL_SECONDS:
        ENROLL_SESSIONS.pop(session_id, None)
        raise HTTPException(status_code=404, detail="SESSION_EXPIRED")

    return s


class EnrollStartRequest(BaseModel):
    username: str
    role: str


class EnrollStartResponse(BaseModel):
    session_id: str
    target: int
    required_angle: str


@router.post("/start", response_model=EnrollStartResponse)
async def start(req: EnrollStartRequest, session: AsyncSession = Depends(get_session)):
    username = (req.username or "").strip()
    role = (req.role or "").strip()

    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")
    if not role:
        raise HTTPException(status_code=400, detail="ROLE_EMPTY")

    # mevcut kullanıcı zorunlu
    await _require_existing_user(session, username)

    sid = str(uuid4())
    ENROLL_SESSIONS[sid] = {
        "created_at": time(),
        "username": username,
        "role": role,
        "embeddings": [],  # List[np.ndarray]
        "embeddings_by_angle": {"center": [], "left": [], "right": []},
        "accepted": 0,
        "target": TARGET_SAMPLES,
        "angle_counts": {"center": 0, "left": 0, "right": 0},
        "angle_idx": 0,
    }

    return EnrollStartResponse(
        session_id=sid,
        target=TARGET_SAMPLES,
        required_angle=ANGLE_SEQUENCE[0],
    )


class EnrollFrameRequest(BaseModel):
    session_id: str
    face_image_b64: str


class EnrollFrameResponse(BaseModel):
    accepted: bool
    reason: str
    count: int
    target: int
    required_angle: str
    angle_counts: Dict[str, int]


@router.post("/frame", response_model=EnrollFrameResponse)
async def push_frame(req: EnrollFrameRequest):
    s = _get_session_or_404(req.session_id)
    required_angle = ANGLE_SEQUENCE[min(s["angle_idx"], len(ANGLE_SEQUENCE) - 1)]

    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        return EnrollFrameResponse(
            accepted=False,
            reason=f"INVALID_IMAGE:{e}",
            count=s["accepted"],
            target=s["target"],
            required_angle=required_angle,
            angle_counts=s["angle_counts"],
        )

    emb, nose_x_ratio = _auth_service.extract_face_embedding_and_pose(img)
    if emb is None:
        return EnrollFrameResponse(
            accepted=False,
            reason="NO_FACE_OR_LOW_QUALITY",
            count=s["accepted"],
            target=s["target"],
            required_angle=required_angle,
            angle_counts=s["angle_counts"],
        )

    bucket = _bucket_nose_ratio(nose_x_ratio)
    if bucket is None:
        return EnrollFrameResponse(
            accepted=False,
            reason="POSE_NOT_DETECTED",
            count=s["accepted"],
            target=s["target"],
            required_angle=required_angle,
            angle_counts=s["angle_counts"],
        )

    if bucket != required_angle:
        return EnrollFrameResponse(
            accepted=False,
            reason=f"REQUIRE_{required_angle.upper()}",
            count=s["accepted"],
            target=s["target"],
            required_angle=required_angle,
            angle_counts=s["angle_counts"],
        )

    s["embeddings"].append(emb)
    s["embeddings_by_angle"][required_angle].append(emb)
    s["accepted"] += 1
    s["angle_counts"][required_angle] += 1

    if s["angle_counts"][required_angle] >= TARGET_PER_ANGLE and s["angle_idx"] < len(ANGLE_SEQUENCE) - 1:
        s["angle_idx"] += 1

    required_angle = ANGLE_SEQUENCE[min(s["angle_idx"], len(ANGLE_SEQUENCE) - 1)]

    reason = "OK"
    if s["accepted"] >= s["target"]:
        reason = "TARGET_REACHED"

    return EnrollFrameResponse(
        accepted=True,
        reason=reason,
        count=s["accepted"],
        target=s["target"],
        required_angle=required_angle,
        angle_counts=s["angle_counts"],
    )


class EnrollFinishRequest(BaseModel):
    session_id: str


@router.post("/finish")
async def finish(req: EnrollFinishRequest, session: AsyncSession = Depends(get_session)):
    s = _get_session_or_404(req.session_id)

    embs: List[np.ndarray] = s["embeddings"]
    if len(embs) < 5:
        raise HTTPException(status_code=400, detail="NOT_ENOUGH_SAMPLES(min=5)")

    by_angle: Dict[str, List[np.ndarray]] = s.get("embeddings_by_angle", {})
    pose_templates: Dict[str, np.ndarray] = {}
    for pose in ANGLE_SEQUENCE:
        samples = by_angle.get(pose, [])
        if not samples:
            continue
        template = np.mean(np.stack(samples, axis=0), axis=0)
        template = template / (np.linalg.norm(template) + 1e-9)
        pose_templates[pose] = template

    if "center" not in pose_templates:
        raise HTTPException(status_code=400, detail="CENTER_TEMPLATE_MISSING")

    samples_by_pose = {
        "center": len(by_angle.get("center", [])),
        "left": len(by_angle.get("left", [])),
        "right": len(by_angle.get("right", [])),
    }

    # Stage pose-aware face templates in memory. Persist only after voice enrollment succeeds.
    PENDING_FACE_TEMPLATES[s["username"]] = {
        "pose_templates": pose_templates,
        "n_samples": len(embs),
        "samples_by_pose": samples_by_pose,
        "created_at": time(),
    }

    ENROLL_SESSIONS.pop(req.session_id, None)

    return {
        "status": "FACE_STAGED",
        "n_samples": len(embs),
        "samples_by_pose": samples_by_pose,
        "message": "Face template staged. It will be saved after voice enrollment succeeds.",
    }