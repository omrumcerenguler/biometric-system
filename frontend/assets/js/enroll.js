import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js";
import { apiStartEnroll, apiPushFrame, apiFinishEnroll } from "./api.js";

export function initEnroll() {
  // enroll.html’de kullandığın id’ler (senin mevcut sayfana göre)
  const usernameEl = byId("username");
  const roleEl = byId("role");

  const btnStartCam = byId("btnStartCam");
  const btnStopCam = byId("btnStopCam");
  const btnStartEnroll = byId("btnStartEnroll");
  const btnStopEnroll = byId("btnStopEnroll");

  const statusEl = byId("statusText");
  const sessionEl = byId("sessionText");
  const progressEl = byId("progressText");
  const progressBarEl = byId("progressBar");

  const videoEl = byId("camVideo");
  const canvasEl = byId("camCanvas");

  let enrollSessionId = null;
  let captureTimer = null;
  let isCapturing = false;
  let targetSamples = 15;

  function setStatus(msg) {
    setText(statusEl, msg);
    console.log("[ENROLL]", msg);
  }
  function setSession(id) {
    enrollSessionId = id;
    setText(sessionEl, id ? `Session: ${id}` : "Session: -");
  }
  function setProgress(count, target) {
    setText(progressEl, `${count}/${target}`);
    const pct = Math.min(100, Math.round((count / target) * 100));
    if (progressBarEl) progressBarEl.style.width = `${pct}%`;
  }

  async function startEnrollFlow() {
    if (isCapturing) return;

    const username = (usernameEl?.value || "").trim();
    const role = (roleEl?.value || "").trim();

    if (!username) return setStatus("Username boş olamaz.");
    if (!role) return setStatus("Role boş olamaz.");
    if (!videoEl || !canvasEl) return setStatus("Enroll video/canvas yok.");

    try {
      setStatus("Starting enrollment...");
      setSession(null);
      setProgress(0, targetSamples);

      const startData = await apiStartEnroll(username, role);
      setSession(startData.session_id);
      targetSamples = startData.target;
      setProgress(0, targetSamples);

      isCapturing = true;
      btnStartEnroll && (btnStartEnroll.disabled = true);
      btnStopEnroll && (btnStopEnroll.disabled = false);

      captureTimer = setInterval(async () => {
        if (!isCapturing) return;

        const b64 = captureFrameBase64(videoEl, canvasEl);
        if (!b64) return;

        try {
          const r = await apiPushFrame(enrollSessionId, b64);

          if (!r.accepted) {
            setStatus(`Collecting... (${r.reason})`);
            return;
          }

          setProgress(r.count, r.target);

          if (r.reason === "TARGET_REACHED") {
            setStatus("Target reached. Saving...");
            await stopEnrollFlow(true);
          }
        } catch (e) {
          console.error(e);
          setStatus(`Frame error: ${e.message}`);
        }
      }, 200);
    } catch (e) {
      console.error(e);
      setStatus(`Start error: ${e.message}`);
      isCapturing = false;
      btnStartEnroll && (btnStartEnroll.disabled = false);
      btnStopEnroll && (btnStopEnroll.disabled = true);
    }
  }

  async function stopEnrollFlow(doFinish) {
    if (!isCapturing) return;
    isCapturing = false;

    if (captureTimer) clearInterval(captureTimer);
    captureTimer = null;

    btnStartEnroll && (btnStartEnroll.disabled = false);
    btnStopEnroll && (btnStopEnroll.disabled = true);

    if (doFinish && enrollSessionId) {
      try {
        const res = await apiFinishEnroll(enrollSessionId);
        setStatus(`Saved: ${res.status || "OK"} (samples: ${res.n_samples || "-"})`);
      } catch (e) {
        setStatus(`Finish error: ${e.message}`);
      }
    } else {
      setStatus("Enrollment stopped.");
    }
  }

  // Bindings
  btnStartCam?.addEventListener("click", async () => {
    try {
      await startCamera(videoEl);
      setStatus("Camera ready.");
    } catch (e) {
      setStatus(`Camera error: ${e.message}`);
    }
  });

  btnStopCam?.addEventListener("click", () => {
    stopCamera([videoEl]);
    setStatus("Camera stopped.");
  });

  btnStartEnroll?.addEventListener("click", startEnrollFlow);
  btnStopEnroll?.addEventListener("click", () => stopEnrollFlow(false));

  // initial
  setSession(null);
  setProgress(0, targetSamples);
  setStatus("Ready.");
  btnStopEnroll && (btnStopEnroll.disabled = true);
}