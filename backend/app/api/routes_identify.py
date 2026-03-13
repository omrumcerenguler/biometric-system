import random
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/identify", tags=["identify"])

_auth_service = AuthenticationService()


class IdentifyRequest(BaseModel):
    face_image_b64: str


class VoiceChallengeResponse(BaseModel):
    challenge_id: str
    prompt: str


class VoiceChallengeValidateRequest(BaseModel):
    challenge_id: str
    answer_text: str


class PoseCheckRequest(BaseModel):
    face_image_b64: str
    required_turn: str


IDENTIFY_CHALLENGES = [
    {
        "id": "id-weekday",
        "prompt": "Soru: Bugun gunlerden ne?",
        "keywords": ["pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi", "pazar"],
    },
    {
        "id": "id-weather",
        "prompt": "Soru: Bugun hava nasil? Bir iki kelimeyle soyleyin.",
        "keywords": ["gunesli", "yagmurlu", "bulutlu", "ruzgarli", "sicak", "soguk"],
    },
    {
        "id": "id-number",
        "prompt": "Soru: 7 artı 5 kac eder?",
        "keywords": ["12", "on iki", "onik"],
    },
]


def _normalize_text(value: str) -> str:
    out = (value or "").lower().strip()
    out = out.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ö", "o").replace("ü", "u").replace("ğ", "g")
    out = re.sub(r"[^a-z0-9 ]+", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _bucket_nose_ratio(nose_x_ratio: float | None) -> str | None:
    if nose_x_ratio is None:
        return None
    if nose_x_ratio < 0.44:
        return "left"
    if nose_x_ratio > 0.56:
        return "right"
    return "center"


@router.get("/voice-challenge", response_model=VoiceChallengeResponse)
async def get_identify_voice_challenge():
    ch = random.choice(IDENTIFY_CHALLENGES)
    return VoiceChallengeResponse(challenge_id=ch["id"], prompt=ch["prompt"])


@router.post("/voice-challenge/validate")
async def validate_identify_voice_challenge(req: VoiceChallengeValidateRequest):
    challenge = next((c for c in IDENTIFY_CHALLENGES if c["id"] == req.challenge_id), None)
    if challenge is None:
        raise HTTPException(status_code=400, detail="CHALLENGE_NOT_FOUND")

    normalized = _normalize_text(req.answer_text)
    passed = any(k in normalized for k in challenge["keywords"])
    return {
        "passed": passed,
        "reason": "OK" if passed else "CHALLENGE_ANSWER_INVALID",
    }


@router.post("/pose-check")
async def identify_pose_check(req: PoseCheckRequest):
    required = (req.required_turn or "").strip().lower()
    if required not in {"left", "right"}:
        raise HTTPException(status_code=400, detail="REQUIRED_TURN_INVALID")

    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_IMAGE: {e}")

    _, nose_x = _auth_service.extract_face_embedding_and_pose(img)
    detected = _bucket_nose_ratio(nose_x)
    passed = detected == required

    return {
        "passed": passed,
        "required_turn": required,
        "detected_turn": detected,
    }


@router.post("/")
async def identify(req: IdentifyRequest, session: AsyncSession = Depends(get_session)):
    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_IMAGE: {e}")
    
    try:
        result = await _auth_service.identify_user(
            session=session,
            face_img=img,
        )
        return result
    except ValueError as e:
        # FaceProcessor "FACE_NOT_DETECTED" atınca buraya düşecek
        if str(e) == "FACE_NOT_DETECTED":
            raise HTTPException(status_code=400, detail="FACE_NOT_DETECTED")
        raise

    result = await _auth_service.identify_face(
        session=session,
        face_img=img,
    )
    return result
