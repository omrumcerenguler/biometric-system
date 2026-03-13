from __future__ import annotations

import cv2
import numpy as np
from typing import Optional, Tuple


class FaceProcessor:
    """
    Real face embedding extractor using InsightFace.
    Produces 512-d face embedding vectors.
    """

    def __init__(self) -> None:
        self._model = None
        self._init_error: Optional[str] = None

        try:
            from insightface.app import FaceAnalysis

            self._model = FaceAnalysis(name="buffalo_l")
            self._model.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            self._init_error = f"{type(e).__name__}: {e}"
            self._model = None

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def extract_embedding(self, bgr_img: np.ndarray) -> np.ndarray:
        embedding, _ = self.extract_embedding_and_pose(bgr_img)
        return embedding

    def extract_embedding_and_pose(self, bgr_img: np.ndarray) -> Tuple[np.ndarray, Optional[float]]:
        if self._model is None:
            raise ValueError("FACE_PROCESSOR_UNAVAILABLE")

        if bgr_img is None or bgr_img.size == 0:
            raise ValueError("INVALID_IMAGE")

        faces = self._model.get(bgr_img)

        if len(faces) == 0:
            raise ValueError("FACE_NOT_DETECTED")

        # take first detected face
        face = faces[0]
        embedding = face.embedding.astype(np.float32)
        nose_x_ratio = self._estimate_nose_x_ratio(face)

        return embedding, nose_x_ratio

    def _estimate_nose_x_ratio(self, face) -> Optional[float]:
        """
        Estimate nose horizontal position relative to eye line.
        Returns a normalized ratio where ~0.5 is frontal.
        """
        kps = getattr(face, "kps", None)
        if kps is None:
            return None

        pts = np.asarray(kps, dtype=np.float32)
        if pts.shape[0] < 3:
            return None

        left_eye = pts[0]
        right_eye = pts[1]
        nose = pts[2]

        eye_span = float(right_eye[0] - left_eye[0])
        if abs(eye_span) < 1e-6:
            return None

        ratio = float((nose[0] - left_eye[0]) / eye_span)
        if not np.isfinite(ratio):
            return None

        return ratio