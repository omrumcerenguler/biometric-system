# Takes raw facial/voice data and converts it into an authentication decision.

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, BiometricData
from app.services.eye_state_detector import EyeStateDetector
from app.services.face_processor import FaceProcessor
from app.services.voice_processor import VoiceProcessor, VoiceFeatures


class AuthenticationService:
    def __init__(self) -> None:
        self.face = FaceProcessor()
        self.eye_state = EyeStateDetector()
        self.voice = VoiceProcessor()

        # thresholds from config
        self.fusion_thr = settings.FUSION_PASS_THRESHOLD
        self.identification_thr = settings.FACE_IDENTIFICATION_THRESHOLD
        self.voice_ident_thr = settings.VOICE_IDENTIFICATION_THRESHOLD

    # =====================================================
    # Utils
    # =====================================================

    @staticmethod
    def _l2norm(vec: np.ndarray) -> np.ndarray:
        vec = np.asarray(vec, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(vec)
        if norm <= 1e-9:
            return vec
        return vec / norm

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        a = np.asarray(a, dtype=np.float32).reshape(-1)
        b = np.asarray(b, dtype=np.float32).reshape(-1)

        if a.size != b.size or a.size == 0:
            return 0.0

        denom = (np.linalg.norm(a) + 1e-8) * (np.linalg.norm(b) + 1e-8)
        return float(np.dot(a, b) / denom)

    # =====================================================
    # Portal Login
    # =====================================================

    async def login_user(
        self,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> dict:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return {
                "success": False,
                "message": "USER_NOT_FOUND",
            }

        if not user.is_active:
            return {
                "success": False,
                "message": "USER_INACTIVE",
            }

        if user.password_hash != password:
            return {
                "success": False,
                "message": "INVALID_PASSWORD",
            }

        return {
            "success": True,
            "message": "LOGIN_SUCCESS",
            "username": user.username,
            "role": user.role,
        }

    # ---------------- Face embedding ----------------

    def extract_face_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        try:
            vec = self.face.extract_embedding(face_img)
            if vec is None:
                return None

            vec = np.asarray(vec, dtype=np.float32).reshape(-1)
            if vec.size == 0:
                return None

            return self._l2norm(vec)
        except Exception:
            return None

    def extract_face_embedding_and_pose(self, face_img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[float]]:
        try:
            vec, nose_x_ratio = self.face.extract_embedding_and_pose(face_img)
            if vec is None:
                return None, None

            vec = np.asarray(vec, dtype=np.float32).reshape(-1)
            if vec.size == 0:
                return None, None

            return self._l2norm(vec), nose_x_ratio
        except Exception:
            return None, None

    # ---------------- Voice embedding ----------------

    def extract_voice_embedding(self, audio: np.ndarray, sr: int) -> Optional[np.ndarray]:
        try:
            vec = self.voice.extract_embedding(audio, sr)
            vec = np.asarray(vec, dtype=np.float32).reshape(-1)

            if vec.size == 0:
                return None

            return self._l2norm(vec)
        except Exception as exc:
            print(f"[VOICE_EMBEDDING_FAILED] {type(exc).__name__}: {exc}")
            return None

    # =====================================================
    # Enrollment - FACE
    # =====================================================

    async def enroll_user_with_template(
        self,
        session: AsyncSession,
        username: str,
        role: str,
        face_template: np.ndarray,
        n_samples: int,
    ) -> dict:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            return {"status": "FAILED", "reason": "USER_NOT_FOUND"}

        vec = self._l2norm(face_template)
        blob = vec.astype(np.float32).tobytes()

        result2 = await session.execute(
            select(BiometricData).where(
                BiometricData.user_id == user.user_id,
                BiometricData.type == "face_feature",
            )
        )
        existing = result2.scalar_one_or_none()

        if existing:
            old_vec = np.frombuffer(existing.enc_feature_blob, dtype=np.float32)
            old_vec = self._l2norm(old_vec)
            sim = self._cosine(vec, old_vec)

            if sim >= 0.95:
                await session.commit()
                return {
                    "status": "FACE_ALREADY_REGISTERED",
                    "similarity": float(sim),
                    "n_samples": int(n_samples),
                }

            existing.enc_feature_blob = blob
            await session.commit()
            return {
                "status": "FACE_UPDATED",
                "similarity": float(sim),
                "n_samples": int(n_samples),
            }

        session.add(
            BiometricData(
                type="face_feature",
                enc_feature_blob=blob,
                user_id=user.user_id,
            )
        )
        await session.commit()

        return {
            "status": "ENROLLED",
            "user_id": user.user_id,
            "n_samples": int(n_samples),
        }

    # =====================================================
    # Enrollment - VOICE
    # =====================================================

    async def enroll_voice(
        self,
        session: AsyncSession,
        username: str,
        role: str,
        audio: np.ndarray,
        sr: int,
    ) -> dict:
        v = self.extract_voice_embedding(audio, sr)
        if v is None:
            return {"status": "FAILED", "reason": "VOICE_EMBEDDING_FAILED"}

        return await self.save_voice_template_vector(
            session=session,
            username=username,
            voice_vec=v,
        )

    async def save_voice_template_vector(
        self,
        session: AsyncSession,
        username: str,
        voice_vec: np.ndarray,
        allow_low_similarity_update: bool = False,
    ) -> dict:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            return {"status": "FAILED", "reason": "USER_NOT_FOUND"}

        v = self._l2norm(np.asarray(voice_vec, dtype=np.float32).reshape(-1))
        if v.size == 0:
            return {"status": "FAILED", "reason": "VOICE_EMBEDDING_FAILED"}

        blob = v.astype(np.float32).tobytes()

        result2 = await session.execute(
            select(BiometricData).where(
                BiometricData.user_id == user.user_id,
                BiometricData.type == "voice_feature",
            )
        )
        existing = result2.scalar_one_or_none()

        if existing:
            old_v = np.frombuffer(existing.enc_feature_blob, dtype=np.float32)
            old_v = self._l2norm(old_v)
            sim = self._cosine(v, old_v)

            # Prevent hijacking an existing user's voice template with someone else.
            if sim < self.voice_ident_thr and not allow_low_similarity_update:
                return {
                    "status": "FAILED",
                    "reason": "VOICE_IDENTITY_MISMATCH",
                    "similarity": float(sim),
                    "user_id": user.user_id,
                }

            if sim >= 0.95:
                await session.commit()
                return {
                    "status": "VOICE_ALREADY_REGISTERED",
                    "similarity": float(sim),
                    "user_id": user.user_id,
                }

            existing.enc_feature_blob = blob
            await session.commit()
            return {
                "status": "VOICE_UPDATED",
                "similarity": float(sim),
                "user_id": user.user_id,
            }

        session.add(
            BiometricData(
                type="voice_feature",
                enc_feature_blob=blob,
                user_id=user.user_id,
            )
        )
        await session.commit()

        return {
            "status": "VOICE_ENROLLED",
            "user_id": user.user_id,
        }

    async def _get_user_voice_template(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Optional[np.ndarray]:
        result = await session.execute(
            select(BiometricData).where(
                BiometricData.user_id == user_id,
                BiometricData.type == "voice_feature",
            )
        )
        bio = result.scalar_one_or_none()

        if not bio or not bio.enc_feature_blob:
            return None

        vec = np.frombuffer(bio.enc_feature_blob, dtype=np.float32)
        if vec.size == 0:
            return None

        return self._l2norm(vec)

    # =====================================================
    # Identification (1:N) - FACE
    # =====================================================

    async def identify_face(self, session: AsyncSession, face_img: np.ndarray) -> dict:
        query_vec, nose_x_ratio = self.extract_face_embedding_and_pose(face_img)
        if query_vec is None:
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "NO_FACE_DETECTED",
            }

        # First capture must be frontal enough to reduce side-pose false positives.
        if nose_x_ratio is None or nose_x_ratio < 0.44 or nose_x_ratio > 0.56:
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "FACE_NOT_FRONTAL",
            }

        eyes_open, _eye_state = self.eye_state.are_eyes_open(face_img)
        if eyes_open is False:
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "EYES_CLOSED",
            }
        if eyes_open is None:
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "EYES_NOT_CLEAR",
            }

        result = await session.execute(
            select(User, BiometricData)
            .join(BiometricData)
            .where(BiometricData.type == "face_feature")
        )

        best_score = -1.0
        best_user = None

        for user, bio in result.all():
            db_vec = np.frombuffer(bio.enc_feature_blob, dtype=np.float32)
            db_vec = self._l2norm(db_vec)

            sim = self._cosine(query_vec, db_vec)
            if sim > best_score:
                best_score = sim
                best_user = user

        if best_user and best_score >= self.identification_thr:
            return {
                "identified": True,
                "user_id": best_user.user_id,
                "username": best_user.username,
                "similarity": float(best_score),
                "reason": "IDENTIFIED",
            }

        return {
            "identified": False,
            "similarity": float(max(best_score, 0.0)),
            "reason": "NO_MATCH",
        }

    async def identify_user(self, session: AsyncSession, face_img: np.ndarray) -> dict:
        return await self.identify_face(session=session, face_img=face_img)

    # =====================================================
    # Verify (Fusion) - FACE + VOICE
    # =====================================================

    async def verify(
        self,
        session: AsyncSession,
        face_img: Optional[np.ndarray],
        audio: Optional[np.ndarray],
        sr: Optional[int],
    ) -> dict:
        if face_img is None:
            return {
                "decision": "DENIED",
                "reason": "FACE_REQUIRED",
                "identified_user": None,
                "fusion_score": 0.0,
                "face_score": 0.0,
                "voice_score": 0.0,
            }

        id_result = await self.identify_face(session, face_img)
        face_score = float(id_result.get("similarity", 0.0))

        if not id_result.get("identified"):
            return {
                "decision": "DENIED",
                "reason": "FACE_NOT_IDENTIFIED",
                "identified_user": None,
                "fusion_score": float(face_score),
                "face_score": float(face_score),
                "voice_score": 0.0,
            }

        user_id = int(id_result["user_id"])
        username = str(id_result["username"])

        if audio is None or sr is None:
            return {
                "decision": "DENIED",
                "reason": "VOICE_REQUIRED",
                "identified_user": username,
                "fusion_score": float(face_score),
                "face_score": float(face_score),
                "voice_score": 0.0,
            }

        probe_v = self.extract_voice_embedding(audio, sr)
        if probe_v is None:
            return {
                "decision": "DENIED",
                "reason": "VOICE_EMBEDDING_FAILED",
                "identified_user": username,
                "fusion_score": float(face_score),
                "face_score": float(face_score),
                "voice_score": 0.0,
            }

        tmpl_v = await self._get_user_voice_template(session, user_id=user_id)
        if tmpl_v is None:
            return {
                "decision": "DENIED",
                "reason": "VOICE_NOT_ENROLLED",
                "identified_user": username,
                "fusion_score": float(face_score),
                "face_score": float(face_score),
                "voice_score": 0.0,
            }

        voice_score = float(self._cosine(probe_v, tmpl_v))

        if voice_score < self.voice_ident_thr:
            fusion_score = float((face_score + voice_score) / 2.0)
            return {
                "decision": "DENIED",
                "reason": "VOICE_NOT_MATCHED",
                "identified_user": username,
                "fusion_score": fusion_score,
                "face_score": float(face_score),
                "voice_score": float(voice_score),
            }

        fusion_score = float((face_score + voice_score) / 2.0)
        decision = "ACCEPTED" if fusion_score >= self.fusion_thr else "DENIED"
        reason = "OK" if decision == "ACCEPTED" else "FUSION_THRESHOLD"

        return {
            "decision": decision,
            "reason": reason,
            "identified_user": username,
            "fusion_score": fusion_score,
            "face_score": float(face_score),
            "voice_score": float(voice_score),
        }

    # =====================================================
    # Optional: Voice liveness-ish scoring
    # =====================================================

    def voice_liveness_score(self, audio: np.ndarray, sr: int) -> float:
        feats: VoiceFeatures = self.voice.extract_features(audio, sr)

        rms_ok = 1.0 if feats.rms > 0.01 else 0.1
        flat_ok = 1.0 if 0.05 <= feats.spec_flatness <= 0.5 else 0.5
        zcr_ok = 1.0 if 0.02 <= feats.zcr <= 0.2 else 0.6

        score = 0.45 * rms_ok + 0.30 * flat_ok + 0.25 * zcr_ok
        return float(max(0.0, min(1.0, score)))