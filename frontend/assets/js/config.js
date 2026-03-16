// API configuration
export const API_BASE = "http://127.0.0.1:8000";

// endpoints
export const ENDPOINTS = {
  identify: "/identify",
  verify: "/auth/verify",
};

// voice recording
export const VOICE_CONFIG = {
  sampleRate: 16000,
  maxDurationSec: 5
};

// verification strategy
export const VERIFY_CONFIG = {
  minChallenges: 2,
  maxChallenges: 5,
  fusionThreshold: 0.75
};

// debug mode
export const DEBUG = true;