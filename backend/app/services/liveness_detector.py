from __future__ import annotations

from dataclasses import dataclass

from app.services.face_processor import FaceFeatures
from app.services.voice_processor import VoiceFeatures


@dataclass(frozen=True)
class LivenessScores:
    face_score: float
    voice_score: float


class LivenessDetector:
    """
    Heuristic liveness scoring (0..1).
    - Face: plausibility + normalized eye openness range
    - Voice: energy (rms) + spectral flatness + zcr sanity

    Thresholds are configurable so you can tune easily later.
    """

    def __init__(
        self,
        face_nose_min: float = 0.25,
        face_nose_max: float = 0.75,
        eye_open_min: float = 0.12,
        eye_open_max: float = 0.70,
        voice_rms_min: float = 0.01,
        voice_flat_min: float = 0.05,
        voice_flat_max: float = 0.50,
        voice_zcr_min: float = 0.02,
        voice_zcr_max: float = 0.20,
    ) -> None:
        self._nose_min = face_nose_min
        self._nose_max = face_nose_max
        self._eye_min = eye_open_min
        self._eye_max = eye_open_max

        self._rms_min = voice_rms_min
        self._flat_min = voice_flat_min
        self._flat_max = voice_flat_max
        self._zcr_min = voice_zcr_min
        self._zcr_max = voice_zcr_max

    @staticmethod
    def _clamp01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return float(x)

    def score_face(self, f: FaceFeatures) -> float:
        # Nose plausibility
        nose_score = 1.0 if (self._nose_min <= f.nose_x_norm <= self._nose_max) else 0.2

        # Normalized eye openness plausibility
        eye_mean = (f.left_eye_open_norm + f.right_eye_open_norm) / 2.0
        eye_score = 1.0 if (self._eye_min <= eye_mean <= self._eye_max) else 0.4

        return self._clamp01(0.55 * nose_score + 0.45 * eye_score)

    def score_voice(self, v: VoiceFeatures) -> float:
        rms_score = 1.0 if v.rms >= self._rms_min else 0.1

        if self._flat_min <= v.spec_flatness <= self._flat_max:
            flat_score = 1.0
        else:
            flat_score = 0.5

        if self._zcr_min <= v.zcr <= self._zcr_max:
            zcr_score = 1.0
        else:
            zcr_score = 0.6

        return self._clamp01(0.45 * rms_score + 0.30 * flat_score + 0.25 * zcr_score)

    def evaluate(self, face: FaceFeatures, voice: VoiceFeatures) -> LivenessScores:
        return LivenessScores(
            face_score=self.score_face(face),
            voice_score=self.score_voice(voice),
        )
