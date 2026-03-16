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
// ENROLL (BIOMETRIC - unified)
// -------------------------
export function apiEnrollBiometric(username, role, face_frames_b64, voice_samples) {
  return jsonFetch("/enroll/biometric", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, role, face_frames_b64, voice_samples }),
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

export function apiIdentifyVoiceChallenge() {
  return jsonFetch("/identify/voice-challenge", {
    method: "GET",
  });
}

export function apiValidateIdentifyVoiceChallenge(challenge_id, answer_text) {
  return jsonFetch("/identify/voice-challenge/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id, answer_text }),
  });
}

export function apiIdentifyPoseCheck(
  face_image_b64,
  required_turn,
  reference_face_image_b64 = null,
  expected_user_id = null
) {
  return jsonFetch("/identify/pose-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      face_image_b64,
      required_turn,
      reference_face_image_b64,
      expected_user_id,
      require_eyes_open: true,
    }),
  });
}

export function apiIdentifyBlinkCheck(
  face_frames_b64,
  reference_face_image_b64 = null,
  expected_user_id = null
) {
  return jsonFetch("/identify/blink-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      face_frames_b64,
      reference_face_image_b64,
      expected_user_id,
    }),
  });
}

// -------------------------
// AUTH VERIFY (Face + Voice)
// -------------------------
export function apiAuthVerify({ face_image_b64, voice_wav_b64 }) {
  return jsonFetch("/auth/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ face_image_b64, voice_wav_b64 }),
  });
}