import { byId, setText } from "./dom.js";
import { startCamera, stopCamera, captureFrameBase64 } from "./camera.js?v=20260314-camera-mirror";
import {
  apiStartEnroll,
  apiPushFrame,
  apiFinishEnroll,
  apiEnrollVoiceBatch,
  apiGetVoiceChallenge,
} from "./api.js";
import {
  startVoiceRecording,
  stopVoiceRecordingToBase64,
} from "./voice.js";

export function initEnroll() {
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
  const btnStopEnroll = byId("btnStopEnroll");

  const progressTextEl = byId("progressText");
  const progressBarEl = byId("progressBar");
  const angleStatusEl = byId("angleStatus");
  const angleGuideEl = byId("angleGuide");
  const statusTextEl = byId("statusText");

  const btnVoiceStart = byId("btnVoiceStart");
  const voiceChallengePromptEl = byId("voiceChallengePrompt");
  const voiceSampleProgressEl = byId("voiceSampleProgress");
  const voiceTranscriptPreviewEl = byId("voiceTranscriptPreview");
  const audioPreview = byId("audioPreview");
  const voiceStatusEl = byId("voiceStatus");

  const query = new URLSearchParams(window.location.search);
  const storageUsername = (localStorage.getItem("portalUsername") || "").trim();
  const storageRole = (localStorage.getItem("portalRole") || "").trim();
  const queryUsername = (query.get("username") || "").trim();
  const queryRole = (query.get("role") || "").trim();

  const username = storageUsername || queryUsername;
  const role = storageRole || queryRole || "user";
  const isLoggedIn = localStorage.getItem("portalLoggedIn") === "true";

  if (enrollUserEl) {
    enrollUserEl.textContent = username ? username : "Not signed in";
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

  let sessionId = null;
  let isCapturing = false;
  let captureTimer = null;
  let frameInFlight = false;
  let targetSamples = 15;
  let acceptedSamples = 0;
  let voiceB64 = null;
  let voiceChallengeId = null;
  let voiceSamples = [];
  let voiceListening = false;
  let faceEnrollmentCompleted = false;
  let voiceEnrollmentCompleted = false;
  const VOICE_TARGET_SAMPLES = 5;

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

  function setAngleStatus(requiredAngle, angleCounts) {
    const counts = angleCounts || { center: 0, left: 0, right: 0 };
    setText(
      angleStatusEl,
      `Required angle: ${requiredAngle} (center:${counts.center} left:${counts.left} right:${counts.right})`
    );

    const mirroredHint = {
      center: "DUZ BAK: Kameraya tam karsidan bak.",
      left: "Basini SOLA cevir.",
      right: "Basini SAGA cevir.",
    };
    setText(
      angleGuideEl,
      mirroredHint[requiredAngle] || "Yuzunu kamerada istenen yone cevir."
    );
  }

  function updateVoiceSampleProgress() {
    const current = Math.min(voiceSamples.length + 1, VOICE_TARGET_SAMPLES);
    setText(
      voiceSampleProgressEl,
      `Saved ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} samples. Current prompt ${current}/${VOICE_TARGET_SAMPLES}`
    );
  }

  function resetCurrentVoiceCapture() {
    voiceB64 = null;
    setText(voiceTranscriptPreviewEl, "Waiting for phrase...");
    if (audioPreview) {
      audioPreview.pause?.();
      audioPreview.src = "";
      audioPreview.classList.add("hidden");
    }
    if (btnVoiceStart) btnVoiceStart.disabled = false;
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

  function extractSpeakTarget(promptText) {
    const raw = String(promptText || "").trim();
    if (!raw) return "";
    const idx = raw.indexOf(":");
    if (idx >= 0 && idx < raw.length - 1) {
      return raw.slice(idx + 1).trim();
    }
    return raw;
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

    let hit = 0;
    for (const w of expectedWords) {
      if (spoken.includes(w)) hit += 1;
    }

    // Spoken length must also be close to expected length to avoid early partial matches.
    const charRatio = Math.min(1, spoken.length / Math.max(expected.length, 1));

    let score = hit / expectedCount;
    if (spoken.includes(expected)) {
      score = 1.0;
    }

    return { score, hitCount: hit, expectedCount, charRatio };
  }

  async function recognizePhraseUntilMatch(expectedText, { lang = "tr-TR", timeoutMs = 10000 } = {}) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
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
        clearTimeout(timer);
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

        const match = phraseMatchScore(expectedText, transcript);
        if (match.score > bestScore) {
          bestScore = match.score;
          bestTranscript = transcript;
          setText(voiceTranscriptPreviewEl, transcript);
        }

        const latest = event.results[event.resultIndex];
        const isFinal = !!latest?.isFinal;

        // Auto-complete only on final ASR segments and near-complete sentence coverage.
        const enoughWords = match.expectedCount > 0 && match.hitCount >= Math.max(2, match.expectedCount - 2);
        const enoughLength = match.charRatio >= 0.75;
        const strongScore = match.score >= 0.70;

        if (pendingFinalizeTimer) {
          clearTimeout(pendingFinalizeTimer);
          pendingFinalizeTimer = null;
        }

        if (isFinal && strongScore && enoughWords && enoughLength) {
          // Small grace delay to avoid early cut-offs right after finalization.
          pendingFinalizeTimer = setTimeout(() => {
            finish(resolve, { transcript, score: match.score });
          }, 700);
        }
      };

      recognition.onerror = (event) => {
        const code = event?.error ? `SPEECH_${String(event.error).toUpperCase()}` : "SPEECH_ERROR";
        finish(reject, new Error(code));
      };

      const timer = setTimeout(() => {
        if (bestScore >= 0.70 && bestTranscript) {
          finish(resolve, { transcript: bestTranscript, score: bestScore });
          return;
        }
        finish(reject, new Error("PHRASE_NOT_MATCHED"));
      }, timeoutMs);

      recognition.start();
    });
  }

  function setProgress(count, target) {
    acceptedSamples = count;
    targetSamples = target;

    setText(progressTextEl, `${count}/${target}`);

    if (progressBarEl) {
      const pct =
        target > 0 ? Math.min(100, Math.round((count / target) * 100)) : 0;
      progressBarEl.style.width = `${pct}%`;
    }
  }

  function showFaceStep() {
    faceStepEl?.classList.remove("hidden");
    voiceStepEl?.classList.add("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 1 of 2");
    setText(stepTitleEl, "Face Enrollment");
    setText(
      stepDescriptionEl,
      "Start the camera, then begin enrollment. The system will collect multiple face samples automatically."
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
      `Read the shown sentence clearly. After ${VOICE_TARGET_SAMPLES} samples voice enrollment completes automatically.`
    );

    if (!voiceChallengeId) {
      loadVoiceChallenge();
    }
    updateVoiceSampleProgress();
  }

  async function loadVoiceChallenge() {
    try {
      const usedIds = voiceSamples.map((sample) => sample.challenge_id);
      const challenge = await apiGetVoiceChallenge(username, usedIds);
      voiceChallengeId = challenge?.challenge_id || null;
      setText(
        voiceChallengePromptEl,
        challenge?.prompt || "Please read the displayed sentence clearly."
      );
      resetCurrentVoiceCapture();
    } catch (e) {
      console.error(e);
      setText(voiceChallengePromptEl, "Okunacak metin alinamadi.");
      voiceChallengeId = null;
    }
  }

  function showCompleteStep() {
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.add("hidden");
    completeStepEl?.classList.remove("hidden");

    setText(stepIndicatorEl, "Completed");
    setText(stepTitleEl, "Enrollment Completed");
    setText(
      stepDescriptionEl,
      "Your face and voice enrollment steps have been completed successfully."
    );
    setText(
      completeStatusEl,
      "Biometric enrollment completed successfully."
    );
  }

  function updateStepButtons() {
    if (btnGoVoice) {
      btnGoVoice.disabled = !faceEnrollmentCompleted;
    }

    if (btnGoComplete) {
      btnGoComplete.disabled = !voiceEnrollmentCompleted;
    }
  }

  async function stopEnrollmentFlow(doFinish) {
    if (!isCapturing) return;

    isCapturing = false;

    if (captureTimer) {
      clearInterval(captureTimer);
      captureTimer = null;
    }

    if (btnStartEnroll) btnStartEnroll.disabled = false;
    if (btnStopEnroll) btnStopEnroll.disabled = true;

    if (doFinish && sessionId) {
      try {
        const result = await apiFinishEnroll(sessionId);
        const nSamples = result?.n_samples ?? acceptedSamples;
        setStatus(`Saved: ${result?.status || "OK"} (samples: ${nSamples})`);

        const status = (result?.status || "").toUpperCase();
        console.log("[FACE FINISH STATUS]", status);
        console.log("[FACE FINISH NSAMPLES]", nSamples);

        // sample geldiyse veya backend olumlu bir status döndüyse tamam kabul et
        if (
          nSamples > 0 ||
          status === "FACE_STAGED" ||
          status === "ENROLLED" ||
          status === "FACE_UPDATED" ||
          status === "FACE_ALREADY_REGISTERED"
        ) {
          faceEnrollmentCompleted = true;
          updateStepButtons();
          console.log("[FACE COMPLETED]", faceEnrollmentCompleted);
          setStatus(`Face enrollment complete. Switching to voice step...`);
          
          setTimeout(() => {
            console.log("[DEBUG] Calling showVoiceStep()");
            showVoiceStep();
          }, 300);
        }
      } catch (e) {
        console.error(e);
        setStatus(`Finish error: ${e.message || "UNKNOWN_ERROR"}`);
      }
    } else {
      setStatus("Enrollment stopped.");
    }
  }

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

  btnStartEnroll?.addEventListener("click", async () => {
    if (isCapturing) return;

    const hasCamera = !!videoEl?.srcObject;
    if (!hasCamera) {
      setStatus("Start camera first.");
      return;
    }

    try {
      setStatus("Starting enrollment...");
      setProgress(0, 15);
      sessionId = null;

      const startRes = await apiStartEnroll(username, role);
      sessionId = startRes?.session_id || null;
      setProgress(0, startRes?.target || 15);
      setAngleStatus(startRes?.required_angle || "center", {
        center: 0,
        left: 0,
        right: 0,
      });

      isCapturing = true;
      if (btnStartEnroll) btnStartEnroll.disabled = true;
      if (btnStopEnroll) btnStopEnroll.disabled = false;

      setStatus("Enrollment started. Collecting samples...");

      captureTimer = setInterval(async () => {
        if (!isCapturing || frameInFlight) return;

        const faceB64 = captureFrameBase64(videoEl, canvasEl);
        if (!faceB64) return;

        frameInFlight = true;

        try {
          const r = await apiPushFrame(sessionId, faceB64);

          if (r?.accepted) {
            setProgress(r.count ?? acceptedSamples, r.target ?? targetSamples);
            setAngleStatus(r?.required_angle || "center", r?.angle_counts);
          } else if (r?.reason) {
            setStatus(`Collecting... (${r.reason})`);
            setAngleStatus(r?.required_angle || "center", r?.angle_counts);
          }

          const reached =
            r?.reason === "TARGET_REACHED" ||
            ((r?.count ?? 0) >= (r?.target ?? targetSamples) &&
              (r?.target ?? targetSamples) > 0);

          if (reached) {
            setStatus("Target reached. Saving...");
            await stopEnrollmentFlow(true);
          }
        } catch (e) {
          console.error(e);
          setStatus(`Frame error: ${e.message || "UNKNOWN_ERROR"}`);
        } finally {
          frameInFlight = false;
        }
      }, 220);
    } catch (e) {
      console.error(e);
      setStatus(`Start error: ${e.message || "UNKNOWN_ERROR"}`);
      isCapturing = false;
      if (btnStartEnroll) btnStartEnroll.disabled = false;
      if (btnStopEnroll) btnStopEnroll.disabled = true;
    }
  });

  btnStopEnroll?.addEventListener("click", async () => {
    await stopEnrollmentFlow(false);
  });

  btnVoiceStart?.addEventListener("click", async () => {
    const minRecordMs = 2200;
    try {
      if (voiceListening) return;
      if (!voiceChallengeId) {
        setVoiceStatus("Metin hazir degil. Lutfen tekrar deneyin.");
        return;
      }
      if (voiceSamples.length >= VOICE_TARGET_SAMPLES) {
        setVoiceStatus(`Already collected ${VOICE_TARGET_SAMPLES} samples.`);
        return;
      }

      voiceB64 = null;
      const voiceRecordStartedAt = Date.now();
      const promptText = (voiceChallengePromptEl?.textContent || "").trim();
      const expectedPhrase = extractSpeakTarget(promptText);
      if (btnVoiceStart) btnVoiceStart.disabled = true;

      setVoiceStatus("Recording started. Metni okuyun; cumle algilaninca otomatik kaydedilecek.");
      await startVoiceRecording();

      const speech = await recognizePhraseUntilMatch(expectedPhrase, {
        lang: "tr-TR",
        timeoutMs: 11000,
      });

      const elapsed = Date.now() - voiceRecordStartedAt;
      if (elapsed < minRecordMs) {
        await sleep(minRecordMs - elapsed);
      }

      const { blob, b64 } = await stopVoiceRecordingToBase64();
      voiceB64 = b64;

      if (audioPreview) {
        audioPreview.src = URL.createObjectURL(blob);
        audioPreview.classList.remove("hidden");
      }

      setText(voiceTranscriptPreviewEl, speech?.transcript || expectedPhrase || "Recorded phrase.");
      setVoiceStatus("Voice sample captured. Saving sample...");

      if (voiceSamples.length >= VOICE_TARGET_SAMPLES) {
        setVoiceStatus(`Already collected ${VOICE_TARGET_SAMPLES} samples.`);
        if (btnVoiceStart) btnVoiceStart.disabled = true;
        return;
      }

      voiceSamples.push({
        voice_wav_b64: voiceB64,
        challenge_id: voiceChallengeId,
        challenge_answer_text: expectedPhrase,
      });

      setVoiceStatus(`Sample ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} saved.`);
      updateVoiceSampleProgress();

      if (voiceSamples.length < VOICE_TARGET_SAMPLES) {
        await loadVoiceChallenge();
        setVoiceStatus(
          `Sample ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} saved. Sonraki cumle otomatik yüklendi.`
        );
        return;
      }

      if (btnVoiceStart) btnVoiceStart.disabled = true;
      setText(
        voiceChallengePromptEl,
        `${VOICE_TARGET_SAMPLES} samples captured. Finalizing voice enrollment...`
      );
      setVoiceStatus(`Saving merged voice template from ${VOICE_TARGET_SAMPLES} samples...`);

      const res = await apiEnrollVoiceBatch(username, role, voiceSamples);
      console.log("[VOICE ENROLL STATUS]", res?.status, res?.reason || "");

      if ((res?.status || "").toUpperCase() === "FAILED") {
        const detail = res?.detail ? ` (${JSON.stringify(res.detail)})` : "";
        setVoiceStatus(`Voice enroll failed: ${res?.reason || "UNKNOWN_ERROR"}${detail}`);
      } else {
        setVoiceStatus(res?.status ? `Voice enrolled: ${res.status}` : "Voice enrolled.");
      }

      const status = (res?.status || "").toUpperCase();
      if (
        status === "VOICE_ENROLLED" ||
        status === "VOICE_UPDATED" ||
        status === "VOICE_ALREADY_REGISTERED"
      ) {
        voiceEnrollmentCompleted = true;
        updateStepButtons();
        setVoiceStatus("Voice enrollment complete. Click 'Finish Enrollment' to complete.");
        setText(
          voiceSampleProgressEl,
          `Saved ${VOICE_TARGET_SAMPLES}/${VOICE_TARGET_SAMPLES} samples. Voice enrollment completed.`
        );
      }
    } catch (e) {
      console.error(e);
      try {
        await stopVoiceRecordingToBase64();
      } catch {}

      const errCode = String(e?.message || "").toUpperCase();
      if (errCode === "PHRASE_NOT_MATCHED" || errCode.startsWith("SPEECH_")) {
        setVoiceStatus("Cumle tam algilanamadi. Metni net okuyup tekrar deneyin.");
      } else {
        setVoiceStatus(`Voice enroll failed: ${e.message || "UNKNOWN_ERROR"}`);
      }
      if (btnVoiceStart) btnVoiceStart.disabled = false;
    } finally {
      voiceListening = false;
    }
  });

  btnGoVoice?.addEventListener("click", () => {
    if (!faceEnrollmentCompleted) {
      setStatus("Complete face enrollment first.");
      return;
    }
    showVoiceStep();
  });

  btnBackToFace?.addEventListener("click", () => {
    if (voiceListening) {
      stopVoiceRecordingToBase64().catch(() => {});
      voiceListening = false;
      if (btnVoiceStart) btnVoiceStart.disabled = false;
    }
    showFaceStep();
  });

  btnGoComplete?.addEventListener("click", () => {
    if (!voiceEnrollmentCompleted) {
      setVoiceStatus("Complete voice enrollment first.");
      return;
    }
    showCompleteStep();
  });

  setProgress(0, targetSamples);
  setAngleStatus("center", { center: 0, left: 0, right: 0 });
  updateVoiceSampleProgress();
  setText(voiceTranscriptPreviewEl, "Waiting for phrase...");
  setStatus("Ready.");
  setVoiceStatus("Ready.");

  if (btnStopEnroll) btnStopEnroll.disabled = true;

  faceEnrollmentCompleted = false;
  voiceEnrollmentCompleted = false;
  updateStepButtons();
  showFaceStep();
}