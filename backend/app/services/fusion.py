def fuse(face_score: float, voice_score: float, w_face: float = 0.55, w_voice: float = 0.45) -> float:
    """
    Weighted fusion of face and voice liveness scores.

    Args:
        face_score (float): [0,1]
        voice_score (float): [0,1]
        w_face (float): weight for face modality
        w_voice (float): weight for voice modality

    Returns:
        float: fused score in [0,1]
    """
    if not (0.0 <= face_score <= 1.0):
        raise ValueError("face_score must be between 0 and 1")
    if not (0.0 <= voice_score <= 1.0):
        raise ValueError("voice_score must be between 0 and 1")

    return (w_face * face_score) + (w_voice * voice_score)
