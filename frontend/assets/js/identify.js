import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js";
import { apiIdentifyFace, apiAuthVerify } from "./api.js";
import { startVoiceRecording, stopVoiceRecordingToBase64 } from "./voice.js";

/**
 * Identify page flow (username input yok):
 * Face capture -> /identify (1:N) -> username found
 * Voice record -> /auth/verify (username + face + voice)
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

  const btnVoiceStart = byId("btnVoiceStart");
  const btnVoiceStop = byId("btnVoiceStop");
  const audioPreview = byId("audioPreview");

  const btnVerify = byId("btnVerify");
  const btnRestart = byId("btnRestart");

  const decisionEl = byId("result-decision");
  const faceScoreEl = byId("face-score");
  const voiceScoreEl = byId("voice-score");
  const fusionScoreEl = byId("fusion-score");

  // --- state ---
  let faceB64 = null;
  let voiceB64 = null;
  let identifiedUsername = null; // /identify’den gelecek

  // --- small status helpers ---
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
      await startCamera(videoEl); // camera.js'in bu imzayı desteklemesi lazım
      setFaceStatus("Camera ready.");
    } catch (e) {
      console.error(e);
      setFaceStatus("Camera error. Check permissions / console.");
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
        identifiedUsername = null;
        setFaceStatus("Not identified. Try again with better lighting.");
        // istersen burada kal, voice'a geçirme
        return;
      }

      identifiedUsername = idRes.username;
      setFaceStatus(`Identified: ${idRes.username} (score ${(idRes.similarity ?? 0).toFixed(3)})`);

      // Face tamam -> Voice step
      showStep("step-voice");
    } catch (e) {
      console.error(e);
      setFaceStatus("Identify failed. Check backend / console.");
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
      setVoiceStatus("Microphone error. Check permissions / console.");
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

      // Verify enable koşulları
      if (btnVerify) btnVerify.disabled = !(!!faceB64 && !!voiceB64 && !!identifiedUsername);

      if (btnVoiceStart) btnVoiceStart.disabled = false;
    } catch (e) {
      console.error(e);
      setVoiceStatus("Stop/encode failed. Check console.");
      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceStop) btnVoiceStop.disabled = true;
    }
  });

  // -----------------------
  // 4) Verify (Face + Voice + identified username)
  // -----------------------
  btnVerify?.addEventListener("click", async () => {
    try {
      if (!identifiedUsername) {
        setStatus("No identified user. Go back and capture face again.");
        return;
      }
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
        username: identifiedUsername,
        face_image_b64: faceB64,
        voice_wav_b64: voiceB64,
      });

      setText(decisionEl, res.decision || "-");
      setText(faceScoreEl, (res.face_score ?? 0).toFixed(3));
      setText(voiceScoreEl, (res.voice_score ?? 0).toFixed(3));
      setText(fusionScoreEl, (res.fusion_score ?? 0).toFixed(3));

      showStep("step-result");
      setStatus("Done.");
    } catch (e) {
      console.error(e);
      setStatus("Verify failed. Check backend response / console.");
    }
  });

  // -----------------------
  // 5) Restart
  // -----------------------
  function restart() {
    stopCamera([videoEl]); // camera.js bu imzayı destekliyorsa
    faceB64 = null;
    voiceB64 = null;
    identifiedUsername = null;

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

  btnRestart?.addEventListener("click", restart);
  window.restartVerify = restart; // HTML’de onclick varsa diye güvenli
}