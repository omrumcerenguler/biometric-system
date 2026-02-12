from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceFeatures:
    """
    Compact, normalized face-geometry features derived from MediaPipe FaceMesh.
    """
    nose_x_norm: float
    left_eye_open_norm: float
    right_eye_open_norm: float


class FaceProcessor:
    """
    Face feature extractor using MediaPipe FaceMesh.

    Fail-safe behavior:
    - If MediaPipe is unavailable/incompatible, raises controlled ValueError when used.
    """

    # MediaPipe landmark indices (FaceMesh)
    NOSE_TIP: Final[int] = 1
    CHIN: Final[int] = 152

    LEFT_EYE_TOP: Final[int] = 159
    LEFT_EYE_BOTTOM: Final[int] = 145

    RIGHT_EYE_TOP: Final[int] = 386
    RIGHT_EYE_BOTTOM: Final[int] = 374

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        max_num_faces: int = 1,
        refine_landmarks: bool = True,
    ) -> None:
        self._mesh = None
        self._init_error: Optional[str] = None

        try:
            import mediapipe as mp

            if not hasattr(mp, "solutions"):
                raise RuntimeError("mediapipe_missing_solutions")

            # ✅ better for video / repeated frames
            self._mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        except Exception as e:
            self._mesh = None
            self._init_error = f"{type(e).__name__}: {e}"

    @property
    def is_available(self) -> bool:
        return self._mesh is not None

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def close(self) -> None:
        if self._mesh is not None:
            try:
                self._mesh.close()
            except Exception:
                pass

    def extract_features(self, bgr_img: np.ndarray) -> FaceFeatures:
        if self._mesh is None:
            raise ValueError("FACE_PROCESSOR_UNAVAILABLE")

        if bgr_img is None or not isinstance(bgr_img, np.ndarray) or bgr_img.size == 0:
            raise ValueError("INVALID_IMAGE")

        if bgr_img.ndim != 3 or bgr_img.shape[2] != 3:
            raise ValueError("INVALID_IMAGE_SHAPE")

        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        res = self._mesh.process(rgb)

        if not res.multi_face_landmarks:
            raise ValueError("FACE_NOT_DETECTED")

        lm = res.multi_face_landmarks[0].landmark

        nose_x = float(lm[self.NOSE_TIP].x)

        face_height = abs(float(lm[self.CHIN].y) - float(lm[self.NOSE_TIP].y))
        if face_height <= 1e-6:
            raise ValueError("FACE_HEIGHT_TOO_SMALL")

        left_open = abs(float(lm[self.LEFT_EYE_TOP].y) - float(lm[self.LEFT_EYE_BOTTOM].y)) / face_height
        right_open = abs(float(lm[self.RIGHT_EYE_TOP].y) - float(lm[self.RIGHT_EYE_BOTTOM].y)) / face_height

        # ✅ clamp to avoid extreme spikes
        left_open = float(max(0.0, min(1.0, left_open)))
        right_open = float(max(0.0, min(1.0, right_open)))

        return FaceFeatures(
            nose_x_norm=float(max(0.0, min(1.0, nose_x))),
            left_eye_open_norm=left_open,
            right_eye_open_norm=right_open,
        )
