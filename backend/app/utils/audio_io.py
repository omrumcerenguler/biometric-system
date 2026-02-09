import base64
import io
import soundfile as sf
import numpy as np

def b64_to_wav_mono(b64_str: str):
    if not b64_str or not isinstance(b64_str, str):
        raise ValueError("VOICE_B64_MISSING")

    try:
        raw = base64.b64decode(b64_str)
    except Exception as e:
        raise ValueError(f"VOICE_B64_INVALID: {e}")

    try:
        data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    except Exception as e:
        raise ValueError(f"VOICE_FORMAT_UNSUPPORTED: {e}")

    # stereo -> mono
    if isinstance(data, np.ndarray) and data.ndim == 2:
        data = data.mean(axis=1)

    return data, sr
