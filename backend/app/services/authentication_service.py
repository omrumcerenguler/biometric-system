from __future__ import annotations

from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.face_processor import FaceProcessor
from app.services.voice_processor import VoiceProcessor, VoiceFeatures


class AuthenticationService:
    """
    Minimal, stable, production-friendly service layer.

    Supports:
    - Face-only verification
    - Voice-only verification
    - Face + Voice fusion verification

    NOTE:
    - DB session is optional for now (future enrollment / template storage).
    """

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session

        self.face = FaceProcessor()
        self.voice = VoiceProcessor()

        # thresholds (later move to settings/config)
        self.fusion_thr = 0.75

    async def verify(
        self,
        username: str,
        face_img: Optional[np.ndarray],
        audio: Optional[np.ndarray],
        sr: Optional[int],
    ) -> dict:
        """
        `face_img` and `audio` are optional.
        - If only face_img is provided -> voice_score = 0.0, fusion = face_score
        - If only audio is provided -> face_score = 0.0, fusion = voice_score
        - If both are provided -> fusion = average(face_score, voice_score)
        """

        face_score = self._verify_face(face_img) if face_img is not None else 0.0
        voice_score = self._verify_voice(audio, sr) if (audio is not None and sr is not None) else 0.0

        used = 0
        total = 0.0
        if face_img is not None:
            total += face_score
            used += 1
        if audio is not None and sr is not None:
            total += voice_score
            used += 1

        fusion_score = (total / used) if used > 0 else 0.0

        decision = "GRANTED" if fusion_score >= self.fusion_thr else "DENIED"

        reason_parts = []
        reason_parts.append("face_used" if face_img is not None else "face_missing")
        reason_parts.append("voice_used" if (audio is not None and sr is not None) else "voice_missing")
        reason_parts.append(f"face={face_score:.2f}")
        reason_parts.append(f"voice={voice_score:.2f}")
        reason_parts.append(f"fusion={fusion_score:.2f}")
        reason_parts.append(f"thr={self.fusion_thr:.2f}")

        return {
            "decision": decision,
            "fusion_score": float(fusion_score),
            "face_score": float(face_score),
            "voice_score": float(voice_score),
            "reason": " | ".join(reason_parts),
        }

    def _verify_face(self, face_img: np.ndarray) -> float:
        """
        Uses FaceProcessor features and returns a normalized score [0,1].
        """
        feats = self.face.extract_features(face_img)

        # Very simple heuristic score (stable for demo)
        eye_avg = (feats.left_eye_open_norm + feats.right_eye_open_norm) / 2.0
        # nose_x close to center is better (0.5)
        center_score = 1.0 - abs(feats.nose_x_norm - 0.5) * 2.0
        center_score = max(0.0, min(1.0, center_score))

        score = 0.6 * eye_avg + 0.4 * center_score
        return float(max(0.0, min(1.0, score)))

    def _verify_voice(self, audio: np.ndarray, sr: int) -> float:
        """
        Uses VoiceProcessor feature extraction and returns a normalized score [0,1].
        This avoids relying on a non-existent `VoiceProcessor.score()` method.
        """
        feats: VoiceFeatures = self.voice.extract_features(audio, sr)

        # Heuristic scoring (stable):
        # - RMS should be above a small threshold (not silence)
        rms_ok = 1.0 if feats.rms > 0.01 else 0.1

        # - Flatness in moderate range
        flat_ok = 1.0 if 0.05 <= feats.spec_flatness <= 0.5 else 0.5

        # - ZCR moderate
        zcr_ok = 1.0 if 0.02 <= feats.zcr <= 0.2 else 0.6

        score = 0.45 * rms_ok + 0.30 * flat_ok + 0.25 * zcr_ok
        return float(max(0.0, min(1.0, score)))
