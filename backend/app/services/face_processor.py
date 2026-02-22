from __future__ import annotations

import cv2
import numpy as np
from typing import Optional


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
        if self._model is None:
            raise ValueError("FACE_PROCESSOR_UNAVAILABLE")

        if bgr_img is None or bgr_img.size == 0:
            raise ValueError("INVALID_IMAGE")

        faces = self._model.get(bgr_img)

        if len(faces) == 0:
            raise ValueError("FACE_NOT_DETECTED")

        # take first detected face
        embedding = faces[0].embedding.astype(np.float32)

        return embedding