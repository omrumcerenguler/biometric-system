let selectedCompany = null;
let selectedMethod = null;

// camera
let stream = null;

// voice
let mediaRecorder = null;
let audioChunks = [];
let recordedAudioBase64 = null;

/* =========================
   STEP NAVIGATION
========================= */
function selectCompany(company) {
  selectedCompany = company;
  document.getElementById("step-company").classList.add("hidden");
  document.getElementById("step-method").classList.remove("hidden");
}

async function selectMethod(method) {
  selectedMethod = method;

  document.getElementById("step-method").classList.add("hidden");

  if (method === "face") {
    document.getElementById("step-face").classList.remove("hidden");
    await startCamera();
  }

  if (method === "voice") {
    document.getElementById("step-voice").classList.remove("hidden");
    // voice için kamera gerekmez
  }
}

/* =========================
   CAMERA
========================= */
async function startCamera() {
  const video = document.getElementById("video");

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });

    video.srcObject = stream;
    await video.play();
  } catch (err) {
    console.error("Camera error:", err);
    alert("Camera access denied or not available");
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
}

/* =========================
   FACE CAPTURE & SEND
========================= */
async function captureFace() {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const imageBase64 = canvas.toDataURL("image/jpeg").split(",")[1];

  // FACE-ONLY payload (voice yok!)
  const payload = {
    username: "demo_user",
    face_image_b64: imageBase64,
  };

  await sendVerify(payload);
}

/* =========================
   VOICE RECORD & SEND
========================= */
async function startVoiceRecord() {
  recordedAudioBase64 = null;
  audioChunks = [];

  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });

    mediaRecorder = new MediaRecorder(audioStream);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // stop mic tracks
      audioStream.getTracks().forEach((t) => t.stop());

      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
      recordedAudioBase64 = await blobToBase64(blob);

      // UI: preview audio (opsiyonel)
      const audioEl = document.getElementById("audio-preview");
      if (audioEl) {
        audioEl.src = URL.createObjectURL(blob);
        audioEl.classList.remove("hidden");
      }

      // kayıt bittiğinde butonları güncelle
      document.getElementById("btn-voice-start").disabled = false;
      document.getElementById("btn-voice-stop").disabled = true;
      document.getElementById("btn-voice-send").disabled = false;
    };

    mediaRecorder.start();

    document.getElementById("btn-voice-start").disabled = true;
    document.getElementById("btn-voice-stop").disabled = false;
    document.getElementById("btn-voice-send").disabled = true;
  } catch (err) {
    console.error("Mic error:", err);
    alert("Microphone access denied or not available");
  }
}

function stopVoiceRecord() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

async function sendVoice() {
  if (!recordedAudioBase64) {
    alert("Please record your voice first.");
    return;
  }

  // VOICE-ONLY payload (face yok!)
  const payload = {
    username: "demo_user",
    voice_wav_b64: recordedAudioBase64,
  };

  await sendVerify(payload);
}

/* =========================
   COMMON: SEND VERIFY
========================= */
async function sendVerify(payload) {
  try {
    const res = await fetch("http://127.0.0.1:8000/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const text = await res.text();
    console.log("Status:", res.status);
    console.log("Response:", text);

    if (!res.ok) {
      alert("Backend error: " + res.status + "\n" + text);
      return;
    }

    const data = JSON.parse(text);
    showResult(data);
  } catch (err) {
    console.error(err);
    alert("Backend connection failed");
  }
}

/* =========================
   UI: RESULT
========================= */
function showResult(data) {
  // face ekranındaysak kamerayı kapat
  stopCamera();

  // voice kaydı varsa recorder temizliği
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try { mediaRecorder.stop(); } catch (_) {}
  }

  // tüm step'leri gizle
  document.getElementById("step-company").classList.add("hidden");
  document.getElementById("step-method").classList.add("hidden");
  document.getElementById("step-face").classList.add("hidden");
  if (document.getElementById("step-voice")) {
    document.getElementById("step-voice").classList.add("hidden");
  }

  // result göster
  document.getElementById("step-result").classList.remove("hidden");

  document.getElementById("result-decision").innerText =
    "Decision: " + (data.decision ?? "N/A");

  document.getElementById("face-score").innerText =
    (data.face_score ?? 0).toFixed ? (data.face_score ?? 0).toFixed(2) : (data.face_score ?? 0);

  document.getElementById("voice-score").innerText =
    (data.voice_score ?? 0).toFixed ? (data.voice_score ?? 0).toFixed(2) : (data.voice_score ?? 0);

  document.getElementById("fusion-score").innerText =
    (data.fusion_score ?? 0).toFixed ? (data.fusion_score ?? 0).toFixed(2) : (data.fusion_score ?? 0);
}

function restart() {
  stopCamera();
  location.reload();
}

/* =========================
   HELPERS
========================= */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      // data:audio/webm;base64,XXXX -> XXXX
      const base64 = String(reader.result).split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

