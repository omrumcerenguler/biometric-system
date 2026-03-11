import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js";
import {
  apiStartEnroll,
  apiPushFrame,
  apiFinishEnroll,
  apiEnrollVoice,
} from "./api.js";
import { startVoiceRecording, stopVoiceRecordingToBase64 } from "./voice.js";

export function initEnroll() {
  const usernameEl = byId("username");
  const roleEl = byId("role");

  const videoEl = byId("camVideo");
  const canvasEl = byId("camCanvas");

  const btnStartCam = byId("btnStartCam");
  const btnStopCam = byId("btnStopCam");
  const btnStartEnroll = byId("btnStartEnroll");
  const btnStopEnroll = byId("btnStopEnroll");

  const sessionTextEl = byId("sessionText");
  const progressTextEl = byId("progressText");
  const progressBarEl = byId("progressBar");
  const statusTextEl = byId("statusText");

  const btnVoiceStart = byId("btnVoiceStart");
  const btnVoiceStop = byId("btnVoiceStop");
  const btnVoiceEnroll = byId("btnVoiceEnroll");
  const audioPreview = byId("audioPreview");
  const voiceStatusEl = byId("voiceStatus");

  let sessionId = null;
  let isCapturing = false;
  let captureTimer = null;
  let frameInFlight = false;
  let targetSamples = 15;
  let acceptedSamples = 0;
  let voiceB64 = null;

  function setStatus(msg) {
    setText(statusTextEl, msg);
    console.log("[ENROLL]", msg);
  }

  function setVoiceStatus(msg) {
    setText(voiceStatusEl, msg);
    console.log("[VOICE]", msg);
  }

  function setSession(id) {
    sessionId = id;
    setText(sessionTextEl, id ? `Session: ${id}` : "Session: -");
  }

  function setProgress(count, target) {
    acceptedSamples = count;
    targetSamples = target;

    setText(progressTextEl, `${count}/${target}`);

    if (progressBarEl) {
      const pct = target > 0 ? Math.min(100, Math.round((count / target) * 100)) : 0;
      progressBarEl.style.width = `${pct}%`;
    }
  }

  async function stopEnrollmentFlow(doFinish) {
    if (!isCapturing) return;

    isCapturing = false;

    if (captureTimer) {
      clearInterval(captureTimer);
      captureTimer = null;
    }

    if (btnStartEnroll) btnStartEnroll.disabled = false;
    if (btnStopEnroll) btnStopEnroll.disabled = true;

    if (doFinish && sessionId) {
      try {
        const result = await apiFinishEnroll(sessionId);
        const nSamples = result?.n_samples ?? acceptedSamples;
        setStatus(`Saved: ${result?.status || "OK"} (samples: ${nSamples})`);
      } catch (e) {
        console.error(e);
        setStatus(`Finish error: ${e.message || "UNKNOWN_ERROR"}`);
      }
    } else {
      setStatus("Enrollment stopped.");
    }
  }

  btnStartCam?.addEventListener("click", async () => {
    try {
      setStatus("Requesting camera...");
      await startCamera(videoEl);
      setStatus("Camera ready.");
    } catch (e) {
      console.error(e);
      setStatus(`Camera error: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  btnStopCam?.addEventListener("click", () => {
    stopCamera([videoEl]);
    setStatus("Camera stopped.");
  });

  btnStartEnroll?.addEventListener("click", async () => {
    if (isCapturing) return;

    const username = (usernameEl?.value || "").trim();
    const role = (roleEl?.value || "").trim();

    if (!username) {
      setStatus("Username is required.");
      return;
    }

    if (!role) {
      setStatus("Role is required.");
      return;
    }

    const hasCamera = !!videoEl?.srcObject;
    if (!hasCamera) {
      setStatus("Start camera first.");
      return;
    }

    try {
      setStatus("Starting enrollment...");
      setProgress(0, 15);
      setSession(null);

      const startRes = await apiStartEnroll(username, role);
      setSession(startRes?.session_id || null);
      setProgress(0, startRes?.target || 15);

      isCapturing = true;
      if (btnStartEnroll) btnStartEnroll.disabled = true;
      if (btnStopEnroll) btnStopEnroll.disabled = false;

      setStatus("Enrollment started. Collecting samples...");

      captureTimer = setInterval(async () => {
        if (!isCapturing || frameInFlight) return;

        const faceB64 = captureFrameBase64(videoEl, canvasEl);
        if (!faceB64) return;

        frameInFlight = true;

        try {
          const r = await apiPushFrame(sessionId, faceB64);

          if (r?.accepted) {
            setProgress(r.count ?? acceptedSamples, r.target ?? targetSamples);
          } else if (r?.reason) {
            setStatus(`Collecting... (${r.reason})`);
          }

          const reached =
            r?.reason === "TARGET_REACHED" ||
            ((r?.count ?? 0) >= (r?.target ?? targetSamples) && (r?.target ?? targetSamples) > 0);

          if (reached) {
            setStatus("Target reached. Saving...");
            await stopEnrollmentFlow(true);
          }
        } catch (e) {
          console.error(e);
          setStatus(`Frame error: ${e.message || "UNKNOWN_ERROR"}`);
        } finally {
          frameInFlight = false;
        }
      }, 220);
    } catch (e) {
      console.error(e);
      setStatus(`Start error: ${e.message || "UNKNOWN_ERROR"}`);
      isCapturing = false;
      if (btnStartEnroll) btnStartEnroll.disabled = false;
      if (btnStopEnroll) btnStopEnroll.disabled = true;
    }
  });

  btnStopEnroll?.addEventListener("click", async () => {
    await stopEnrollmentFlow(false);
  });

  btnVoiceStart?.addEventListener("click", async () => {
    try {
      voiceB64 = null;
      if (btnVoiceStart) btnVoiceStart.disabled = true;
      if (btnVoiceStop) btnVoiceStop.disabled = false;
      if (btnVoiceEnroll) btnVoiceEnroll.disabled = true;

      setVoiceStatus("Recording...");
      await startVoiceRecording();
    } catch (e) {
      console.error(e);
      setVoiceStatus(`Microphone error: ${e.message || "UNKNOWN_ERROR"}`);
      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceStop) btnVoiceStop.disabled = true;
      if (btnVoiceEnroll) btnVoiceEnroll.disabled = false;
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

      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceEnroll) btnVoiceEnroll.disabled = !voiceB64;
    } catch (e) {
      console.error(e);
      setVoiceStatus(`Stop/encode failed: ${e.message || "UNKNOWN_ERROR"}`);
      if (btnVoiceStart) btnVoiceStart.disabled = false;
      if (btnVoiceStop) btnVoiceStop.disabled = true;
    }
  });

  btnVoiceEnroll?.addEventListener("click", async () => {
    try {
      const username = (usernameEl?.value || "").trim();
      const role = (roleEl?.value || "").trim();

      if (!username) {
        setVoiceStatus("Username is required.");
        return;
      }

      if (!role) {
        setVoiceStatus("Role is required.");
        return;
      }

      if (!voiceB64) {
        setVoiceStatus("Record voice first.");
        return;
      }

      if (btnVoiceEnroll) btnVoiceEnroll.disabled = true;
      setVoiceStatus("Saving voice template...");

      const res = await apiEnrollVoice(username, role, voiceB64);
      setVoiceStatus(res?.status ? `Voice enrolled: ${res.status}` : "Voice enrolled.");
    } catch (e) {
      console.error(e);
      setVoiceStatus(`Voice enroll failed: ${e.message || "UNKNOWN_ERROR"}`);
    } finally {
      if (btnVoiceEnroll) btnVoiceEnroll.disabled = false;
    }
  });

  setSession(null);
  setProgress(0, targetSamples);
  setStatus("Ready.");
  setVoiceStatus("Ready.");

  if (btnStopEnroll) btnStopEnroll.disabled = true;
  if (btnVoiceStop) btnVoiceStop.disabled = true;
}
