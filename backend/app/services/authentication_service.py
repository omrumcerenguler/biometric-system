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

    Liveness is handled via:
    - start_face_liveness()
    - update_face_liveness()

    Final verify() does NOT advance liveness; it only checks whether
    liveness has already passed for this user (if required).
    """

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session

        self.face = FaceProcessor()
        self.voice = VoiceProcessor()

        # Thresholds
        self.face_thr = 0.40
        self.voice_thr = 0.70
        self.fusion_thr = 0.45

        # Liveness requirement
        self.require_face_liveness = True

        # Per-user liveness session
        self._face_sessions: dict[str, FaceLivenessStateMachine] = {}

    # ======================
    # LIVENESS (START/UPDATE)
    # ======================
    def start_face_liveness(self, username: str) -> dict:
        machine = FaceLivenessStateMachine()
        self._face_sessions[username] = machine
        step = machine.current_step().value if machine.current_step() is not None else None
        return {
            "step": step,
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

        status = (
            "PASSED"
            if (state.done and not state.failed)
            else ("FAILED" if state.failed else "IN_PROGRESS")
        )

        return {
            "status": status,
            "step": cur_step,
            "instruction": "Liveness passed." if status == "PASSED" else machine.instruction(),
            "done": bool(state.done),
            "failed": bool(state.failed),
            "passed_step": bool(passed_step),
            "debug": {
                "nose_x": float(feats.nose_x_norm),
                "eye_open": float(eye_avg),
            },
        }
    
    def is_liveness_passed(self, username: str) -> bool:
        machine = self._face_sessions.get(username)
        if machine is None:
            return False
        st = machine.state
        return bool(st.done and not st.failed)


    def _is_face_liveness_passed(self, username: str) -> bool:
        machine = self._face_sessions.get(username)
        if machine is None:
            return False

        # state = machine.update(...) returns a state object, but we don't store it.
        # So we infer pass from machine's internal state if it exists.
        # If your FaceLivenessStateMachine does not keep state internally,
        # then we must store last state per user in this service.
        internal_state = getattr(machine, "state", None)
        if internal_state is None:
            return False

        return bool(internal_state.done and not internal_state.failed)

    # ======================
    # FINAL VERIFY
    # ======================
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

        # ----------------------
        # FACE SCORE (no liveness update here)
        # ----------------------
        if is_face:
            feats = self.face.extract_features(face_img)

            eye_avg = (feats.left_eye_open_norm + feats.right_eye_open_norm) / 2.0
            center_score = 1.0 - abs(feats.nose_x_norm - 0.5) * 2.0
            center_score = max(0.0, min(1.0, center_score))

            face_score = float(max(0.0, min(1.0, 0.6 * eye_avg + 0.4 * center_score)))

        # ----------------------
        # VOICE SCORE
        # ----------------------
        if is_voice:
            voice_score = self._verify_voice(audio, sr)

        # ----------------------
        # FUSION
        # ----------------------
        used = 0
        total = 0.0
        if is_face:
            total += face_score
            used += 1
        if is_voice:
            total += voice_score
            used += 1
        fusion_score = total / used if used > 0 else 0.0

        # ----------------------
        # LIVENESS GATE (check only)
        # ----------------------
        face_liveness_passed = True
        face_liveness_step = None
        face_liveness_instruction = None

        if self.require_face_liveness and is_face:
            machine = self._face_sessions.get(username)
            if machine is None:
                face_liveness_passed = False
            else:
                st = getattr(machine, "state", None)
                if st is None:
                    face_liveness_passed = False
                else:
                    face_liveness_passed = bool(st.done and not st.failed)

                face_liveness_step = (
                    machine.current_step().value
                    if machine.current_step() is not None
                    else None
                )
                face_liveness_instruction = machine.instruction()

        # ----------------------
        # DECISION LOGIC
        # ----------------------
        if is_face and not is_voice:
            decision = "GRANTED" if (face_score >= self.face_thr and face_liveness_passed) else "DENIED"
        elif is_voice and not is_face:
            decision = "GRANTED" if (voice_score >= self.voice_thr) else "DENIED"
        else:
            decision = "GRANTED" if (fusion_score >= self.fusion_thr and face_liveness_passed) else "DENIED"

        reason = (
            f"face={face_score:.2f} | "
            f"voice={voice_score:.2f} | "
            f"fusion={fusion_score:.2f} | "
            f"face_thr={self.face_thr:.2f} | "
            f"voice_thr={self.voice_thr:.2f} | "
            f"fusion_thr={self.fusion_thr:.2f} | "
            f"liveness_passed={str(face_liveness_passed).lower()}"
        )

        # Clear liveness session on success
        if decision == "GRANTED" and username in self._face_sessions:
            self._face_sessions.pop(username, None)


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
