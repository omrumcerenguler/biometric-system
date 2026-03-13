from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


@dataclass(frozen=True)
class EyeState:
    left_ear: float
    right_ear: float

    @property
    def mean_ear(self) -> float:
        return float((self.left_ear + self.right_ear) / 2.0)


class EyeStateDetector:
    """
    Lightweight eye-open detector using MediaPipe FaceMesh and EAR (eye aspect ratio).
    """

    LEFT_EYE_IDX = (33, 160, 158, 133, 153, 144)
    RIGHT_EYE_IDX = (362, 385, 387, 263, 373, 380)

    # Practical threshold for webcam quality. Lower means stricter open-eye requirement.
    EYE_OPEN_EAR_THRESHOLD = 0.18

    def __init__(self) -> None:
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
        )

    @staticmethod
    def _distance(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b))

    def _compute_ear(self, points: np.ndarray, idx: tuple[int, int, int, int, int, int]) -> float:
        p1, p2, p3, p4, p5, p6 = (points[i] for i in idx)

        denom = max(self._distance(p1, p4), 1e-6)
        ear = (self._distance(p2, p6) + self._distance(p3, p5)) / (2.0 * denom)
        return float(ear)

    def detect(self, bgr_img: np.ndarray) -> Optional[EyeState]:
        if bgr_img is None or bgr_img.size == 0:
            return None

        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        result = self._mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None

        h, w = bgr_img.shape[:2]
        lms = result.multi_face_landmarks[0].landmark
        pts = np.array([(lm.x * w, lm.y * h) for lm in lms], dtype=np.float32)

        left_ear = self._compute_ear(pts, self.LEFT_EYE_IDX)
        right_ear = self._compute_ear(pts, self.RIGHT_EYE_IDX)

        return EyeState(left_ear=left_ear, right_ear=right_ear)

    def are_eyes_open(self, bgr_img: np.ndarray) -> tuple[Optional[bool], Optional[EyeState]]:
        state = self.detect(bgr_img)
        if state is None:
            return None, None

        is_open = state.mean_ear >= self.EYE_OPEN_EAR_THRESHOLD
        return is_open, state
