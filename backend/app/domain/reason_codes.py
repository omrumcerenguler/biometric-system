"""Canonical reason codes, legacy->canonical mappings and metadata.

This file is a non-breaking bootstrap: it only defines constants,
mapping tables and a helper to normalize legacy reason strings to
the canonical reason codes. Do not import or use these helpers in
runtime yet; they are added as a safe source-of-truth for future
commits.
"""
from typing import Dict

# --- REASON_CODES (canonical, stable identifiers) ------------------------
ACQ_NO_FACE = "ACQ_NO_FACE"
ACQ_MULTIPLE_FACES = "ACQ_MULTIPLE_FACES"
ACQ_FACE_NOT_FRONTAL = "ACQ_FACE_NOT_FRONTAL"
ACQ_FACE_YAW_OUT_OF_RANGE = "ACQ_FACE_YAW_OUT_OF_RANGE"
ACQ_FACE_TOO_SMALL = "ACQ_FACE_TOO_SMALL"
ACQ_FACE_BLURRY = "ACQ_FACE_BLURRY"
ACQ_EYES_CLOSED = "ACQ_EYES_CLOSED"
ACQ_EYES_NOT_CLEAR = "ACQ_EYES_NOT_CLEAR"
ACQ_POSE_MISMATCH = "ACQ_POSE_MISMATCH"
ACQ_POSE_NOT_ENOUGH_TURN = "ACQ_POSE_NOT_ENOUGH_TURN"
ACQ_REFERENCE_FACE_INVALID = "ACQ_REFERENCE_FACE_INVALID"
ACQ_FACE_MISMATCH = "ACQ_FACE_MISMATCH"
ACQ_BLINK_NOT_DETECTED = "ACQ_BLINK_NOT_DETECTED"
ACQ_INSUFFICIENT_FRAMES = "ACQ_INSUFFICIENT_FRAMES"
ACQ_REQUIRED_TURN_INVALID = "ACQ_REQUIRED_TURN_INVALID"

VOICE_REQUIRED = "VOICE_REQUIRED"
VOICE_NOT_RECORDED = "VOICE_NOT_RECORDED"
VOICE_EMBEDDING_FAILED = "VOICE_EMBEDDING_FAILED"
VOICE_NOT_ENROLLED = "VOICE_NOT_ENROLLED"
VOICE_NOT_MATCHED = "VOICE_NOT_MATCHED"
VOICE_CHALLENGE_TOO_SHORT = "VOICE_CHALLENGE_TOO_SHORT"
VOICE_CHALLENGE_INVALID = "VOICE_CHALLENGE_INVALID"

ENROLL_USERNAME_EMPTY = "ENROLL_USERNAME_EMPTY"
ENROLL_ROLE_EMPTY = "ENROLL_ROLE_EMPTY"
ENROLL_FACE_SAMPLES_EMPTY = "ENROLL_FACE_SAMPLES_EMPTY"
ENROLL_VOICE_SAMPLES_EMPTY = "ENROLL_VOICE_SAMPLES_EMPTY"
ENROLL_INVALID_FACE_ANGLE = "ENROLL_INVALID_FACE_ANGLE"
ENROLL_FACE_EMBEDDING_FAILED = "ENROLL_FACE_EMBEDDING_FAILED"
ENROLL_FACE_POSE_MISMATCH = "ENROLL_FACE_POSE_MISMATCH"
ENROLL_INSUFFICIENT_FACE_SAMPLES = "ENROLL_INSUFFICIENT_FACE_SAMPLES"
ENROLL_VOICE_SAMPLES_INSUFFICIENT = "ENROLL_VOICE_SAMPLES_INSUFFICIENT"
ENROLL_VOICE_PROMPT_EMPTY = "ENROLL_VOICE_PROMPT_EMPTY"
ENROLL_VOICE_EMBEDDING_FAILED = "ENROLL_VOICE_EMBEDDING_FAILED"
ENROLL_DUPLICATE_FACE = "ENROLL_DUPLICATE_FACE"
ENROLL_DUPLICATE_VOICE = "ENROLL_DUPLICATE_VOICE"
ENROLL_SAVE_ERROR = "ENROLL_SAVE_ERROR"
ENROLL_FAILED = "ENROLL_FAILED"

AUTH_MISSING_TOKEN = "AUTH_MISSING_TOKEN"
AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
AUTH_INVALID_TOKEN_PAYLOAD = "AUTH_INVALID_TOKEN_PAYLOAD"
AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"
AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"

NET_NETWORK_ERROR = "NET_NETWORK_ERROR"
SYS_INVALID_IMAGE = "SYS_INVALID_IMAGE"
SYS_INVALID_REFERENCE_IMAGE = "SYS_INVALID_REFERENCE_IMAGE"
SYS_UNKNOWN_ERROR = "SYS_UNKNOWN_ERROR"


# Aggregate list for quick membership checks
REASON_CODES = [
    ACQ_NO_FACE,
    ACQ_MULTIPLE_FACES,
    ACQ_FACE_NOT_FRONTAL,
    ACQ_FACE_YAW_OUT_OF_RANGE,
    ACQ_FACE_TOO_SMALL,
    ACQ_FACE_BLURRY,
    ACQ_EYES_CLOSED,
    ACQ_EYES_NOT_CLEAR,
    ACQ_POSE_MISMATCH,
    ACQ_POSE_NOT_ENOUGH_TURN,
    ACQ_REFERENCE_FACE_INVALID,
    ACQ_FACE_MISMATCH,
    ACQ_BLINK_NOT_DETECTED,
    ACQ_INSUFFICIENT_FRAMES,
    ACQ_REQUIRED_TURN_INVALID,
    VOICE_REQUIRED,
    VOICE_NOT_RECORDED,
    VOICE_EMBEDDING_FAILED,
    VOICE_NOT_ENROLLED,
    VOICE_NOT_MATCHED,
    VOICE_CHALLENGE_TOO_SHORT,
    VOICE_CHALLENGE_INVALID,
    ENROLL_USERNAME_EMPTY,
    ENROLL_ROLE_EMPTY,
    ENROLL_FACE_SAMPLES_EMPTY,
    ENROLL_VOICE_SAMPLES_EMPTY,
    ENROLL_INVALID_FACE_ANGLE,
    ENROLL_FACE_EMBEDDING_FAILED,
    ENROLL_FACE_POSE_MISMATCH,
    ENROLL_INSUFFICIENT_FACE_SAMPLES,
    ENROLL_VOICE_SAMPLES_INSUFFICIENT,
    ENROLL_VOICE_PROMPT_EMPTY,
    ENROLL_VOICE_EMBEDDING_FAILED,
    ENROLL_DUPLICATE_FACE,
    ENROLL_DUPLICATE_VOICE,
    ENROLL_SAVE_ERROR,
    ENROLL_FAILED,
    AUTH_MISSING_TOKEN,
    AUTH_INVALID_TOKEN,
    AUTH_INVALID_TOKEN_PAYLOAD,
    AUTH_USER_NOT_FOUND,
    AUTH_USER_INACTIVE,
    AUTH_INSUFFICIENT_PERMISSIONS,
    NET_NETWORK_ERROR,
    SYS_INVALID_IMAGE,
    SYS_INVALID_REFERENCE_IMAGE,
    SYS_UNKNOWN_ERROR,
]


# --- LEGACY_TO_CANONICAL --------------------------------------------------
# Exact legacy string -> canonical reason mapping. Keep mappings to specific
# canonical codes (not broad categories). Add entries here as a bootstrap.
LEGACY_TO_CANONICAL: Dict[str, str] = {
    "NO_FACE_DETECTED": ACQ_NO_FACE,
    "FACE_NOT_DETECTED": ACQ_NO_FACE,
    "FACE_BLURRY": ACQ_FACE_BLURRY,
    "EYES_CLOSED": ACQ_EYES_CLOSED,
    "BLINK_NOT_DETECTED": ACQ_BLINK_NOT_DETECTED,
    "FACE_NOT_FRONTAL": ACQ_FACE_NOT_FRONTAL,
    "FACE_NOT_FRONTAL_ENOUGH": ACQ_FACE_NOT_FRONTAL,
    "FACE_MISMATCH": ACQ_FACE_MISMATCH,
    "TOO_SHORT": VOICE_CHALLENGE_TOO_SHORT,
    "CHALLENGE_ANSWER_INVALID": VOICE_CHALLENGE_INVALID,
    "VOICE_IDENTITY_MISMATCH": VOICE_NOT_MATCHED,
    "VOICE_NOT_MATCHED": VOICE_NOT_MATCHED,
    "NO_AUDIO": VOICE_NOT_RECORDED,
    "VOICE_REQUIRED": VOICE_REQUIRED,
    # enrollment legacy variants
    "USERNAME_EMPTY": ENROLL_USERNAME_EMPTY,
    "ROLE_EMPTY": ENROLL_ROLE_EMPTY,
    "FACE_SAMPLES_EMPTY": ENROLL_FACE_SAMPLES_EMPTY,
    "VOICE_SAMPLES_EMPTY": ENROLL_VOICE_SAMPLES_EMPTY,
}


# --- REASON_META ----------------------------------------------------------
# For each canonical code provide category, retryable and a default message.
REASON_META: Dict[str, Dict[str, object]] = {
    ACQ_NO_FACE: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Face not detected clearly. Please center your face.",
    },
    ACQ_MULTIPLE_FACES: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Multiple faces detected. Ensure only you are in frame.",
    },
    ACQ_FACE_NOT_FRONTAL: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Please face the camera directly (frontal).",
    },
    ACQ_FACE_YAW_OUT_OF_RANGE: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Please turn your head slightly so it's within view.",
    },
    ACQ_FACE_TOO_SMALL: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Move closer to the camera so your face fills more of the frame.",
    },
    ACQ_FACE_BLURRY: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Face appears blurry. Try holding still or improving lighting.",
    },
    ACQ_EYES_CLOSED: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Please open your eyes for the capture.",
    },
    ACQ_EYES_NOT_CLEAR: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Eyes not clearly visible. Adjust lighting or remove obstructions.",
    },
    ACQ_POSE_MISMATCH: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Please follow the pose instructions (turn/look).",
    },
    ACQ_POSE_NOT_ENOUGH_TURN: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Turn your head more to satisfy the pose check.",
    },
    ACQ_REFERENCE_FACE_INVALID: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Reference/enrolled face is invalid. Contact support.",
    },
    ACQ_FACE_MISMATCH: {
        "category": "FACE_REJECT",
        "retryable": False,
        "message": "Face did not match the enrolled identity.",
    },
    ACQ_BLINK_NOT_DETECTED: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Blink not detected. Please blink when prompted.",
    },
    ACQ_INSUFFICIENT_FRAMES: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Not enough frames captured. Try again and remain steady.",
    },
    ACQ_REQUIRED_TURN_INVALID: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Requested turn/pose invalid for this device. Try a different angle.",
    },
    VOICE_REQUIRED: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Voice is required for verification. Please record your answer.",
    },
    VOICE_NOT_RECORDED: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "No voice was recorded. Please try again.",
    },
    VOICE_EMBEDDING_FAILED: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Voice processing failed. Contact support.",
    },
    VOICE_NOT_ENROLLED: {
        "category": "VOICE_REJECT",
        "retryable": False,
        "message": "No voice enrollment found for this user.",
    },
    VOICE_NOT_MATCHED: {
        "category": "VOICE_REJECT",
        "retryable": False,
        "message": "Voice did not match the enrolled voice.",
    },
    VOICE_CHALLENGE_TOO_SHORT: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Recording too short. Please record the full challenge sentence.",
    },
    VOICE_CHALLENGE_INVALID: {
        "category": "USER_ACTION",
        "retryable": True,
        "message": "Recorded challenge didn't match required prompt. Try again.",
    },
    ENROLL_USERNAME_EMPTY: {
        "category": "ENROLLMENT",
        "retryable": False,
        "message": "Username is required for enrollment.",
    },
    ENROLL_ROLE_EMPTY: {
        "category": "ENROLLMENT",
        "retryable": False,
        "message": "Role is required for enrollment.",
    },
    ENROLL_FACE_SAMPLES_EMPTY: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Provide face samples to continue enrollment.",
    },
    ENROLL_VOICE_SAMPLES_EMPTY: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Provide voice samples to continue enrollment.",
    },
    ENROLL_INVALID_FACE_ANGLE: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Face angle invalid for enrollment. Follow guidance.",
    },
    ENROLL_FACE_EMBEDDING_FAILED: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Face embedding failed during enrollment.",
    },
    ENROLL_FACE_POSE_MISMATCH: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Face pose mismatch. Please follow enrollment pose instructions.",
    },
    ENROLL_INSUFFICIENT_FACE_SAMPLES: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Insufficient face samples for enrollment.",
    },
    ENROLL_VOICE_SAMPLES_INSUFFICIENT: {
        "category": "ENROLLMENT",
        "retryable": True,
        "message": "Insufficient voice samples for enrollment.",
    },
    ENROLL_VOICE_PROMPT_EMPTY: {
        "category": "ENROLLMENT",
        "retryable": False,
        "message": "Voice prompt is missing for enrollment.",
    },
    ENROLL_VOICE_EMBEDDING_FAILED: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Voice embedding failed during enrollment.",
    },
    ENROLL_DUPLICATE_FACE: {
        "category": "ENROLLMENT",
        "retryable": False,
        "message": "A similar face is already enrolled.",
    },
    ENROLL_DUPLICATE_VOICE: {
        "category": "ENROLLMENT",
        "retryable": False,
        "message": "A similar voice is already enrolled.",
    },
    ENROLL_SAVE_ERROR: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Failed to save enrollment. Try again later.",
    },
    ENROLL_FAILED: {
        "category": "SYSTEM",
        "retryable": False,
        "message": "Enrollment failed. Contact support.",
    },
    AUTH_MISSING_TOKEN: {"category": "AUTH_ERROR", "retryable": False, "message": "Authentication token missing."},
    AUTH_INVALID_TOKEN: {"category": "AUTH_ERROR", "retryable": False, "message": "Invalid authentication token."},
    AUTH_INVALID_TOKEN_PAYLOAD: {"category": "AUTH_ERROR", "retryable": False, "message": "Authentication token payload invalid."},
    AUTH_USER_NOT_FOUND: {"category": "AUTH_ERROR", "retryable": False, "message": "User not found."},
    AUTH_USER_INACTIVE: {"category": "AUTH_ERROR", "retryable": False, "message": "User account is inactive."},
    AUTH_INSUFFICIENT_PERMISSIONS: {"category": "AUTH_ERROR", "retryable": False, "message": "Insufficient permissions."},
    NET_NETWORK_ERROR: {"category": "NETWORK", "retryable": True, "message": "Network error. Check your connection."},
    SYS_INVALID_IMAGE: {"category": "SYSTEM", "retryable": False, "message": "Invalid image provided."},
    SYS_INVALID_REFERENCE_IMAGE: {"category": "SYSTEM", "retryable": False, "message": "Invalid reference/enrolled image."},
    SYS_UNKNOWN_ERROR: {"category": "SYSTEM", "retryable": False, "message": "Unknown system error."},
}


def normalize_reason_code(reason: str) -> str:
    """Normalize a legacy or canonical reason string to a canonical reason code.

    Returns a canonical reason code defined in REASON_CODES. If the input
    is unknown, returns `SYS_UNKNOWN_ERROR`.
    """
    if not reason:
        return SYS_UNKNOWN_ERROR
    reason = reason.strip()
    # If already a canonical code, return as-is
    if reason in REASON_CODES:
        return reason
    # Exact-match legacy mapping
    mapped = LEGACY_TO_CANONICAL.get(reason)
    if mapped:
        return mapped
    # Try uppercase variant match
    mapped = LEGACY_TO_CANONICAL.get(reason.upper())
    if mapped:
        return mapped
    # Unknown fallback
    return SYS_UNKNOWN_ERROR


__all__ = [
    "REASON_CODES",
    "LEGACY_TO_CANONICAL",
    "REASON_META",
    "normalize_reason_code",
]
