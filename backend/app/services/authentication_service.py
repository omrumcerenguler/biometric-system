from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from sqlalchemy import select
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, BiometricData
from app.services.eye_state_detector import EyeStateDetector
from app.services.face_processor import FaceProcessor
from app.services.fusion import fuse
from app.services.voice_processor import VoiceProcessor, VoiceFeatures


FACE_TEMPLATE_TYPE_BY_POSE = {
    "center": "face_feature_center",
    "left": "face_feature_left",
    "right": "face_feature_right",
}
LEGACY_FACE_TEMPLATE_TYPE = "face_feature"


class AuthenticationService:

    def count_faces(self, face_img: np.ndarray) -> Optional[int]:
        try:
            return int(self.face.count_faces(face_img))
        except Exception:
            return None

    def __init__(self) -> None:
        self.face = FaceProcessor()
        self.eye_state = EyeStateDetector()
        self.voice = VoiceProcessor()

        self.fusion_thr = settings.FUSION_PASS_THRESHOLD
        self.identification_thr = settings.FACE_IDENTIFICATION_THRESHOLD
        self.voice_ident_thr = settings.VOICE_IDENTIFICATION_THRESHOLD
        self.voice_template_update_thr = settings.VOICE_TEMPLATE_UPDATE_THRESHOLD

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

    def bucket_pose_from_nose_ratio(self, nose_x_ratio: Optional[float]) -> Optional[str]:
        if nose_x_ratio is None:
            return None
        if nose_x_ratio < 0.44:
            return "left"
        if nose_x_ratio > 0.56:
            return "right"
        return "center"

    async def _get_user_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def _get_biometric_row(
        self,
        session: AsyncSession,
        user_id: int,
        bio_type: str,
    ) -> Optional[BiometricData]:
        result = await session.execute(
            select(BiometricData).where(
                BiometricData.user_id == user_id,
                BiometricData.type == bio_type,
            )
        )
        return result.scalar_one_or_none()

    # =====================================================
    # Portal Login
    # =====================================================

    async def login_user(
        self,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> dict:
        user = await self._get_user_by_username(session, username)

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

    # =====================================================
    # Face Embedding / Pose
    # =====================================================

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

    def extract_face_embedding_and_pose(
        self,
        face_img: np.ndarray,
    ):
        """
        embedding, nose_x_ratio, yaw, pitch, bbox_size, blur_score
        """
        """
        embedding, nose_x_ratio, yaw, bbox_size, blur_score
        """
        try:
            result = self.face.extract_embedding_and_pose(face_img)
            if result is None or len(result) < 5:
                return (None,) * 5
            embedding, nose_x_ratio, yaw, bbox_size, blur_score = result
            if embedding is None or np.asarray(embedding).size == 0:
                return (None,) * 5
            embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
            return self._l2norm(embedding), nose_x_ratio, yaw, bbox_size, blur_score
        except Exception:
            return (None,) * 5
            return int(self.face.count_faces(face_img))
        except Exception:
            return None

    # =====================================================
    # Voice Embedding
    # =====================================================

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
    # Enrollment Helpers
    # =====================================================

    async def _upsert_biometric_vector(
        self,
        session: AsyncSession,
        user_id: int,
        bio_type: str,
        vec: np.ndarray,
    ) -> None:
        blob = self._l2norm(vec).astype(np.float32).tobytes()
        existing = await self._get_biometric_row(session, user_id, bio_type)

        if existing:
            existing.enc_feature_blob = blob
            return

        session.add(
            BiometricData(
                type=bio_type,
                enc_feature_blob=blob,
                user_id=user_id,
            )
        )

    # =====================================================
    # Enrollment - FACE (Pose-Aware)
    # =====================================================

    async def enroll_user_with_pose_templates(
        self,
        session: AsyncSession,
        username: str,
        role: str,
        pose_templates: dict[str, np.ndarray],
        n_samples_by_pose: dict[str, int],
    ) -> dict:
        logging.warning("[ENROLL_FACE] fonksiyonuna girildi.")
        user = await self._get_user_by_username(session, username)

        if user is None:
            return {"status": "FAILED", "reason": "USER_NOT_FOUND"}

        # Başka kullanıcıya ait yüz kontrolü
        for pose, vec in pose_templates.items():
            if vec is None:
                continue

            normalized_vec = self._l2norm(vec)

            if pose == "center":
                bio_types = [LEGACY_FACE_TEMPLATE_TYPE, FACE_TEMPLATE_TYPE_BY_POSE[pose]]
            else:
                bio_types = [FACE_TEMPLATE_TYPE_BY_POSE[pose]]

            result_all = await session.execute(
                select(BiometricData, User)
                .join(User, BiometricData.user_id == User.user_id)
                .where(
                    BiometricData.type.in_(bio_types),
                    BiometricData.user_id != user.user_id,
                )
            )

            for other_face, other_user in result_all.all():
                other_vec = np.frombuffer(other_face.enc_feature_blob, dtype=np.float32)
                other_vec = self._l2norm(other_vec)
                sim = self._cosine(normalized_vec, other_vec)
                logging.warning(f"[FACE_SIM] pose={pose}, user={other_user.username}, sim={sim:.4f}")

                if sim >= 0.80:
                    logging.warning(f"[FACE_MATCH] pose={pose}, user={other_user.username}, sim={sim:.4f} (eşik aşıldı)")
                    return {
                        "status": "FACE_ALREADY_REGISTERED_OTHER_USER",
                        "reason": f"This face is already registered to user: {other_user.username}",
                        "similarity": float(sim),
                        "other_user_id": other_user.user_id,
                        "other_username": other_user.username,
                        "pose": pose,
                    }

        saved_poses: list[str] = []

        for pose, bio_type in FACE_TEMPLATE_TYPE_BY_POSE.items():
            vec = pose_templates.get(pose)
            if vec is None:
                continue

            await self._upsert_biometric_vector(
                session=session,
                user_id=user.user_id,
                bio_type=bio_type,
                vec=vec,
            )
            saved_poses.append(pose)

        # backward compatibility
        legacy_center = pose_templates.get("center")
        if legacy_center is not None:
            await self._upsert_biometric_vector(
                session=session,
                user_id=user.user_id,
                bio_type=LEGACY_FACE_TEMPLATE_TYPE,
                vec=legacy_center,
            )

        return {
            "status": "ENROLLED",
            "user_id": user.user_id,
            "saved_poses": saved_poses,
            "samples_by_pose": {
                "center": int(n_samples_by_pose.get("center", 0)),
                "left": int(n_samples_by_pose.get("left", 0)),
                "right": int(n_samples_by_pose.get("right", 0)),
            },
        }

    async def enroll_user_with_template(
        self,
        session: AsyncSession,
        username: str,
        role: str,
        face_template: np.ndarray,
        n_samples: int,
    ) -> dict:
        user = await self._get_user_by_username(session, username)

        if user is None:
            return {"status": "FAILED", "reason": "USER_NOT_FOUND"}

        vec = self._l2norm(face_template)
        blob = vec.astype(np.float32).tobytes()

        # Başka kullanıcıya ait generic yüz kontrolü
        result_all = await session.execute(
            select(BiometricData, User)
            .join(User, BiometricData.user_id == User.user_id)
            .where(
                BiometricData.type == LEGACY_FACE_TEMPLATE_TYPE,
                BiometricData.user_id != user.user_id,
            )
        )

        for other_face, other_user in result_all.all():
            other_vec = np.frombuffer(other_face.enc_feature_blob, dtype=np.float32)
            other_vec = self._l2norm(other_vec)
            sim = self._cosine(vec, other_vec)

            if sim >= 0.95:
                return {
                    "status": "FACE_ALREADY_REGISTERED_OTHER_USER",
                    "reason": f"This face is already registered to user: {other_user.username}",
                    "similarity": float(sim),
                    "other_user_id": other_user.user_id,
                    "other_username": other_user.username,
                    "n_samples": int(n_samples),
                }

        existing = await self._get_biometric_row(session, user.user_id, LEGACY_FACE_TEMPLATE_TYPE)

        if existing:
            old_vec = np.frombuffer(existing.enc_feature_blob, dtype=np.float32)
            old_vec = self._l2norm(old_vec)
            sim = self._cosine(vec, old_vec)

            if sim >= 0.95:
                return {
                    "status": "FACE_ALREADY_REGISTERED",
                    "similarity": float(sim),
                    "n_samples": int(n_samples),
                }

            existing.enc_feature_blob = blob
            return {
                "status": "FACE_UPDATED",
                "similarity": float(sim),
                "n_samples": int(n_samples),
            }

        session.add(
            BiometricData(
                type=LEGACY_FACE_TEMPLATE_TYPE,
                enc_feature_blob=blob,
                user_id=user.user_id,
            )
        )

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
        user = await self._get_user_by_username(session, username)

        if user is None:
            return {"status": "FAILED", "reason": "USER_NOT_FOUND"}

        v = self._l2norm(np.asarray(voice_vec, dtype=np.float32).reshape(-1))
        if v.size == 0:
            return {"status": "FAILED", "reason": "VOICE_EMBEDDING_FAILED"}

        blob = v.astype(np.float32).tobytes()

        # Başka kullanıcıya ait ses kontrolü
        result_all = await session.execute(
            select(BiometricData, User)
            .join(User, BiometricData.user_id == User.user_id)
            .where(
                BiometricData.type == "voice_feature",
                BiometricData.user_id != user.user_id,
            )
        )

        for other_voice, other_user in result_all.all():
            other_vec = np.frombuffer(other_voice.enc_feature_blob, dtype=np.float32)
            other_vec = self._l2norm(other_vec)
            sim = self._cosine(v, other_vec)

            if sim >= 0.80:
                return {
                    "status": "VOICE_ALREADY_REGISTERED_OTHER_USER",
                    "reason": "This voice is already registered to another user.",
                    "similarity": float(sim),
                    "other_user_id": other_user.user_id,
                    "other_username": other_user.username,
                }

        existing = await self._get_biometric_row(session, user.user_id, "voice_feature")

        if existing:
            old_v = np.frombuffer(existing.enc_feature_blob, dtype=np.float32)
            old_v = self._l2norm(old_v)
            sim = self._cosine(v, old_v)

            if sim < self.voice_template_update_thr and not allow_low_similarity_update:
                return {
                    "status": "FAILED",
                    "reason": "VOICE_IDENTITY_MISMATCH",
                    "similarity": float(sim),
                    "user_id": user.user_id,
                }

            if sim >= 0.95:
                return {
                    "status": "VOICE_ALREADY_REGISTERED",
                    "similarity": float(sim),
                    "user_id": user.user_id,
                }

            existing.enc_feature_blob = blob
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

        return {
            "status": "VOICE_ENROLLED",
            "user_id": user.user_id,
        }

    # =====================================================
    # Read Templates
    # =====================================================

    async def _get_user_voice_template(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Optional[np.ndarray]:
        bio = await self._get_biometric_row(session, user_id, "voice_feature")

        if not bio or not bio.enc_feature_blob:
            return None

        vec = np.frombuffer(bio.enc_feature_blob, dtype=np.float32)
        if vec.size == 0:
            return None

        return self._l2norm(vec)

    async def _get_user_face_template(
        self,
        session: AsyncSession,
        user_id: int,
        pose: str = "center",
    ) -> Optional[np.ndarray]:
        pose_key = (pose or "center").strip().lower()
        type_candidates: list[str] = []

        if pose_key in FACE_TEMPLATE_TYPE_BY_POSE:
            type_candidates.append(FACE_TEMPLATE_TYPE_BY_POSE[pose_key])

        if pose_key == "center":
            type_candidates.append(LEGACY_FACE_TEMPLATE_TYPE)

        if not type_candidates:
            type_candidates = [LEGACY_FACE_TEMPLATE_TYPE]

        for bio_type in type_candidates:
            bio = await self._get_biometric_row(session, user_id, bio_type)

            if not bio or not bio.enc_feature_blob:
                continue

            vec = np.frombuffer(bio.enc_feature_blob, dtype=np.float32)
            if vec.size == 0:
                continue

            return self._l2norm(vec)

        return None

    async def _get_best_face_template_for_identification(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Optional[np.ndarray]:
        result = await session.execute(
            select(BiometricData).where(
                BiometricData.user_id == user_id,
                BiometricData.type.in_(
                    [FACE_TEMPLATE_TYPE_BY_POSE["center"], LEGACY_FACE_TEMPLATE_TYPE]
                ),
            )
        )
        rows = result.scalars().all()

        if not rows:
            return None

        by_type = {row.type: row for row in rows}
        preferred = (
            by_type.get(FACE_TEMPLATE_TYPE_BY_POSE["center"])
            or by_type.get(LEGACY_FACE_TEMPLATE_TYPE)
        )

        if not preferred or not preferred.enc_feature_blob:
            return None

        vec = np.frombuffer(preferred.enc_feature_blob, dtype=np.float32)
        if vec.size == 0:
            return None

        return self._l2norm(vec)

    # =====================================================
    # Identification (1:N) - FACE
    # =====================================================

    async def identify_face(self, session: AsyncSession, face_img: np.ndarray) -> dict:

        # Debug değişkenleri
        debug = {
            "yaw": None,
            "blur_score": None,
            "bbox_size": None,
            "nose_x_ratio": None,
            "debug_step": None,
        }

        # 1. Tek yüz var mı?
        face_count = self.count_faces(face_img)
        if face_count is not None and face_count > 1:
            debug["debug_step"] = "multiple_faces"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "MULTIPLE_FACES_DETECTED",
                **debug,
            }

        # 2. Embedding ve tüm pose/kalite çıktıları
        query_vec, nose_x_ratio, yaw, bbox_size, blur_score = self.extract_face_embedding_and_pose(face_img)
        debug.update({
            "yaw": yaw,
            "blur_score": blur_score,
            "bbox_size": bbox_size,
            "nose_x_ratio": nose_x_ratio,
        })
        if query_vec is None:
            debug["debug_step"] = "embedding_failed"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "NO_FACE_DETECTED",
                **debug,
            }

        # 3. Head pose: yaw aralıkta mı?
        if yaw is None or abs(yaw) > 0.25:  # gevşetildi: ~14 derece
            debug["debug_step"] = "yaw_out_of_range"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "FACE_YAW_OUT_OF_RANGE",
                **debug,
            }

        # 4. Nose_x_ratio ortada mı? (yardımcı)
        if nose_x_ratio is None or nose_x_ratio < 0.44 or nose_x_ratio > 0.56:
            debug["debug_step"] = "not_frontal"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "FACE_NOT_FRONTAL",
                **debug,
            }

        # 5. Gözler açık ve net mi?
        eyes_open, _eye_state = self.eye_state.are_eyes_open(face_img)
        if eyes_open is False:
            debug["debug_step"] = "eyes_closed"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "EYES_CLOSED",
                **debug,
            }
        if eyes_open is None:
            debug["debug_step"] = "eyes_not_clear"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "EYES_NOT_CLEAR",
                **debug,
            }

        # 6. Yüz yeterince büyük mü? (bbox_size yüksek olmalı, örneğin %4'ten küçükse çok uzak)
        if bbox_size is None or bbox_size < 0.04:  # örnek: %4'ten küçükse çok uzak
            debug["debug_step"] = "bbox_too_small"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "FACE_TOO_SMALL",
                **debug,
            }

        # 7. Yüz net mi? (blur score yüksek olmalı)
        if blur_score is None or blur_score < 18.0:  # örnek eşik: 18
            debug["debug_step"] = "face_blurry"
            return {
                "identified": False,
                "similarity": 0.0,
                "reason": "FACE_BLURRY",
                **debug,
            }

        # 8. Eşleşme
        best_score = -1.0
        best_user = None

        user_result = await session.execute(select(User))
        for user in user_result.scalars().all():
            db_vec = await self._get_best_face_template_for_identification(
                session=session,
                user_id=user.user_id,
            )
            if db_vec is None:
                continue

            sim = self._cosine(query_vec, db_vec)
            if sim > best_score:
                best_score = sim
                best_user = user

        if best_user and best_score >= self.identification_thr:
            debug["debug_step"] = "matched"
            return {
                "identified": True,
                "user_id": best_user.user_id,
                "username": best_user.username,
                "similarity": float(best_score),
                "reason": "IDENTIFIED",
                **debug,
            }

        debug["debug_step"] = "no_match"
        return {
            "identified": False,
            "similarity": float(max(best_score, 0.0)),
            "reason": "NO_MATCH",
            **debug,
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
            fusion_score = float(fuse(face_score=face_score, voice_score=voice_score))
            return {
                "decision": "DENIED",
                "reason": "VOICE_NOT_MATCHED",
                "identified_user": username,
                "fusion_score": fusion_score,
                "face_score": float(face_score),
                "voice_score": float(voice_score),
            }

        fusion_score = float(fuse(face_score=face_score, voice_score=voice_score))
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