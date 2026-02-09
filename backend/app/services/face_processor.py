from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceFeatures:
    """
    Compact, normalized face-geometry features derived from MediaPipe FaceMesh.
    All values are designed to be relatively scale-invariant across different face sizes.
    """
    nose_x_norm: float          # approx [0,1] normalized x-coordinate
    left_eye_open_norm: float   # eye openness normalized by face height
    right_eye_open_norm: float  # eye openness normalized by face height


class FaceProcessor:
    """
    Face feature extractor using MediaPipe FaceMesh.

    Fail-safe behavior:
    - If MediaPipe is unavailable / incompatible on the current environment,
      the processor becomes "unavailable" and will raise a controlled ValueError
      when used (instead of crashing the API at startup).
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
        max_num_faces: int = 1,
        refine_landmarks: bool = True,
    ) -> None:
        self._mesh = None
        self._init_error: Optional[str] = None

        try:
            import mediapipe as mp

            # Some broken installs can import mediapipe but miss "solutions"
            if not hasattr(mp, "solutions"):
                raise RuntimeError("mediapipe_missing_solutions")

            self._mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,  # single-frame extraction (UI can stream later)
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
            )
        except Exception as e:
            # Mark as unavailable; do NOT crash app startup
            self._mesh = None
            self._init_error = f"{type(e).__name__}: {e}"

    @property
    def is_available(self) -> bool:
        return self._mesh is not None

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def close(self) -> None:
        """Release MediaPipe native resources (if initialized)."""
        if self._mesh is not None:
            try:
                self._mesh.close()
            except Exception:
                pass

    def extract_features(self, bgr_img: np.ndarray) -> FaceFeatures:
        """
        Extract normalized facial features from a BGR image.

        Args:
            bgr_img: OpenCV BGR image (H x W x 3)

        Returns:
            FaceFeatures with normalized values.

        Raises:
            ValueError: if input is invalid, no face is detected, or processor unavailable.
        """
        if self._mesh is None:
            # Controlled error for API layer to return a clean response
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

        # Base values
        nose_x = float(lm[self.NOSE_TIP].x)

        # Normalize eye openness by approximate face height (chin-to-nose distance)
        face_height = abs(float(lm[self.CHIN].y) - float(lm[self.NOSE_TIP].y))
        if face_height <= 1e-6:
            raise ValueError("FACE_HEIGHT_TOO_SMALL")

        left_open = abs(float(lm[self.LEFT_EYE_TOP].y) - float(lm[self.LEFT_EYE_BOTTOM].y)) / face_height
        right_open = abs(float(lm[self.RIGHT_EYE_TOP].y) - float(lm[self.RIGHT_EYE_BOTTOM].y)) / face_height

        return FaceFeatures(
            nose_x_norm=nose_x,
            left_eye_open_norm=left_open,
            right_eye_open_norm=right_open,
        )
