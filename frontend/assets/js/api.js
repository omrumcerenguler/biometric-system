import { API_BASE } from "./config.js";

// küçük helper: URL birleştir (çift slash olmasın)
function joinUrl(base, path) {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

async function jsonFetch(path, options = {}) {
  const url = joinUrl(API_BASE, path);

  let res;
  try {
    res = await fetch(url, options);
  } catch (e) {
    throw new Error("NETWORK_ERROR");
  }

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP_${res.status}`;
    throw new Error(msg);
  }

  return data;
}

// -------------------------
// ENROLL (FACE - session based)
// -------------------------
export function apiStartEnroll(username, role) {
  return jsonFetch("/enroll/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, role }),
  });
}

export function apiPushFrame(session_id, face_image_b64) {
  return jsonFetch("/enroll/frame", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, face_image_b64 }),
  });
}

export function apiFinishEnroll(session_id) {
  return jsonFetch("/enroll/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id }),
  });
}

// -------------------------
// ENROLL (VOICE - identity template)
// -------------------------
export function apiEnrollVoice(username, role, voice_wav_b64) {
  return jsonFetch("/enroll/voice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, role, voice_wav_b64 }),
  });
}

// -------------------------
// IDENTIFY (1:N) - Face
// -------------------------
export function apiIdentifyFace(face_image_b64) {
  // 307 redirect yememek için /identify/ daha stabil
  return jsonFetch("/identify/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ face_image_b64 }),
  });
}

// -------------------------
// AUTH VERIFY (Face + Voice)  (username YOK)
// -------------------------
export function apiAuthVerify({ face_image_b64, voice_wav_b64 }) {
  return jsonFetch("/auth/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ face_image_b64, voice_wav_b64 }),
  });
}