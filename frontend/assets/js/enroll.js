import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js?v=20260314-camera-mirror";
import { apiEnrollBiometric } from "./api.js";
import {
  startVoiceRecording,
  stopVoiceRecordingToBase64,
} from "./voice.js";

export function initEnroll() {
  // ---------- DOM ----------
  const enrollUserEl = byId("enrollUser");

  const faceStepEl = byId("faceStep");
  const voiceStepEl = byId("voiceStep");
  const completeStepEl = byId("completeStep");

  const stepIndicatorEl = byId("stepIndicator");
  const stepTitleEl = byId("stepTitle");
  const stepDescriptionEl = byId("stepDescription");

  const btnGoVoice = byId("btnGoVoice");
  const btnBackToFace = byId("btnBackToFace");
  const btnGoComplete = byId("btnGoComplete");
  const completeStatusEl = byId("completeStatus");

  const videoEl = byId("camVideo");
  const canvasEl = byId("camCanvas");

  const btnStartCam = byId("btnStartCam");
  const btnStopCam = byId("btnStopCam");
  const btnStartEnroll = byId("btnStartEnroll");

  const progressTextEl = byId("progressText");
  const progressBarEl = byId("progressBar");
  const statusTextEl = byId("statusText");

  const btnVoiceStart = byId("btnVoiceStart");
  const voiceChallengePromptEl = byId("voiceChallengePrompt");
  const voiceSampleProgressEl = byId("voiceSampleProgress");
  const voiceTranscriptPreviewEl = byId("voiceTranscriptPreview");
  const audioPreview = byId("audioPreview");
  const voiceStatusEl = byId("voiceStatus");

  // ---------- Auth / User ----------
  const query = new URLSearchParams(window.location.search);
  const storageUsername = (localStorage.getItem("portalUsername") || "").trim();
  const storageRole = (localStorage.getItem("portalRole") || "").trim();
  const queryUsername = (query.get("username") || "").trim();
  const queryRole = (query.get("role") || "").trim();

  const username = storageUsername || queryUsername;
  const role = storageRole || queryRole || "user";
  const isLoggedIn = localStorage.getItem("portalLoggedIn") === "true";

  if (enrollUserEl) {
    enrollUserEl.textContent = username || "Not signed in";
  }

  if (!storageUsername && queryUsername) {
    localStorage.setItem("portalUsername", queryUsername);
  }
  if (!storageRole && queryRole) {
    localStorage.setItem("portalRole", queryRole);
  }

  if ((!isLoggedIn && !queryUsername) || !username) {
    window.location.href = "../portal/office_login.html";
    return;
  }

  // ---------- State ----------
  const FACE_TARGET_SAMPLES = 15;
  const VOICE_TARGET_SAMPLES = 5;

  const VOICE_PROMPTS = [
    "Bugun biyometrik kayit islemi yapiyorum",
    "Kameraya bakiyorum ve net konusuyorum",
    "Ses ve yuz verilerim sisteme kaydedilecek",
    "Bu sistem guvenli giris icin kullaniliyor",
    "Kayit islemimi basariyla tamamlamak istiyorum",
  ];

  let faceSamples = [];
  let voiceSamples = [];
  let voiceListening = false;

  let faceEnrollmentCompleted = false;
  let voiceEnrollmentCompleted = false;
  let biometricSubmitCompleted = false;

  // ---------- Helpers ----------
  function setStatus(msg) {
    setText(statusTextEl, msg);
    console.log("[ENROLL]", msg);
  }

  function setVoiceStatus(msg) {
    setText(voiceStatusEl, msg);
    console.log("[VOICE]", msg);
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[ı]/g, "i")
      .replace(/[ş]/g, "s")
      .replace(/[ç]/g, "c")
      .replace(/[ö]/g, "o")
      .replace(/[ü]/g, "u")
      .replace(/[ğ]/g, "g")
      .replace(/[^a-z0-9 ]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function phraseMatchScore(expectedText, spokenText) {
    const expected = normalizeText(expectedText);
    const spoken = normalizeText(spokenText);

    if (!expected || !spoken) {
      return { score: 0, hitCount: 0, expectedCount: 0, charRatio: 0 };
    }

    const expectedWords = expected.split(" ").filter(Boolean);
    const expectedCount = expectedWords.length;

    if (!expectedCount) {
      return { score: 0, hitCount: 0, expectedCount: 0, charRatio: 0 };
    }

    let hitCount = 0;
    for (const word of expectedWords) {
      if (spoken.includes(word)) hitCount += 1;
    }

    const charRatio = Math.min(1, spoken.length / Math.max(expected.length, 1));

    let score = hitCount / expectedCount;
    if (spoken.includes(expected)) {
      score = 1;
    }

    return { score, hitCount, expectedCount, charRatio };
  }

  async function recognizePhraseUntilMatch(
    expectedText,
    { lang = "tr-TR", timeoutMs = 10000 } = {}
  ) {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      throw new Error("SPEECH_RECOGNITION_UNSUPPORTED");
    }

    return new Promise((resolve, reject) => {
      const recognition = new SpeechRecognition();
      let done = false;
      let bestTranscript = "";
      let bestScore = 0;
      let pendingFinalizeTimer = null;

      const finish = (fn, value) => {
        if (done) return;
        done = true;
        clearTimeout(timeoutTimer);
        if (pendingFinalizeTimer) {
          clearTimeout(pendingFinalizeTimer);
          pendingFinalizeTimer = null;
        }
        try {
          recognition.stop();
        } catch {}
        fn(value);
      };

      recognition.lang = lang;
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i += 1) {
          transcript += `${event.results[i][0]?.transcript || ""} `;
        }

        transcript = transcript.trim();
        if (!transcript) return;

        setText(voiceTranscriptPreviewEl, transcript);

        const match = phraseMatchScore(expectedText, transcript);
        if (match.score > bestScore) {
          bestScore = match.score;
          bestTranscript = transcript;
        }

        const latest = event.results[event.resultIndex];
        const isFinal = !!latest?.isFinal;

        const enoughWords =
          match.expectedCount > 0 &&
          match.hitCount >= Math.max(2, match.expectedCount - 1);
        const enoughLength = match.charRatio >= 0.75;
        const strongScore = match.score >= 0.7;

        if (pendingFinalizeTimer) {
          clearTimeout(pendingFinalizeTimer);
          pendingFinalizeTimer = null;
        }

        if (isFinal && enoughWords && enoughLength && strongScore) {
          pendingFinalizeTimer = setTimeout(() => {
            finish(resolve, { transcript, score: match.score });
          }, 700);
        }
      };

      recognition.onerror = (event) => {
        const code = event?.error
          ? `SPEECH_${String(event.error).toUpperCase()}`
          : "SPEECH_ERROR";
        finish(reject, new Error(code));
      };

      const timeoutTimer = setTimeout(() => {
        if (bestScore >= 0.7 && bestTranscript) {
          finish(resolve, { transcript: bestTranscript, score: bestScore });
          return;
        }
        finish(reject, new Error("PHRASE_NOT_MATCHED"));
      }, timeoutMs);

      recognition.start();
    });
  }

  function resetAudioPreview() {
    if (!audioPreview) return;
    audioPreview.pause?.();
    audioPreview.src = "";
    audioPreview.classList.add("hidden");
  }

  function updateFaceProgress() {
    const current = Math.min(faceSamples.length, FACE_TARGET_SAMPLES);
    setText(progressTextEl, `${current}/${FACE_TARGET_SAMPLES}`);

    if (progressBarEl) {
      const pct = Math.min(
        100,
        Math.round((current / FACE_TARGET_SAMPLES) * 100)
      );
      progressBarEl.style.width = `${pct}%`;
    }
  }

  function updateVoiceSampleProgress() {
    setText(
      voiceSampleProgressEl,
      `Saved ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} samples`
    );
  }

  function getCurrentVoicePrompt() {
    return VOICE_PROMPTS[voiceSamples.length] || "";
  }

  function updateVoicePrompt() {
    if (voiceEnrollmentCompleted) {
      setText(
        voiceChallengePromptEl,
        `${VOICE_TARGET_SAMPLES} samples captured. Voice enrollment completed.`
      );
      return;
    }

    const prompt = getCurrentVoicePrompt();
    setText(
      voiceChallengePromptEl,
      prompt || "Please read the displayed sentence clearly."
    );
  }

  function showFaceStep() {
    faceStepEl?.classList.remove("hidden");
    voiceStepEl?.classList.add("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 1 of 2");
    setText(stepTitleEl, "Face Enrollment");
    setText(
      stepDescriptionEl,
      "Start the camera and collect face samples first."
    );
  }

  function showVoiceStep() {
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.remove("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 2 of 2");
    setText(stepTitleEl, "Voice Enrollment");
    setText(
      stepDescriptionEl,
      `Record ${VOICE_TARGET_SAMPLES} voice samples by reading the shown sentence.`
    );

    updateVoicePrompt();
    updateVoiceSampleProgress();
  }

  function showCompleteStep(message = "Biometric enrollment completed successfully.") {
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.add("hidden");
    completeStepEl?.classList.remove("hidden");

    setText(stepIndicatorEl, "Completed");
    setText(stepTitleEl, "Enrollment Completed");
    setText(
      stepDescriptionEl,
      "Your face and voice enrollment steps have been completed successfully."
    );
    setText(completeStatusEl, message);
  }

  function updateStepButtons() {
    if (btnGoVoice) {
      btnGoVoice.disabled = !faceEnrollmentCompleted;
    }

    if (btnGoComplete) {
      btnGoComplete.disabled =
        !faceEnrollmentCompleted ||
        !voiceEnrollmentCompleted ||
        biometricSubmitCompleted;
    }

    if (btnVoiceStart) {
      btnVoiceStart.disabled =
        voiceListening ||
        voiceEnrollmentCompleted ||
        biometricSubmitCompleted;
    }

    if (btnStartEnroll) {
      btnStartEnroll.disabled = biometricSubmitCompleted;
    }
  }

  // ---------- Camera ----------
  btnStartCam?.addEventListener("click", async () => {
    try {
      setStatus("Requesting camera...");
      await startCamera(videoEl);
      setStatus("Camera ready.");
    } catch (e) {
      console.error(e);
      setStatus(`Camera error: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  btnStopCam?.addEventListener("click", () => {
    stopCamera([videoEl]);
    setStatus("Camera stopped.");
  });

  // ---------- Face ----------
  btnStartEnroll?.addEventListener("click", async () => {
    try {
      if (faceEnrollmentCompleted) {
        setStatus("Face samples already collected.");
        return;
      }

      const hasCamera = !!videoEl?.srcObject;
      if (!hasCamera) {
        setStatus("Start camera first.");
        return;
      }

      setStatus("Collecting face samples...");
      if (btnStartEnroll) btnStartEnroll.disabled = true;

      faceSamples = [];
      updateFaceProgress();

      for (let i = 0; i < FACE_TARGET_SAMPLES; i += 1) {
        const faceB64 = captureFrameBase64(videoEl, canvasEl);

        if (faceB64) {
          faceSamples.push(faceB64);
          updateFaceProgress();
        }

        await sleep(220);
      }

      if (faceSamples.length < FACE_TARGET_SAMPLES) {
        setStatus(
          `Not enough face samples collected (${faceSamples.length}/${FACE_TARGET_SAMPLES}). Please try again.`
        );
        if (btnStartEnroll) btnStartEnroll.disabled = false;
        return;
      }

      faceEnrollmentCompleted = true;
      setStatus(
        `Face samples completed (${faceSamples.length}/${FACE_TARGET_SAMPLES}).`
      );
      updateStepButtons();

      setTimeout(() => {
        showVoiceStep();
      }, 250);
    } catch (e) {
      console.error(e);
      setStatus(`Face collection error: ${e.message || "UNKNOWN_ERROR"}`);
      if (!biometricSubmitCompleted && btnStartEnroll) {
        btnStartEnroll.disabled = false;
      }
    }
  });

  // ---------- Voice ----------
  btnVoiceStart?.addEventListener("click", async () => {
    const minRecordMs = 2200;

    try {
      if (voiceListening) return;

      if (!faceEnrollmentCompleted) {
        setVoiceStatus("Complete face enrollment first.");
        return;
      }

      if (voiceEnrollmentCompleted) {
        setVoiceStatus(`Already collected ${VOICE_TARGET_SAMPLES} samples.`);
        return;
      }

      const promptText = getCurrentVoicePrompt();
      if (!promptText) {
        setVoiceStatus("No prompt available.");
        return;
      }

      voiceListening = true;
      updateStepButtons();

      resetAudioPreview();
      setText(voiceTranscriptPreviewEl, "Listening...");
      setVoiceStatus("Recording started. Read the sentence clearly.");

      const recordStartedAt = Date.now();
      await startVoiceRecording();

      const speech = await recognizePhraseUntilMatch(promptText, {
        lang: "tr-TR",
        timeoutMs: 11000,
      });

      const elapsed = Date.now() - recordStartedAt;
      if (elapsed < minRecordMs) {
        await sleep(minRecordMs - elapsed);
      }

      const { blob, b64 } = await stopVoiceRecordingToBase64();

      if (audioPreview) {
        audioPreview.src = URL.createObjectURL(blob);
        audioPreview.classList.remove("hidden");
      }

      setText(voiceTranscriptPreviewEl, speech?.transcript || promptText);

      voiceSamples.push({
        voice_wav_b64: b64,
        challenge_answer_text: promptText,
        transcript_text: speech?.transcript || "",
      });

      updateVoiceSampleProgress();

      if (voiceSamples.length >= VOICE_TARGET_SAMPLES) {
        voiceEnrollmentCompleted = true;
        updateVoicePrompt();
        setVoiceStatus(
          `Voice samples completed (${voiceSamples.length}/${VOICE_TARGET_SAMPLES}).`
        );
      } else {
        updateVoicePrompt();
        setVoiceStatus(
          `Sample ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} saved.`
        );
      }

      updateStepButtons();
    } catch (e) {
      console.error(e);

      try {
        await stopVoiceRecordingToBase64();
      } catch {}

      const errCode = String(e?.message || "").toUpperCase();
      if (errCode === "PHRASE_NOT_MATCHED" || errCode.startsWith("SPEECH_")) {
        setVoiceStatus("Sentence was not matched clearly. Please try again.");
      } else {
        setVoiceStatus(`Voice recording failed: ${e.message || "UNKNOWN_ERROR"}`);
      }
    } finally {
      voiceListening = false;
      updateStepButtons();
    }
  });

  // ---------- Navigation ----------
  btnGoVoice?.addEventListener("click", () => {
    if (!faceEnrollmentCompleted) {
      setStatus("Complete face enrollment first.");
      return;
    }
    showVoiceStep();
  });

  btnBackToFace?.addEventListener("click", async () => {
    if (voiceListening) {
      try {
        await stopVoiceRecordingToBase64();
      } catch {}
      voiceListening = false;
    }

    updateStepButtons();
    showFaceStep();
  });

  // ---------- Final submit ----------
  btnGoComplete?.addEventListener("click", async () => {
    try {
      if (!faceEnrollmentCompleted) {
        setStatus("Complete face enrollment first.");
        return;
      }

      if (!voiceEnrollmentCompleted) {
        setVoiceStatus("Complete voice enrollment first.");
        return;
      }

      if (!faceSamples.length || faceSamples.length < FACE_TARGET_SAMPLES) {
        setStatus("Face samples are missing.");
        return;
      }

      if (!voiceSamples.length || voiceSamples.length < VOICE_TARGET_SAMPLES) {
        setVoiceStatus("Voice samples are missing.");
        return;
      }

      biometricSubmitCompleted = false;
      updateStepButtons();

      setStatus("Sending biometric enrollment...");
      setVoiceStatus("Submitting biometric data...");

      const response = await apiEnrollBiometric(
        username,
        role,
        faceSamples,
        voiceSamples
      );

      biometricSubmitCompleted = true;
      updateStepButtons();

      const successMessage =
        response?.message || "Biometric enrollment completed successfully.";

      setStatus(successMessage);
      setVoiceStatus("Enrollment completed.");
      showCompleteStep(successMessage);
    } catch (e) {
      console.error(e);
      biometricSubmitCompleted = false;
      updateStepButtons();

      const msg = e?.message || "UNKNOWN_ERROR";
      setStatus(`Enrollment failed: ${msg}`);
      setVoiceStatus(`Enrollment failed: ${msg}`);
    }
  });

  // ---------- Init ----------
  updateFaceProgress();
  updateVoiceSampleProgress();
  updateVoicePrompt();
  setText(voiceTranscriptPreviewEl, "Waiting for phrase...");
  setStatus("Ready.");
  setVoiceStatus("Ready.");

  faceEnrollmentCompleted = false;
  voiceEnrollmentCompleted = false;
  biometricSubmitCompleted = false;

  updateStepButtons();
  showFaceStep();
}