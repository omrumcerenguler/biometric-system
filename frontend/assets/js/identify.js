import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js";
import { apiIdentifyFace, apiAuthVerify } from "./api.js";
import { startVoiceRecording, stopVoiceRecordingToBase64 } from "./voice.js";

/**
 * Identify page flow:
 * Face capture -> /identify (1:N) -> user found
 * Voice record -> /auth/verify (face + voice)
 */
export function initIdentify() {
  // --- step helper ---
  const stepIds = ["step-face", "step-voice", "step-verify", "step-result"];
  function showStep(idToShow) {
    stepIds.forEach((id) => {
      const el = byId(id);
      if (!el) return;
      el.classList.toggle("hidden", id !== idToShow);
    });
  }

  // --- elements ---
  const videoEl = byId("video");
  const canvasEl = byId("canvas");

  const faceStatusEl = byId("faceStatus");
  const voiceStatusEl = byId("voiceStatus");
  const statusTextEl = byId("statusText");

  const btnCamStart = byId("btnCamStart");
  const btnFaceCapture = byId("btnFaceCapture");
  const btnBack = byId("btnBack");

  const btnVoiceStart = byId("btnVoiceStart");
  const btnVoiceStop = byId("btnVoiceStop");
  const audioPreview = byId("audioPreview");

  const btnVerify = byId("btnVerify");
  const btnRestart = byId("btnRestart");
  const btnRestartResult = byId("btnRestartResult");

  const decisionEl = byId("result-decision");
  const faceScoreEl = byId("face-score");
  const voiceScoreEl = byId("voice-score");
  const fusionScoreEl = byId("fusion-score");

  // --- state ---
  let faceB64 = null;
  let voiceB64 = null;
  let identifiedUser = null; // sadece bilgi amaçlı

  // --- status helpers ---
  function setFaceStatus(msg) {
    if (faceStatusEl) setText(faceStatusEl, msg);
    console.log("[FACE]", msg);
  }

  function setVoiceStatus(msg) {
    if (voiceStatusEl) setText(voiceStatusEl, msg);
    console.log("[VOICE]", msg);
  }

  function setStatus(msg) {
    if (statusTextEl) setText(statusTextEl, msg);
    console.log("[STATUS]", msg);
  }

  // --- initial UI ---
  showStep("step-face");
  if (btnVoiceStop) btnVoiceStop.disabled = true;
  if (btnVerify) btnVerify.disabled = true;

  // -----------------------
  // 1) Camera
  // -----------------------
  btnCamStart?.addEventListener("click", async () => {
    try {
      setFaceStatus("Requesting camera...");
      await startCamera(videoEl);
      setFaceStatus("Camera ready.");
    } catch (e) {
      console.error(e);
      setFaceStatus(`Camera error: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  // -----------------------
  // 2) Capture Face + Identify
  // -----------------------
  btnFaceCapture?.addEventListener("click", async () => {
    try {
      faceB64 = captureFrameBase64(videoEl, canvasEl);

      if (!faceB64) {
        setFaceStatus("Face frame not captured. Start camera first.");
        return;
      }

      setFaceStatus("Identifying face...");
      const idRes = await apiIdentifyFace(faceB64);

      if (!idRes?.identified) {
        identifiedUser = null;
        setFaceStatus("Not identified. Try again with better lighting.");
        return;
      }

      identifiedUser = idRes.username || `user_id=${idRes.user_id}`;
      setFaceStatus(
        `Identified: ${identifiedUser} (score ${(idRes.similarity ?? 0).toFixed(3)})`
      );

      // Face tamam -> Voice step
      showStep("step-voice");
    } catch (e) {
      console.error(e);
      setFaceStatus(`Identify failed: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  // -----------------------
  // 3) Voice record
  // -----------------------
  btnVoiceStart?.addEventListener("click", async () => {
    try {
      voiceB64 = null;

      if (btnVoiceStart) btnVoiceStart.disabled = true;
      if (btnVoiceStop) btnVoiceStop.disabled = false;
      if (btnVerify) btnVerify.disabled = true;

      setVoiceStatus("Recording...");
      await startVoiceRecording();
    } catch (e) {
      console.error(e);
      setVoiceStatus(`Microphone error: ${e.message || "UNKNOWN_ERROR"}`);
      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceStop) btnVoiceStop.disabled = true;
    }
  });

  btnVoiceStop?.addEventListener("click", async () => {
    try {
      if (btnVoiceStop) btnVoiceStop.disabled = true;

      const { blob, b64 } = await stopVoiceRecordingToBase64();
      voiceB64 = b64;

      if (audioPreview) {
        audioPreview.src = URL.createObjectURL(blob);
        audioPreview.classList.remove("hidden");
      }

      setVoiceStatus("Voice recorded.");

      // Voice tamam -> Verify step
      showStep("step-verify");

      if (btnVerify) btnVerify.disabled = !(!!faceB64 && !!voiceB64);

      if (btnVoiceStart) btnVoiceStart.disabled = false;
    } catch (e) {
      console.error(e);
      setVoiceStatus(`Stop/encode failed: ${e.message || "UNKNOWN_ERROR"}`);
      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceStop) btnVoiceStop.disabled = true;
    }
  });

  // -----------------------
  // 4) Verify (Face + Voice)
  // -----------------------
  btnVerify?.addEventListener("click", async () => {
    try {
      if (!faceB64) {
        setStatus("Face missing. Capture face first.");
        return;
      }

      if (!voiceB64) {
        setStatus("Voice missing. Record voice first.");
        return;
      }

      setStatus("Verifying...");

      const res = await apiAuthVerify({
        face_image_b64: faceB64,
        voice_wav_b64: voiceB64,
      });

      setText(decisionEl, res.decision || "-");
      setText(faceScoreEl, (res.face_score ?? 0).toFixed(3));
      setText(voiceScoreEl, (res.voice_score ?? 0).toFixed(3));
      setText(fusionScoreEl, (res.fusion_score ?? 0).toFixed(3));

      showStep("step-result");
      setStatus(res.reason || "Done.");
    } catch (e) {
      console.error(e);

      if (e.message === "VOICE_NOT_ENROLLED") {
        setStatus("Voice template not found for this user. Enroll voice first.");
        return;
      }

      if (e.message === "FACE_NOT_IDENTIFIED") {
        setStatus("Face not identified. Capture face again.");
        return;
      }

      setStatus(`Verify failed: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  // -----------------------
  // 5) Restart
  // -----------------------
  function restart() {
    stopCamera([videoEl]);
    faceB64 = null;
    voiceB64 = null;
    identifiedUser = null;

    if (audioPreview) {
      audioPreview.pause?.();
      audioPreview.src = "";
      audioPreview.classList.add("hidden");
    }

    setFaceStatus("");
    setVoiceStatus("");
    setStatus("");

    if (btnVoiceStop) btnVoiceStop.disabled = true;
    if (btnVerify) btnVerify.disabled = true;

    showStep("step-face");
  }

  // -----------------------
  // 6) Back
  // -----------------------
  btnBack?.addEventListener("click", (e) => {
    e.preventDefault();
    window.location.assign("../portal/login_portal.html");
  });

  btnRestart?.addEventListener("click", restart);
  btnRestartResult?.addEventListener("click", restart);
  window.restartVerify = restart;
}
