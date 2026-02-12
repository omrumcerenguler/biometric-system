from __future__ import annotations

from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.face_processor import FaceProcessor
from app.services.voice_processor import VoiceProcessor, VoiceFeatures
from app.services.face_liveness_state_machine import FaceLivenessStateMachine


class AuthenticationService:
    """
    Clean, stable service layer.

    Supports:
    - Face-only verification
    - Voice-only verification
    - Face + Voice fusion
    """

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session

        self.face = FaceProcessor()
        self.voice = VoiceProcessor()

        # 🔧 Thresholds (assignment-safe demo values)
        self.face_thr = 0.40
        self.voice_thr = 0.70
        self.fusion_thr = 0.45

        # 🔧 Liveness requirement
        self.require_face_liveness = True

        # Per-user liveness session
        self._face_sessions: dict[str, FaceLivenessStateMachine] = {}

    async def verify(
        self,
        username: str,
        face_img: Optional[np.ndarray],
        audio: Optional[np.ndarray],
        sr: Optional[int],
    ) -> dict:

        is_face = face_img is not None
        is_voice = audio is not None and sr is not None

        face_score = 0.0
        voice_score = 0.0
        face_liveness_passed = False
        face_liveness_step = None
        face_liveness_instruction = None

        # ======================
        # FACE
        # ======================
        if is_face:
            feats = self.face.extract_features(face_img)

            eye_avg = (feats.left_eye_open_norm + feats.right_eye_open_norm) / 2.0
            center_score = 1.0 - abs(feats.nose_x_norm - 0.5) * 2.0
            center_score = max(0.0, min(1.0, center_score))

            face_score = float(
                max(0.0, min(1.0, 0.6 * eye_avg + 0.4 * center_score))
            )

            # --- LIVENESS ---
            machine = self._face_sessions.get(username)
            if machine is None:
                machine = FaceLivenessStateMachine()
                self._face_sessions[username] = machine

            state = machine.update(
                nose_x=float(feats.nose_x_norm),
                eye_open_ratio=float(eye_avg),
                face_detected=True,
            )

            face_liveness_passed = bool(state.done and not state.failed)
            face_liveness_step = (
                machine.current_step().value
                if machine.current_step() is not None
                else None
            )
            face_liveness_instruction = machine.instruction()

        # ======================
        # VOICE
        # ======================
        if is_voice:
            voice_score = self._verify_voice(audio, sr)

        # ======================
        # FUSION
        # ======================
        used = 0
        total = 0.0

        if is_face:
            total += face_score
            used += 1
        if is_voice:
            total += voice_score
            used += 1

        fusion_score = total / used if used > 0 else 0.0

        # ======================
        # DECISION LOGIC
        # ======================
        if is_face and not is_voice:
            # Face only
            if self.require_face_liveness:
                decision = (
                    "GRANTED"
                    if (face_score >= self.face_thr and face_liveness_passed)
                    else "DENIED"
                )
            else:
                decision = (
                    "GRANTED"
                    if face_score >= self.face_thr
                    else "DENIED"
                )

        elif is_voice and not is_face:
            # Voice only
            decision = (
                "GRANTED"
                if voice_score >= self.voice_thr
                else "DENIED"
            )

        else:
            # Face + Voice
            if self.require_face_liveness:
                decision = (
                    "GRANTED"
                    if (fusion_score >= self.fusion_thr and face_liveness_passed)
                    else "DENIED"
                )
            else:
                decision = (
                    "GRANTED"
                    if fusion_score >= self.fusion_thr
                    else "DENIED"
                )

        # ======================
        # DEBUG REASON
        # ======================
        reason = (
            f"face={face_score:.2f} | "
            f"voice={voice_score:.2f} | "
            f"fusion={fusion_score:.2f} | "
            f"face_thr={self.face_thr:.2f} | "
            f"voice_thr={self.voice_thr:.2f} | "
            f"fusion_thr={self.fusion_thr:.2f} | "
            f"liveness_passed={str(face_liveness_passed).lower()}"
        )

        return {
            "decision": decision,
            "fusion_score": float(fusion_score),
            "face_score": float(face_score),
            "voice_score": float(voice_score),
            "reason": reason,
            "face_liveness_step": face_liveness_step,
            "face_liveness_instruction": face_liveness_instruction,
            "face_liveness_passed": face_liveness_passed,
        }

    # ======================
    # VOICE SCORING
    # ======================
    def _verify_voice(self, audio: np.ndarray, sr: int) -> float:
        feats: VoiceFeatures = self.voice.extract_features(audio, sr)

        rms_ok = 1.0 if feats.rms > 0.01 else 0.1
        flat_ok = 1.0 if 0.05 <= feats.spec_flatness <= 0.5 else 0.5
        zcr_ok = 1.0 if 0.02 <= feats.zcr <= 0.2 else 0.6

        score = 0.45 * rms_ok + 0.30 * flat_ok + 0.25 * zcr_ok
        return float(max(0.0, min(1.0, score)))

#yeni
def start_face_liveness(self, username: str):
    machine = FaceLivenessStateMachine()
    self._face_sessions[username] = machine
    return {
        "step": machine.current_step().value,
        "instruction": machine.instruction(),
    }


def update_face_liveness(self, username: str, face_img: np.ndarray) -> dict:
    feats = self.face.extract_features(face_img)

    eye_avg = (feats.left_eye_open_norm + feats.right_eye_open_norm) / 2.0

    machine = self._face_sessions.get(username)
    if machine is None:
        machine = FaceLivenessStateMachine()
        self._face_sessions[username] = machine

    prev_step = machine.current_step().value if machine.current_step() is not None else None

    state = machine.update(
        nose_x=float(feats.nose_x_norm),
        eye_open_ratio=float(eye_avg),
        face_detected=True,
    )

    cur_step = machine.current_step().value if machine.current_step() is not None else None

    passed_step = (prev_step != cur_step) or (state.done and not state.failed)

    return {
        "status": "PASSED" if (state.done and not state.failed) else ("FAILED" if state.failed else "IN_PROGRESS"),
        "step": cur_step,
        "instruction": machine.instruction(),
        "done": bool(state.done),
        "failed": bool(state.failed),
        "passed_step": bool(passed_step),
        "debug": {
            "nose_x": float(feats.nose_x_norm),
            "eye_open": float(eye_avg),
        },
    }
