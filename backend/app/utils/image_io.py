import base64
import cv2
import numpy as np


def b64_to_bgr_image(face_b64: str) -> np.ndarray:
    """
    Accepts:
      - raw base64 (no prefix)
      - data-url base64: 'data:image/jpeg;base64,...'
    Returns:
      - OpenCV BGR image (np.ndarray)
    """
    if "," in face_b64 and face_b64.strip().lower().startswith("data:"):
        face_b64 = face_b64.split(",", 1)[1]

    raw = base64.b64decode(face_b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cv2.imdecode returned None")
    return img
