import base64
import cv2
import numpy as np

def b64_to_bgr_image(b64_str: str) -> np.ndarray:
    if not b64_str or not isinstance(b64_str, str):
        raise ValueError("FACE_B64_MISSING")

    try:
        raw = base64.b64decode(b64_str)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("FACE_DECODE_FAILED")
        return img
    except Exception as e:
        raise ValueError(f"FACE_B64_INVALID: {e}")
