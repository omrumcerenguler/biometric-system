let mediaStream = null;

export async function startCamera(videoEl) {
  if (!videoEl) throw new Error("VIDEO_ELEMENT_MISSING");

  // stream varsa tekrar bağla
  if (mediaStream) {
    videoEl.srcObject = mediaStream;
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
  ctx.drawImage(videoEl, 0, 0, w, h);

  const dataUrl = canvasEl.toDataURL("image/jpeg", quality);
  return dataUrl.split(",")[1];
}