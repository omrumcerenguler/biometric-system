import pytest
from app.services.fusion import fuse


def test_fusion_basic():
    score = fuse(face_score=0.8, voice_score=0.6)
    assert 0.0 <= score <= 1.0
    assert round(score, 3) == round(0.55 * 0.8 + 0.45 * 0.6, 3)


def test_fusion_all_zero():
    assert fuse(0.0, 0.0) == 0.0


def test_fusion_all_one():
    assert fuse(1.0, 1.0) == 1.0


def test_fusion_invalid_face_score():
    with pytest.raises(ValueError):
        fuse(face_score=1.5, voice_score=0.5)


def test_fusion_invalid_voice_score():
    with pytest.raises(ValueError):
        fuse(face_score=0.5, voice_score=-0.2)
