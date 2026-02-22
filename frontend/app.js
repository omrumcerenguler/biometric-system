// frontend/app.js

// =========================
// 0) STEP NAVIGATION (GLOBAL)
// =========================
let selectedCompany = null;
let selectedMethod = null;

function showStep(stepIdToShow) {
  const steps = ["step-company", "step-enroll", "step-method", "step-face", "step-voice", "step-result"];
  steps.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("hidden", id !== stepIdToShow);
  });
}
window.showStep = showStep;
window.startCamera = startCamera;

// Aktif step'e göre video/canvas seç (EN ÖNEMLİ FIX)
function getActiveVideoEl() {
  const stepFace = document.getElementById("step-face");
  const faceVisible = stepFace && !stepFace.classList.contains("hidden");

  if (faceVisible) return document.getElementById("video");     // step-face içindeki video
  return document.getElementById("camVideo");                   // enrollment video
}

function getActiveCanvasEl() {
  const stepFace = document.getElementById("step-face");
  const faceVisible = stepFace && !stepFace.classList.contains("hidden");

  if (faceVisible) return document.getElementById("canvas");    // step-face içindeki canvas
  return document.getElementById("camCanvas");                  // enrollment canvas
}

window.selectCompany = function (company) {
  selectedCompany = company;
  console.log("Selected company:", selectedCompany);
  showStep("step-method");
};

window.selectMethod = async function (method) {
  selectedMethod = method;
  console.log("Selected method:", selectedMethod);

  if (method === "face") {
    showStep("step-face");
    // ✅ eskisi gibi: face ekranına geçince kamerayı otomatik aç
    await startCamera();
  } else if (method === "voice") {
    showStep("step-voice");
  }
};

window.restart = function () {
  selectedCompany = null;
  selectedMethod = null;
  console.log("Restart");
  showStep("step-company");
};

window.addEventListener("DOMContentLoaded", () => {
  showStep("step-company");
});

// =========================
// 1) ENROLLMENT (CAMERA + API)
// =========================

// ⚠️ Backend URL
const API_BASE = "http://127.0.0.1:8000";

let mediaStream = null;
let captureTimer = null;

let enrollSessionId = null;
let targetSamples = 15;
let acceptedSamples = 0;
let isCapturing = false;

// --- UI elements ---
const usernameEl = document.getElementById("username");
const roleEl = document.getElementById("role");

const btnStartCam = document.getElementById("btnStartCam");
const btnStopCam = document.getElementById("btnStopCam");

const btnStartEnroll = document.getElementById("btnStartEnroll");
const btnStopEnroll = document.getElementById("btnStopEnroll");

const statusEl = document.getElementById("statusText");
const sessionEl = document.getElementById("sessionText");
const progressEl = document.getElementById("progressText");
const progressBarEl = document.getElementById("progressBar");

// -------------------------
// Helpers
// -------------------------
function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
  console.log("[STATUS]", msg);
}

function setProgress(count, target) {
  acceptedSamples = count;
  targetSamples = target;

  if (progressEl) progressEl.textContent = `${count}/${target}`;
  const pct = Math.min(100, Math.round((count / target) * 100));
  if (progressBarEl) progressBarEl.style.width = `${pct}%`;
}

function setSession(id) {
  enrollSessionId = id;
  if (sessionEl) sessionEl.textContent = id ? `Session: ${id}` : `Session: -`;
}

// -------------------------
// Camera
// -------------------------
async function startCamera() {
  const v = getActiveVideoEl();
  if (!v) {
    setStatus("Video elementi bulunamadı (#camVideo veya #video).");
    return;
  }

  // Stream zaten varsa: sadece aktif videoya bağla
  if (mediaStream) {
    v.srcObject = mediaStream;
    try {
      await v.play();
    } catch {}
    setStatus("Camera ready.");
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    });

    // autoplay için güvenli ayarlar
    v.muted = true;
    v.playsInline = true;

    v.srcObject = mediaStream;
    await v.play();

    setStatus("Camera ready.");
  } catch (err) {
    console.error(err);
    setStatus("Camera error: permission or device issue. (Console'a bak)");
  }
}

function stopCamera() {
  if (captureTimer) {
    clearInterval(captureTimer);
    captureTimer = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }

  // iki video elementini de temizle
  const v1 = document.getElementById("camVideo");
  const v2 = document.getElementById("video");
  if (v1) v1.srcObject = null;
  if (v2) v2.srcObject = null;

  setStatus("Camera stopped.");
}

// -------------------------
// Capture frame -> base64 JPEG
// -------------------------
function captureFrameBase64() {
  const v = getActiveVideoEl();
  const c = getActiveCanvasEl();
  if (!v || !c) return null;

  const ctx = c.getContext("2d");
  const w = v.videoWidth;
  const h = v.videoHeight;
  if (!w || !h) return null;

  c.width = w;
  c.height = h;
  ctx.drawImage(v, 0, 0, w, h);

  const dataUrl = c.toDataURL("image/jpeg", 0.85);
  return dataUrl.split(",")[1];

}

// -------------------------
// API calls
// -------------------------
async function apiStartEnroll(username, role) {
  const res = await fetch(`${API_BASE}/enroll/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, role }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Enroll start failed");
  }

  return await res.json(); // {session_id, target}
}

async function apiPushFrame(session_id, face_image_b64) {
  const res = await fetch(`${API_BASE}/enroll/frame`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, face_image_b64 }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Enroll frame failed");
  }

  return await res.json(); // {accepted, reason, count, target}
}

async function apiFinishEnroll(session_id) {
  const res = await fetch(`${API_BASE}/enroll/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Enroll finish failed");
  }

  return await res.json();
}

// -------------------------
// Enrollment flow
// -------------------------
async function startEnrollmentFlow() {
  if (isCapturing) return;

  const username = (usernameEl?.value || "").trim();
  const role = (roleEl?.value || "").trim();

  if (!username) {
    setStatus("Username boş olamaz.");
    return;
  }
  if (!role) {
    setStatus("Role boş olamaz.");
    return;
  }

  if (!mediaStream) {
    setStatus("Önce kamerayı başlat.");
    return;
  }

  try {
    setStatus("Starting enrollment...");
    setProgress(0, targetSamples);
    setSession(null);

    const startData = await apiStartEnroll(username, role);
    setSession(startData.session_id);
    setProgress(0, startData.target);

    setStatus("Enrollment started. Collecting samples...");

    isCapturing = true;
    if (btnStartEnroll) btnStartEnroll.disabled = true;
    if (btnStopEnroll) btnStopEnroll.disabled = false;

    captureTimer = setInterval(async () => {
      if (!isCapturing) return;

      const b64 = captureFrameBase64();
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
          stopEnrollmentFlow(true);
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
    if (btnStartEnroll) btnStartEnroll.disabled = false;
    if (btnStopEnroll) btnStopEnroll.disabled = true;
  }
}

async function stopEnrollmentFlow(doFinish) {
  if (!isCapturing) return;

  isCapturing = false;

  if (btnStartEnroll) btnStartEnroll.disabled = false;
  if (btnStopEnroll) btnStopEnroll.disabled = true;

  if (captureTimer) {
    clearInterval(captureTimer);
    captureTimer = null;
  }

  if (doFinish && enrollSessionId) {
    try {
      const result = await apiFinishEnroll(enrollSessionId);
      setStatus(`Saved: ${result.status || "OK"} (samples: ${result.n_samples || acceptedSamples})`);
    } catch (e) {
      console.error(e);
      setStatus(`Finish error: ${e.message}`);
    }
  } else {
    setStatus("Enrollment stopped.");
  }
}

// -------------------------
// IDENTIFY (Face) API
// -------------------------
async function apiIdentifyFace(face_image_b64) {
  const res = await fetch(`${API_BASE}/identify/`, {   // ✅ DOĞRU PATH
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ face_image_b64 }),          // ✅ Backend bunu bekliyor
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Identify failed");
  }

  return await res.json();
}

// -------------------------
// STEP-FACE: Capture button handler
// -------------------------
window.captureFace = async function () {
  try {
    // 1) Frame al
    const b64 = captureFrameBase64();
    if (!b64) {
      setStatus("Frame alınamadı. Kamera açık mı?");
      return;
    }

    setStatus("Capturing... Identifying face...");

    // 2) Backend'e gönder
    const result = await apiIdentifyFace(b64);

    // 3) Sonucu ekrana bas
    // Beklenen result örneği (senin AuthenticationService identify_face gibi):
    // { identified: true/false, username, user_id, similarity }

    const decisionEl = document.getElementById("result-decision");
    const faceScoreEl = document.getElementById("face-score");
    const voiceScoreEl = document.getElementById("voice-score");
    const fusionScoreEl = document.getElementById("fusion-score");

    if (result.identified) {
      if (decisionEl) decisionEl.textContent = `✅ IDENTIFIED: ${result.username} (id=${result.user_id})`;
    } else {
      if (decisionEl) decisionEl.textContent = `❌ NOT IDENTIFIED`;
    }

    if (faceScoreEl) faceScoreEl.textContent = (result.similarity ?? 0).toFixed(3);
    if (voiceScoreEl) voiceScoreEl.textContent = "-";
    if (fusionScoreEl) fusionScoreEl.textContent = "-";

    // 4) Result step'e geç
    showStep("step-result");
    setStatus("Done.");
  } catch (e) {
    console.error(e);
    setStatus(`Capture/Identify error: ${e.message}`);
  }
};

// -------------------------
// Button bindings (NULL-SAFE)
// -------------------------
if (btnStartCam) btnStartCam.addEventListener("click", startCamera);
if (btnStopCam) btnStopCam.addEventListener("click", stopCamera);

if (btnStartEnroll) btnStartEnroll.addEventListener("click", startEnrollmentFlow);
if (btnStopEnroll) btnStopEnroll.addEventListener("click", () => stopEnrollmentFlow(false));

// İlk yüklemede enrollment UI
setSession(null);
setProgress(0, targetSamples);
setStatus("Ready.");
if (btnStopEnroll) btnStopEnroll.disabled = true;