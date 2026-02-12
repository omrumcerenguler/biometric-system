let selectedCompany = null;
let selectedMethod = null;

// camera
let stream = null;

// voice
let mediaRecorder = null;
let audioChunks = [];
let recordedAudioBase64 = null;
let recordedAudioMime = null;

/* =========================
   STEP NAVIGATION
========================= */
function selectCompany(company) {
  selectedCompany = company;
  hideAllSteps();
  document.getElementById("step-method").classList.remove("hidden");
}

async function selectMethod(method) {
  selectedMethod = method;

  hideAllSteps();

  if (method === "face") {
    document.getElementById("step-face").classList.remove("hidden");
    await startCamera();
  }

  if (method === "voice") {
    stopCamera();
    document.getElementById("step-voice").classList.remove("hidden");
    // voice için kamera gerekmez
  }
}

function hideAllSteps() {
  const ids = ["step-company", "step-method", "step-face", "step-voice", "step-result"];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });
}

/* =========================
   CAMERA
========================= */
async function startCamera() {
  const video = document.getElementById("video");

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
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
  if (!video.videoWidth || !video.videoHeight) {
    alert("Camera not ready yet. Please wait 1-2 seconds.");
    return;
  }

  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const imageBase64 = canvas.toDataURL("image/jpeg").split(",")[1];

  // FACE-ONLY payload
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
  recordedAudioMime = null;
  audioChunks = [];

  // button states (optional)
  const btnStart = document.getElementById("btn-voice-start");
  const btnStop = document.getElementById("btn-voice-stop");
  const btnSend = document.getElementById("btn-voice-send");

  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });

    mediaRecorder = new MediaRecorder(audioStream);
    recordedAudioMime = mediaRecorder.mimeType;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // stop mic tracks
      audioStream.getTracks().forEach((t) => t.stop());

      const blob = new Blob(audioChunks, { type: recordedAudioMime || "audio/webm" });
      recordedAudioBase64 = await blobToBase64(blob);

      // preview audio (optional)
      const audioEl = document.getElementById("audio-preview");
      if (audioEl) {
        audioEl.src = URL.createObjectURL(blob);
        audioEl.classList.remove("hidden");
      }

      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;
      if (btnSend) btnSend.disabled = false;

      console.log("Recorded voice mime:", recordedAudioMime);
      console.log("Recorded voice base64 length:", recordedAudioBase64?.length);
    };

    mediaRecorder.start();

    if (btnStart) btnStart.disabled = true;
    if (btnStop) btnStop.disabled = false;
    if (btnSend) btnSend.disabled = true;
  } catch (err) {
    console.error("Mic error:", err);
    alert("Microphone access denied or not available");

    if (btnStart) btnStart.disabled = false;
    if (btnStop) btnStop.disabled = true;
    if (btnSend) btnSend.disabled = true;
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

  // VOICE-ONLY payload
  // NOTE: This is usually WEBM base64, not WAV.
  // Backend must be able to decode it.
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
    console.log("Raw response:", text);

    if (!res.ok) {
      alert("Backend error: " + res.status + "\n" + text);
      return;
    }

    const data = JSON.parse(text);
    console.log("API result:", data);
    console.log("reason:", data.reason);

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
  stopCamera();

  // hide steps
  hideAllSteps();
  document.getElementById("step-result").classList.remove("hidden");

  // decision
  document.getElementById("result-decision").innerText =
    "Decision: " + (data.decision ?? "N/A");

  // scores
  document.getElementById("face-score").innerText = toFixedSafe(data.face_score, 2);
  document.getElementById("voice-score").innerText = toFixedSafe(data.voice_score, 2);
  document.getElementById("fusion-score").innerText = toFixedSafe(data.fusion_score, 2);

  // OPTIONAL: show reason / instruction if you have element(s)
  const reasonEl = document.getElementById("result-reason");
  if (reasonEl) reasonEl.innerText = data.reason ?? "";

  const instrEl = document.getElementById("liveness-instruction");
  if (instrEl) instrEl.innerText = data.face_liveness_instruction ?? "";
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

function toFixedSafe(value, digits) {
  const num = Number(value ?? 0);
  if (Number.isFinite(num)) return num.toFixed(digits);
  return "0.00";
}
