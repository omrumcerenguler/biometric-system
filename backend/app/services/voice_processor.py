from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import librosa
import numpy as np


@dataclass(frozen=True)
class VoiceFeatures:
    """
    Compact audio features for liveness / anti-spoof heuristics.

    Notes:
    - All features are simple and fast to compute.
    - Designed for downstream scoring (0..1) in LivenessDetector.
    """
    rms: float
    zcr: float
    spec_flatness: float
    mfcc_mean: float


class VoiceProcessor:
    """
    Voice feature extractor.

    Pro-level decisions:
    - Expects mono waveform as float32/float64 numpy array.
    - Performs basic validation and safe normalization.
    - Keeps parameters (n_mfcc) configurable and explicit.
    """

    DEFAULT_N_MFCC: Final[int] = 13
    EPS: Final[float] = 1e-12

    def __init__(self, n_mfcc: int = DEFAULT_N_MFCC) -> None:
        self._n_mfcc = int(n_mfcc)

    def extract_features(self, audio: np.ndarray, sr: int) -> VoiceFeatures:
        """
        Extract audio features from a mono waveform.

        Args:
            audio: 1-D numpy array (mono). Prefer float32 in [-1, 1].
            sr: sampling rate (e.g., 16000)

        Returns:
            VoiceFeatures

        Raises:
            ValueError: if input audio/sr is invalid or too short.
        """
        if audio is None or not isinstance(audio, np.ndarray) or audio.size == 0:
            raise ValueError("INVALID_AUDIO")

        if audio.ndim != 1:
            raise ValueError("AUDIO_NOT_MONO")

        sr = int(sr)
        if sr <= 0:
            raise ValueError("INVALID_SAMPLE_RATE")

        # Very short audio can break some spectral features; require a minimum duration (~0.2s)
        min_samples = int(0.2 * sr)
        if audio.size < min_samples:
            raise ValueError("AUDIO_TOO_SHORT")

        # Ensure finite values
        if not np.isfinite(audio).all():
            raise ValueError("AUDIO_NOT_FINITE")

        # Convert to float32 for consistent librosa behavior
        audio = audio.astype(np.float32, copy=False)

        # Safe normalization (avoid divide-by-zero)
        peak = float(np.max(np.abs(audio)))
        if peak > self.EPS:
            audio = audio / peak

        # Feature extraction
        # rms: energy; zcr: rough noisiness; flatness: tone vs noise; mfcc_mean: coarse timbre indicator
        rms = float(np.mean(librosa.feature.rms(y=audio)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=audio)))
        flat = float(np.mean(librosa.feature.spectral_flatness(y=audio)))

        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=self._n_mfcc)
        mfcc_mean = float(np.mean(mfcc))

        return VoiceFeatures(
            rms=rms,
            zcr=zcr,
            spec_flatness=flat,
            mfcc_mean=mfcc_mean,
        )
