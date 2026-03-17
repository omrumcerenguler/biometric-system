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

    def count_faces(self, bgr_img: np.ndarray) -> int:
        if self._model is None:
            raise ValueError("FACE_PROCESSOR_UNAVAILABLE")

        if bgr_img is None or bgr_img.size == 0:
            raise ValueError("INVALID_IMAGE")

        faces = self._model.get(bgr_img)
        return len(faces)

    def extract_embedding(self, bgr_img: np.ndarray) -> np.ndarray:
        embedding, nose_x_ratio, yaw, bbox_size, blur_score = self.extract_embedding_and_pose(bgr_img)
        return embedding


    def extract_embedding_and_pose(self, bgr_img: np.ndarray):
        """
        Returns:
            embedding: np.ndarray
            nose_x_ratio: float | None
            yaw: float | None
            bbox_size: float | None (yüzün görüntüdeki oranı)
            blur_score: float | None (yüksekse net, düşükse bulanık)
        """
        if self._model is None:
            raise ValueError("FACE_PROCESSOR_UNAVAILABLE")

        if bgr_img is None or bgr_img.size == 0:
            raise ValueError("INVALID_IMAGE")

        faces = self._model.get(bgr_img)
        if len(faces) == 0:
            raise ValueError("FACE_NOT_DETECTED")

        face = faces[0]
        embedding = face.embedding.astype(np.float32)
        nose_x_ratio = self._estimate_nose_x_ratio(face)

        # Head pose (yaw) tahmini (landmarklardan basit yaklaşım)
        yaw = self._estimate_head_pose(face)

        # Bounding box oranı (yüzün görüntüdeki alanı)
        bbox_size = self._estimate_bbox_size(face, bgr_img)

        # Blur (bulanıklık) ölçümü
        blur_score = self._estimate_blur_score(bgr_img, face)

        return embedding, nose_x_ratio, yaw, bbox_size, blur_score

    def _estimate_head_pose(self, face) -> float | None:
        """
        Basit head pose tahmini: yaw (sağa/sola dönüş)
        """
        kps = getattr(face, "kps", None)
        if kps is None or len(kps) < 5:
            return None
        pts = np.asarray(kps, dtype=np.float32)
        left_eye = pts[0]
        right_eye = pts[1]
        nose = pts[2]
        # Yaw: gözler arası yatay fark ile burun
        eye_dx = right_eye[0] - left_eye[0]
        nose_dx = nose[0] - (left_eye[0] + right_eye[0]) / 2
        yaw = nose_dx / (eye_dx + 1e-6)
        return float(yaw)

    def _estimate_bbox_size(self, face, bgr_img) -> float | None:
        bbox = getattr(face, "bbox", None)
        if bbox is None or len(bbox) != 4:
            return None
        x1, y1, x2, y2 = bbox
        face_area = max(0, (x2 - x1)) * max(0, (y2 - y1))
        img_area = bgr_img.shape[0] * bgr_img.shape[1]
        if img_area == 0:
            return None
        return float(face_area) / float(img_area)

    def _estimate_blur_score(self, bgr_img, face) -> float | None:
        bbox = getattr(face, "bbox", None)
        if bbox is None or len(bbox) != 4:
            return None
        x1, y1, x2, y2 = [int(v) for v in bbox]
        face_crop = bgr_img[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if face_crop.size == 0:
            return None
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(laplacian_var)

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