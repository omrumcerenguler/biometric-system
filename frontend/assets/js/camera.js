let mediaStream = null;
// Keep preview and captured frame orientation consistent.
// false => non-mirrored (natural camera orientation)
// true  => mirrored (selfie mirror view)
const USE_MIRRORED_CAMERA = true;

export async function startCamera(videoEl) {
  if (!videoEl) throw new Error("VIDEO_ELEMENT_MISSING");

  // stream varsa tekrar bağla
  if (mediaStream) {
    videoEl.srcObject = mediaStream;
    videoEl.dataset.cameraMirror = USE_MIRRORED_CAMERA ? "true" : "false";
    videoEl.classList.toggle("camera-mirrored", USE_MIRRORED_CAMERA);
    videoEl.classList.toggle("camera-unmirrored", !USE_MIRRORED_CAMERA);
    videoEl.style.transform = USE_MIRRORED_CAMERA ? "scaleX(-1)" : "scaleX(1)";
    videoEl.style.webkitTransform = USE_MIRRORED_CAMERA ? "scaleX(-1)" : "scaleX(1)";
    videoEl.style.transformOrigin = "center center";
    await videoEl.play().catch(() => {});
    return mediaStream;
  }

  mediaStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user" },
    audio: false,
  });

  videoEl.muted = true;
  videoEl.playsInline = true;
  videoEl.srcObject = mediaStream;
  videoEl.dataset.cameraMirror = USE_MIRRORED_CAMERA ? "true" : "false";
  videoEl.classList.toggle("camera-mirrored", USE_MIRRORED_CAMERA);
  videoEl.classList.toggle("camera-unmirrored", !USE_MIRRORED_CAMERA);
  videoEl.style.transform = USE_MIRRORED_CAMERA ? "scaleX(-1)" : "scaleX(1)";
  videoEl.style.webkitTransform = USE_MIRRORED_CAMERA ? "scaleX(-1)" : "scaleX(1)";
  videoEl.style.transformOrigin = "center center";
  await videoEl.play();

  return mediaStream;
}

export function stopCamera(videoEls = []) {
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  videoEls.forEach((v) => {
    if (v) v.srcObject = null;
  });
}

export function captureFrameBase64(videoEl, canvasEl, quality = 0.85) {
  if (!videoEl || !canvasEl) return null;

  const w = videoEl.videoWidth;
  const h = videoEl.videoHeight;
  if (!w || !h) return null;

  canvasEl.width = w;
  canvasEl.height = h;

  const ctx = canvasEl.getContext("2d");
  if (USE_MIRRORED_CAMERA) {
    // Keep backend orientation same as preview when mirror mode is enabled.
    ctx.save();
    ctx.translate(w, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(videoEl, 0, 0, w, h);
    ctx.restore();
  } else {
    ctx.drawImage(videoEl, 0, 0, w, h);
  }

  const dataUrl = canvasEl.toDataURL("image/jpeg", quality);
  return dataUrl.split(",")[1];
}