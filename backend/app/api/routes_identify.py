
import random
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/identify", tags=["identify"])

_auth_service = AuthenticationService()

# --- Response Models ---
from pydantic import BaseModel
class IdentifyFaceResponse(BaseModel):
    identified: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    similarity: float
    reason: str
    yaw: Optional[float] = None
    blur_score: Optional[float] = None
    bbox_size: Optional[float] = None
    nose_x_ratio: Optional[float] = None
    debug_step: Optional[str] = None



class VoiceIdentifyRequest(BaseModel):
    voice_b64: str
    expected_user_id: int

class VoiceIdentifyResponse(BaseModel):
    identified: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    similarity: float
    threshold: float
    reason: str

class IdentifyRequest(BaseModel):
    face_image_b64: str
from app.utils.audio_io import b64_to_wav_mono

# Ses biyometrik kimlik doğrulama endpoint'i
@router.post("/voice", response_model=VoiceIdentifyResponse)
async def identify_voice(
    req: VoiceIdentifyRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        audio, sr = b64_to_wav_mono(req.voice_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"INVALID_AUDIO: {e}")

    # 1:1 voice identification (expected_user_id zorunlu)
    result = await _auth_service.identify_user_by_voice(
        session=session,
        audio=audio,
        sr=sr,
        expected_user_id=req.expected_user_id,
    )
    return result


class VoiceChallengeResponse(BaseModel):
    challenge_id: str
    prompt: str


class VoiceChallengeValidateRequest(BaseModel):
    challenge_id: str
    answer_text: str


class PoseCheckRequest(BaseModel):
    face_image_b64: str
    required_turn: str
    reference_face_image_b64: Optional[str] = None
    expected_user_id: Optional[int] = None
    require_eyes_open: bool = True


class BlinkCheckRequest(BaseModel):
    face_frames_b64: list[str]
    reference_face_image_b64: Optional[str] = None
    expected_user_id: Optional[int] = None


IDENTIFY_CHALLENGES = [
    {
        "id": "id-weekday",
        "prompt": "Soru: Bugun gunlerden ne?",
    },
    {
        "id": "id-month",
        "prompt": "Soru: Su an hangi aydayiz?",
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


def _current_weekday_keywords() -> list[str]:
    weekday_map = {
        0: ["pazartesi"],
        1: ["sali"],
        2: ["carsamba"],
        3: ["persembe"],
        4: ["cuma"],
        5: ["cumartesi"],
        6: ["pazar"],
    }
    return weekday_map.get(datetime.now().weekday(), [])


def _current_month_keywords() -> list[str]:
    month_map = {
        1: ["ocak"],
        2: ["subat"],
        3: ["mart"],
        4: ["nisan"],
        5: ["mayis"],
        6: ["haziran"],
        7: ["temmuz"],
        8: ["agustos"],
        9: ["eylul"],
        10: ["ekim"],
        11: ["kasim"],
        12: ["aralik"],
    }
    return month_map.get(datetime.now().month, [])


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

    if req.challenge_id == "id-weekday":
        expected_keywords = _current_weekday_keywords()
    elif req.challenge_id == "id-month":
        expected_keywords = _current_month_keywords()
    else:
        expected_keywords = challenge.get("keywords", [])

    passed = any(k in normalized for k in expected_keywords)
    return {
        "passed": passed,
        "reason": "OK" if passed else "CHALLENGE_ANSWER_INVALID",
    }


@router.post("/pose-check")
async def identify_pose_check(req: PoseCheckRequest, session: AsyncSession = Depends(get_session)):
    required = (req.required_turn or "").strip().lower()
    if required not in {"center", "left", "right"}:
        raise HTTPException(status_code=400, detail="REQUIRED_TURN_INVALID")

    pose_identity_thr = float(settings.FACE_POSE_IDENTITY_THRESHOLD)
    pose_min_delta = float(settings.FACE_POSE_MIN_DELTA)
    right_abs_min = float(settings.FACE_POSE_RIGHT_MIN_NOSE_X)
    left_abs_max = float(settings.FACE_POSE_LEFT_MAX_NOSE_X)

    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_IMAGE: {e}")

    face_count = _auth_service.count_faces(img)
    if face_count is not None and face_count > 1:
        return {
            "passed": False,
            "required_turn": required,
            "detected_turn": None,
            "reason": "MULTIPLE_FACES_DETECTED",
            "face_count": face_count,
        }

    probe_face_vec, nose_x, yaw, bbox_size, blur_score = _auth_service.extract_face_embedding_and_pose(img)
    if probe_face_vec is None:
        return {
            "passed": False,
            "required_turn": required,
            "detected_turn": None,
            "reason": "NO_FACE_DETECTED",
        }

    if req.require_eyes_open:
        eyes_open, _eye_state = _auth_service.eye_state.are_eyes_open(img)
        if eyes_open is False:
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": None,
                "reason": "EYES_CLOSED",
            }
        if eyes_open is None:
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": None,
                "reason": "EYES_NOT_CLEAR",
            }

    similarity = None
    template_similarity = None
    reference_nose_x = None

    if req.reference_face_image_b64:
        try:
            ref_img = b64_to_bgr_image(req.reference_face_image_b64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"INVALID_REFERENCE_IMAGE: {e}")

        _ref_face_vec, reference_nose_x, _ref_yaw, _ref_bbox_size, _ref_blur_score = _auth_service.extract_face_embedding_and_pose(ref_img)
        if reference_nose_x is None:
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": None,
                "reason": "REFERENCE_FACE_INVALID",
            }

    detected = _bucket_nose_ratio(nose_x)

    # Referans frontal frame varsa relative turn hesabı kullan
    if nose_x is not None and reference_nose_x is not None:
        delta = float(nose_x - reference_nose_x)
        if delta >= pose_min_delta:
            detected = "right"
        elif delta <= -pose_min_delta:
            detected = "left"
        else:
            detected = "center"

    # Genel turn eşleşmesi
    if detected != required:
        return {
            "passed": False,
            "required_turn": required,
            "detected_turn": detected,
            "reason": "POSE_NOT_ENOUGH_TURN" if detected == "center" and required in {"left", "right"} else "POSE_MISMATCH",
            "similarity": None,
            "reference_similarity": None,
            "reference_nose_x": reference_nose_x,
            "nose_x": nose_x,
            "pose_min_delta": pose_min_delta,
        }

    # center için frontal guard
    if required == "center":
        if nose_x is None or _bucket_nose_ratio(nose_x) != "center":
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": detected,
                "reason": "FACE_NOT_FRONTAL_ENOUGH",
                "similarity": None,
                "reference_similarity": None,
                "reference_nose_x": reference_nose_x,
                "nose_x": nose_x,
            }

    # right için absolute guard
    if required == "right" and (nose_x is None or float(nose_x) < right_abs_min):
        return {
            "passed": False,
            "required_turn": required,
            "detected_turn": "center",
            "reason": "POSE_NOT_ENOUGH_TURN",
            "similarity": None,
            "reference_similarity": None,
            "reference_nose_x": reference_nose_x,
            "nose_x": nose_x,
            "pose_min_delta": pose_min_delta,
            "right_abs_min": right_abs_min,
        }

    # left için absolute guard
    if required == "left" and (nose_x is None or float(nose_x) > left_abs_max):
        return {
            "passed": False,
            "required_turn": required,
            "detected_turn": "center",
            "reason": "POSE_NOT_ENOUGH_TURN",
            "similarity": None,
            "reference_similarity": None,
            "reference_nose_x": reference_nose_x,
            "nose_x": nose_x,
            "pose_min_delta": pose_min_delta,
            "left_abs_max": left_abs_max,
        }

    # İstenirse expected user'ın ilgili pose template'i ile identity check
    if req.expected_user_id is not None:
        expected_face_vec = await _auth_service._get_user_face_template(
            session=session,
            user_id=int(req.expected_user_id),
            pose=required,
        )
        if expected_face_vec is None:
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": detected,
                "reason": "EXPECTED_USER_POSE_TEMPLATE_MISSING",
                "similarity": similarity,
                "reference_similarity": None,
                "reference_nose_x": reference_nose_x,
                "nose_x": nose_x,
                "pose_min_delta": pose_min_delta,
            }

        template_similarity = float(_auth_service._cosine(probe_face_vec, expected_face_vec))
        if template_similarity < pose_identity_thr:
            return {
                "passed": False,
                "required_turn": required,
                "detected_turn": detected,
                "reason": "FACE_MISMATCH",
                "similarity": template_similarity,
                "reference_similarity": None,
                "threshold": pose_identity_thr,
                "reference_nose_x": reference_nose_x,
                "nose_x": nose_x,
                "pose_min_delta": pose_min_delta,
            }

    return {
        "passed": True,
        "required_turn": required,
        "detected_turn": detected,
        "reason": "OK",
        "similarity": template_similarity if template_similarity is not None else similarity,
        "reference_similarity": similarity,
        "reference_nose_x": reference_nose_x,
        "nose_x": nose_x,
        "pose_min_delta": pose_min_delta,
    }


@router.post("/blink-check")
async def identify_blink_check(req: BlinkCheckRequest, session: AsyncSession = Depends(get_session)):
    if not req.face_frames_b64 or len(req.face_frames_b64) < 6:
        raise HTTPException(status_code=400, detail="BLINK_FRAMES_MIN_6")

    first_valid_face_vec = None
    for raw in req.face_frames_b64:
        try:
            probe_img = b64_to_bgr_image(raw)
            vec, _nose_x, _yaw, _bbox_size, _blur_score = _auth_service.extract_face_embedding_and_pose(probe_img)
            if vec is not None:
                first_valid_face_vec = vec
                break
        except Exception:
            continue

    if req.reference_face_image_b64 and first_valid_face_vec is not None:
        try:
            ref_img = b64_to_bgr_image(req.reference_face_image_b64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"INVALID_REFERENCE_IMAGE: {e}")

        ref_vec = _auth_service.extract_face_embedding(ref_img)
        if ref_vec is not None:
            sim = float(_auth_service._cosine(first_valid_face_vec, ref_vec))
            if sim < float(settings.FACE_POSE_IDENTITY_THRESHOLD):
                return {
                    "passed": False,
                    "reason": "FACE_MISMATCH",
                    "similarity": sim,
                    "threshold": float(settings.FACE_POSE_IDENTITY_THRESHOLD),
                }

    if req.expected_user_id is not None and first_valid_face_vec is not None:
        expected_vec = await _auth_service._get_user_face_template(
            session=session,
            user_id=int(req.expected_user_id),
        )
        if expected_vec is not None:
            sim = float(_auth_service._cosine(first_valid_face_vec, expected_vec))
            if sim < float(settings.FACE_POSE_IDENTITY_THRESHOLD):
                return {
                    "passed": False,
                    "reason": "FACE_MISMATCH",
                    "similarity": sim,
                    "threshold": float(settings.FACE_POSE_IDENTITY_THRESHOLD),
                }

    ear_values: list[float] = []
    valid_frames = 0

    for raw in req.face_frames_b64:
        try:
            img = b64_to_bgr_image(raw)
        except ValueError:
            continue

        eye_state = _auth_service.eye_state.detect(img)
        if eye_state is None:
            continue

        valid_frames += 1
        ear_values.append(float(eye_state.mean_ear))

    if valid_frames < 4 or not ear_values:
        return {
            "passed": False,
            "reason": "EYES_NOT_CLEAR",
            "valid_frames": valid_frames,
        }

    baseline_ear = float(max(ear_values))
    min_ear = float(min(ear_values))
    if baseline_ear <= 1e-6:
        return {
            "passed": False,
            "reason": "EYES_NOT_CLEAR",
            "valid_frames": valid_frames,
        }

    drop_ratio = min_ear / baseline_ear
    threshold_ratio = 0.65
    blink_idx = int(min(range(len(ear_values)), key=lambda i: ear_values[i]))
    reopened = any(v >= baseline_ear * 0.80 for v in ear_values[blink_idx + 1 :])
    passed = drop_ratio <= threshold_ratio and reopened

    return {
        "passed": passed,
        "reason": "OK" if passed else "BLINK_NOT_DETECTED",
        "valid_frames": valid_frames,
        "baseline_ear": baseline_ear,
        "min_ear": min_ear,
        "drop_ratio": float(drop_ratio),
        "threshold_ratio": threshold_ratio,
        "reopened": reopened,
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
        # Debug alanlarını response'a ekle
        return IdentifyFaceResponse(
            identified=result.get("identified", False),
            user_id=result.get("user_id"),
            username=result.get("username"),
            similarity=result.get("similarity", 0.0),
            reason=result.get("reason", "UNKNOWN"),
            yaw=result.get("yaw"),
            blur_score=result.get("blur_score"),
            bbox_size=result.get("bbox_size"),
            nose_x_ratio=result.get("nose_x_ratio"),
            debug_step=result.get("debug_step"),
        )
    except ValueError as e:
        if str(e) == "FACE_NOT_DETECTED":
            raise HTTPException(status_code=400, detail="FACE_NOT_DETECTED")
        raise