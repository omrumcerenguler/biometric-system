from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import librosa
import numpy as np


@dataclass(frozen=True)
class VoiceFeatures:
    rms: float
    zcr: float
    spec_flatness: float
    mfcc_mean: float


class VoiceProcessor:
    DEFAULT_N_MFCC: Final[int] = 13
    TARGET_SR: Final[int] = 16000
    EPS: Final[float] = 1e-12

    def __init__(self, n_mfcc: int = DEFAULT_N_MFCC) -> None:
        self._n_mfcc = int(n_mfcc)

    # -------------------------
    # Shared preprocessing
    # -------------------------
    def _validate_and_preprocess(self, audio: np.ndarray, sr: int, min_seconds: float) -> tuple[np.ndarray, int]:
        if audio is None or not isinstance(audio, np.ndarray) or audio.size == 0:
            raise ValueError("INVALID_AUDIO")
        if audio.ndim != 1:
            raise ValueError("AUDIO_NOT_MONO")

        sr = int(sr)
        if sr <= 0:
            raise ValueError("INVALID_SAMPLE_RATE")

        if not np.isfinite(audio).all():
            raise ValueError("AUDIO_NOT_FINITE")

        audio = audio.astype(np.float32, copy=False)

        # Resample to stable SR
        if sr != self.TARGET_SR:
            audio = librosa.resample(y=audio, orig_sr=sr, target_sr=self.TARGET_SR)
            sr = self.TARGET_SR

        min_samples = int(min_seconds * sr)
        if audio.size < min_samples:
            raise ValueError("AUDIO_TOO_SHORT")

        # Peak normalize (safe)
        peak = float(np.max(np.abs(audio)))
        if peak > self.EPS:
            audio = audio / peak

        return audio, sr

    # -------------------------
    # Liveness-ish features (heuristics)
    # -------------------------
    def extract_features(self, audio: np.ndarray, sr: int) -> VoiceFeatures:
        audio, sr = self._validate_and_preprocess(audio, sr, min_seconds=0.2)

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

    # -------------------------
    # Identity embedding (voiceprint)
    # -------------------------
    def extract_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        V1 Voiceprint embedding (MFCC + delta MFCC stats pooling).

        Output:
            1-D float32 vector with fixed size:
            - mfcc mean (n_mfcc)
            - mfcc std  (n_mfcc)
            - delta mean (n_mfcc)
            - delta std  (n_mfcc)
            => total = 4 * n_mfcc
        """
        audio, sr = self._validate_and_preprocess(audio, sr, min_seconds=2.0)

        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=self._n_mfcc)  # (n_mfcc, T)
        d_mfcc = librosa.feature.delta(mfcc)  # (n_mfcc, T)

        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)
        d_mean = np.mean(d_mfcc, axis=1)
        d_std = np.std(d_mfcc, axis=1)

        emb = np.concatenate([mfcc_mean, mfcc_std, d_mean, d_std], axis=0).astype(np.float32)
        return emb