from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import uuid4
from time import time
from typing import Dict, List

import numpy as np

from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/enroll", tags=["enroll"])
_auth_service = AuthenticationService()


# =====================================================
# ================ LEGACY (single-shot) ===============
# =====================================================
class EnrollRequest(BaseModel):
    username: str
    role: str
    face_image_b64: str


@router.post("/")
async def enroll(req: EnrollRequest, session: AsyncSession = Depends(get_session)):
    """
    Tek foto ile kayıt (eski endpoint - kalsın)
    """
    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_IMAGE: {e}")

    result = await _auth_service.enroll_user(
        session=session,
        username=req.username,
        role=req.role,
        face_img=img,
    )
    return result


# =====================================================
# ============ SESSION-BASED ENROLLMENT ===============
# =====================================================
TARGET_SAMPLES = 15
SESSION_TTL_SECONDS = 120  # 2 minutes
ENROLL_SESSIONS: Dict[str, dict] = {}


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


@router.post("/start", response_model=EnrollStartResponse)
async def start(req: EnrollStartRequest):
    username = req.username.strip()
    role = req.role.strip()

    if not username:
        raise HTTPException(status_code=400, detail="USERNAME_EMPTY")
    if not role:
        raise HTTPException(status_code=400, detail="ROLE_EMPTY")

    sid = str(uuid4())
    ENROLL_SESSIONS[sid] = {
        "created_at": time(),
        "username": username,
        "role": role,
        "embeddings": [],  # List[np.ndarray]
        "accepted": 0,
        "target": TARGET_SAMPLES,
    }

    return EnrollStartResponse(session_id=sid, target=TARGET_SAMPLES)


class EnrollFrameRequest(BaseModel):
    session_id: str
    face_image_b64: str


class EnrollFrameResponse(BaseModel):
    accepted: bool
    reason: str
    count: int
    target: int


@router.post("/frame", response_model=EnrollFrameResponse)
async def push_frame(req: EnrollFrameRequest):
    s = _get_session_or_404(req.session_id)

    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        return EnrollFrameResponse(
            accepted=False,
            reason=f"INVALID_IMAGE:{e}",
            count=s["accepted"],
            target=s["target"],
        )

    # 1) embedding çıkar
    emb = _auth_service.face.extract_embedding(img)
    if emb is None:
        return EnrollFrameResponse(
            accepted=False,
            reason="NO_FACE_OR_LOW_QUALITY",
            count=s["accepted"],
            target=s["target"],
        )

    # 2) normalize (cosine stabil)
    emb = emb.astype(np.float32)
    emb = emb / (np.linalg.norm(emb) + 1e-9)

    # 3) session'a ekle
    s["embeddings"].append(emb)
    s["accepted"] += 1

    reason = "OK"
    if s["accepted"] >= s["target"]:
        reason = "TARGET_REACHED"

    return EnrollFrameResponse(
        accepted=True,
        reason=reason,
        count=s["accepted"],
        target=s["target"],
    )


class EnrollFinishRequest(BaseModel):
    session_id: str


@router.post("/finish")
async def finish(req: EnrollFinishRequest, session: AsyncSession = Depends(get_session)):
    s = _get_session_or_404(req.session_id)

    embs: List[np.ndarray] = s["embeddings"]
    if len(embs) < 5:
        raise HTTPException(status_code=400, detail="NOT_ENOUGH_SAMPLES(min=5)")

    # template = mean + normalize
    template = np.mean(np.stack(embs, axis=0), axis=0)
    template = template / (np.linalg.norm(template) + 1e-9)

    result = await _auth_service.enroll_user_with_template(
        session=session,
        username=s["username"],
        role=s["role"],
        face_template=template,
        n_samples=len(embs),
    )

    ENROLL_SESSIONS.pop(req.session_id, None)
    return result