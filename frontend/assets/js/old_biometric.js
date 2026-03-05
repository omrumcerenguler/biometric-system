// frontend/assets/js/biometric.js

// =========================
// 0) STEP NAVIGATION (GLOBAL)
// =========================
let selectedCompany = null;
let selectedMethod = null;

function showStep(stepIdToShow) {
  const steps = ["step-method", "step-face", "step-voice", "step-result"];
  steps.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("hidden", id !== stepIdToShow);
  });
}
window.showStep = showStep;

// Aktif step'e göre video/canvas seç (EN ÖNEMLİ FIX)
function getActiveVideoEl() {
  const stepFace = document.getElementById("step-face");
  const faceVisible = stepFace && !stepFace.classList.contains("hidden");

  if (faceVisible) return document.getElementById("video"); // step-face içindeki video
  return document.getElementById("camVideo"); // enrollment video
}

function getActiveCanvasEl() {
  const stepFace = document.getElementById("step-face");
  const faceVisible = stepFace && !stepFace.classList.contains("hidden");

  if (faceVisible) return document.getElementById("canvas"); // step-face içindeki canvas
  return document.getElementById("camCanvas"); // enrollment canvas
}

window.selectMethod = async function (method) {
  selectedMethod = method;
  console.log("Selected method:", selectedMethod);

  if (method === "face") {
    showStep("step-face");
    await startCamera(); // face ekranına geçince kamerayı otomatik aç
  } else if (method === "voice") {
    showStep("step-voice");
  }
};

window.restart = function () {
  selectedCompany = null;
  showStep("step-home");
};

// =========================
// 1) ENROLLMENT (CAMERA + API)
// =========================

// ⚠️ Backend URL
const API_BASE = "http://127.0.0.1:8000";

// stream/timer/state
let mediaStream = null;
let captureTimer = null;

let enrollSessionId = null;
let targetSamples = 15;
let acceptedSamples = 0;
let isCapturing = false;

// --- UI elements (sayfaya göre var/yok olabilir) ---
let usernameEl, roleEl;
let btnStartCam, btnStopCam, btnStartEnroll, btnStopEnroll;
let statusEl, sessionEl, progressEl, progressBarEl;

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
window.startCamera = startCamera;

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
window.stopCamera = stopCamera;

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
// API calls (ENROLL)
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
      setStatus(
        `Saved: ${result.status || "OK"} (samples: ${result.n_samples || acceptedSamples})`,
      );
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
  const res = await fetch(`${API_BASE}/identify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ face_image_b64 }),
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
    const usernameInput = document.getElementById("usernameInput");
    const username = usernameInput?.value?.trim();

    if (!username) {
      setStatus("Username required.");
      return;
    }

    const faceB64 = captureFrameBase64();
    if (!faceB64) {
      setStatus("Face frame alınamadı.");
      return;
    }

    if (!recordedVoiceB64) {
      setStatus("Voice recording required.");
      return;
    }

    setStatus("Sending face + voice...");

    const res = await fetch(`${API_BASE}/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: username,
        face_image_b64: faceB64,
        voice_wav_b64: recordedVoiceB64
      }),
    });

    const result = await res.json();

    if (!res.ok) {
      setStatus(result.detail || "Verify error.");
      return;
    }

    const decisionEl = document.getElementById("result-decision");
    const faceScoreEl = document.getElementById("face-score");
    const voiceScoreEl = document.getElementById("voice-score");
    const fusionScoreEl = document.getElementById("fusion-score");

    if (decisionEl) decisionEl.textContent = result.decision;
    if (faceScoreEl) faceScoreEl.textContent = result.face_score.toFixed(3);
    if (voiceScoreEl) voiceScoreEl.textContent = result.voice_score.toFixed(3);
    if (fusionScoreEl) fusionScoreEl.textContent = result.fusion_score.toFixed(3);

    showStep("step-result");
    setStatus("Done.");
  } catch (err) {
    console.error(err);
    setStatus("Verify failed.");
  }
};

// --- simple in-tab page history (biometric flow) ---
(function trackPrevPage() {
  try {
    const prev = sessionStorage.getItem("prevPath");
    const last = sessionStorage.getItem("lastPath");

    // her sayfa açılışında: prev <- last, last <- current
    sessionStorage.setItem("prevPath", last || "");
    sessionStorage.setItem("lastPath", window.location.pathname);
  } catch (e) {
    // ignore
  }
})();

window.goBack = function () {
  const prevPath = sessionStorage.getItem("prevPath");

  // Eğer prevPath varsa ve biometric içinde bir sayfaysa, oraya dön
  if (prevPath && prevPath.includes("/biometric/")) {
    window.location.href = prevPath;
    return;
  }

  // yoksa tarayıcı back dene
  if (window.history.length > 1) {
    window.history.back();
    return;
  }

  // en son fallback
  window.location.href = "/portal/login_portal.html";
};

// -------------------------
// Init + Button bindings (NULL-SAFE)
// -------------------------
function bindBiometricUI() {
  // elementleri burada alıyoruz ki sayfa yüklenmeden null olmasın
  usernameEl = document.getElementById("username");
  roleEl = document.getElementById("role");

  btnStartCam = document.getElementById("btnStartCam");
  btnStopCam = document.getElementById("btnStopCam");
  btnStartEnroll = document.getElementById("btnStartEnroll");
  btnStopEnroll = document.getElementById("btnStopEnroll");

  statusEl = document.getElementById("statusText");
  sessionEl = document.getElementById("sessionText");
  progressEl = document.getElementById("progressText");
  progressBarEl = document.getElementById("progressBar");

  if (btnStartCam) btnStartCam.addEventListener("click", startCamera);
  if (btnStopCam) btnStopCam.addEventListener("click", stopCamera);

  if (btnStartEnroll)
    btnStartEnroll.addEventListener("click", startEnrollmentFlow);
  if (btnStopEnroll)
    btnStopEnroll.addEventListener("click", () => stopEnrollmentFlow(false));

  // ilk durum (bu elementler yoksa zaten sadece console’a yazar)
  setSession(null);
  setProgress(0, targetSamples);
  setStatus("Ready.");
  if (btnStopEnroll) btnStopEnroll.disabled = true;

  // step yapısı bu sayfada varsa başlangıç step’i
  const hasCompanyStep = document.getElementById("step-company");
  if (hasCompanyStep) {
    showStep("step-home");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  // Verify/Identify step sayfasıysa:
  if (document.getElementById("step-method")) {
    showStep("step-method");
  }

  // Enroll sayfasıysa (en azından username inputu varsa):
  if (document.getElementById("btnStartCam") || document.getElementById("username")) {
    bindBiometricUI();
  }
});


// Reset verify flow (same page step navigation, not browser back)
function restartVerify() {
  // kamera açıksa kapat
  if (window.stopCamera) window.stopCamera();
  // tekrar method ekranına dön
  if (window.showStep) window.showStep("step-method");
}


// =========================
// VOICE RECORDING (VERIFY)
// =========================

let voiceRecorder = null;
let voiceChunks = [];
let recordedVoiceB64 = null;

window.startVoiceRecording = async function () {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    voiceRecorder = new MediaRecorder(stream);
    voiceChunks = [];

    voiceRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        voiceChunks.push(e.data);
      }
    };

    voiceRecorder.onstop = async () => {
      const blob = new Blob(voiceChunks, { type: "audio/webm" });

      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result.split(",")[1];
        recordedVoiceB64 = base64data;
        setStatus("Voice recorded.");
      };
      reader.readAsDataURL(blob);
    };

    voiceRecorder.start();
    setStatus("Recording voice...");
  } catch (err) {
    console.error(err);
    setStatus("Microphone error.");
  }
};

window.stopVoiceRecording = function () {
  if (voiceRecorder && voiceRecorder.state !== "inactive") {
    voiceRecorder.stop();
    setStatus("Voice stopped.");
  }
};