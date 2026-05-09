import { byId, setText } from "./dom.js";
import {
  startCamera,
  stopCamera,
  captureFrameBase64,
} from "./camera.js?v=20260314-camera-mirror";
import {
  apiEnrollBiometric,
  apiIdentifyPoseCheck,
  apiPrecheckFace,
  apiPrecheckVoice,
  apiSaveSecurityAnswers,
  apiGetSecurityQuestions,
} from "./api.js";
import { startVoiceRecording, stopVoiceRecordingToBase64 } from "./voice.js";

export function initEnroll() {
  // ---------- DOM ----------
  const enrollUserEl = byId("enrollUser");

  const faceStepEl = byId("faceStep");
  const voiceStepEl = byId("voiceStep");
  const completeStepEl = byId("completeStep");
  const securityStepEl = byId("securityStep");

  const stepIndicatorEl = byId("stepIndicator");
  const stepTitleEl = byId("stepTitle");
  const stepDescriptionEl = byId("stepDescription");

  const btnGoVoice = byId("btnGoVoice");
  const btnBackToFace = byId("btnBackToFace");
  const btnGoComplete = byId("btnGoComplete");
  const completeStatusEl = byId("completeStatus");
  const btnBackToVoice = byId("btnBackToVoice");
  const btnSaveSecurityQuestions = byId("btnSaveSecurityQuestions");

  const videoEl = byId("camVideo");
  const canvasEl = byId("camCanvas");

  const btnStartCam = byId("btnStartCam");
  const btnStopCam = byId("btnStopCam");
  const btnStartEnroll = byId("btnStartEnroll");

  const progressTextEl = byId("progressText");
  const progressBarEl = byId("progressBar");
  const statusTextEl = byId("statusText");

  const angleStatusEl = byId("angleStatus");
  const angleGuideEl = byId("angleGuide");

  const btnVoiceStart = byId("btnVoiceStart");
  const voiceChallengePromptEl = byId("voiceChallengePrompt");
  const voiceSampleProgressEl = byId("voiceSampleProgress");
  const voiceTranscriptPreviewEl = byId("voiceTranscriptPreview");
  const audioPreview = byId("audioPreview");
  const voiceStatusEl = byId("voiceStatus");

  const securityQuestion1El = byId("securityQuestion1");
  const securityQuestion2El = byId("securityQuestion2");
  const securityQuestion3El = byId("securityQuestion3");

  const securityAnswer1El = byId("securityAnswer1");
  const securityAnswer2El = byId("securityAnswer2");
  const securityAnswer3El = byId("securityAnswer3");

  const securityEnrollStatusEl = byId("securityEnrollStatus");

  //sound
  const angleCompleteSound = new Audio("/clients/shared/angle-complete.wav");
  angleCompleteSound.volume = 0.35;

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
  const FACE_TARGET_PER_ANGLE = 5;
  const FACE_ANGLE_ORDER = ["center", "left", "right"];
  const FACE_TOTAL_TARGET = FACE_TARGET_PER_ANGLE * FACE_ANGLE_ORDER.length;
  const FACE_CAPTURE_INTERVAL_MS = 450;

  const VOICE_TARGET_SAMPLES = 10;
  const VOICE_PROMPTS = [
    "Bugun hava cok guzel",
    "Sisteme guvenli sekilde giris yapiyorum",
    "Kayit islemi icin hazirim",
    "Mikrofona net ve duzgun konusuyorum",
    "Biyometrik verilerim korunacak",
    "Her ornekte ayni sekilde konusuyorum",
    "Kayit islemi basariyla tamamlanacak",
    "Bu sistem hizli ve kullanisli",
    "Gizliligime onem veriyorum",
    "Islem tamamlandiginda bilgilendirilecegim",
  ];

  let requiredAngle = FACE_ANGLE_ORDER[0];
  let faceCaptureRunning = false;
  let voiceListening = false;

  let faceSamplesByAngle = {
    center: [],
    left: [],
    right: [],
  };

  let angleCounts = {
    center: 0,
    left: 0,
    right: 0,
  };

  let voiceSamples = [];

  let faceEnrollmentCompleted = false;
  let voiceEnrollmentCompleted = false;
  let biometricSubmitCompleted = false;

  let faceDuplicateChecked = false;
  let faceDuplicateBlocked = false;
  let faceDuplicateMessage = "";

  let voiceDuplicateChecked = false;
  let voiceDuplicateBlocked = false;
  let voiceDuplicateMessage = "";

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

  function playAngleCompleteSound() {
    try {
      angleCompleteSound.currentTime = 0;
      angleCompleteSound.play().catch(() => {});
    } catch {}
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
    { lang = "tr-TR", timeoutMs = 10000 } = {},
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

  function getTotalAcceptedFaceSamples() {
    return angleCounts.center + angleCounts.left + angleCounts.right;
  }

  function getFlattenedFaceSamples() {
    return [
      ...faceSamplesByAngle.center,
      ...faceSamplesByAngle.left,
      ...faceSamplesByAngle.right,
    ];
  }

  function resetFaceEnrollmentState() {
    requiredAngle = FACE_ANGLE_ORDER[0];
    faceSamplesByAngle = {
      center: [],
      left: [],
      right: [],
    };
    angleCounts = {
      center: 0,
      left: 0,
      right: 0,
    };
    faceEnrollmentCompleted = false;

    faceDuplicateChecked = false;
    faceDuplicateBlocked = false;
    faceDuplicateMessage = "";
  }

  function resetVoiceEnrollmentState() {
    voiceSamples = [];
    voiceEnrollmentCompleted = false;
    voiceDuplicateChecked = false;
    voiceDuplicateBlocked = false;
    voiceDuplicateMessage = "";
  }

  function updateFaceProgress() {
    const current = getTotalAcceptedFaceSamples();
    setText(progressTextEl, `${current}/${FACE_TOTAL_TARGET}`);

    if (progressBarEl) {
      const pct = Math.min(
        100,
        Math.round((current / FACE_TOTAL_TARGET) * 100),
      );
      progressBarEl.style.width = `${pct}%`;
    }

    if (angleStatusEl) {
      setText(
        angleStatusEl,
        `Center: ${angleCounts.center}/${FACE_TARGET_PER_ANGLE} | Left: ${angleCounts.left}/${FACE_TARGET_PER_ANGLE} | Right: ${angleCounts.right}/${FACE_TARGET_PER_ANGLE}`,
      );
    }
  }

  function updateFaceGuidance() {
    const friendly = {
      center: "Look straight at the camera.",
      left: "Turn your head LEFT.",
      right: "Turn your head RIGHT.",
    };

    if (faceEnrollmentCompleted) {
      setText(angleGuideEl, "Face enrollment completed.");
      return;
    }

    setText(
      angleGuideEl,
      friendly[requiredAngle] ||
        "Align your face with the requested direction.",
    );
  }

  function updateVoiceSampleProgress() {
    setText(
      voiceSampleProgressEl,
      `Saved ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} samples`,
    );
  }

  function getCurrentVoicePrompt() {
    return VOICE_PROMPTS[voiceSamples.length] || "";
  }

  function updateVoicePrompt() {
    if (voiceEnrollmentCompleted) {
      setText(
        voiceChallengePromptEl,
        `${VOICE_TARGET_SAMPLES} samples captured. Voice enrollment completed.`,
      );
      return;
    }

    const prompt = getCurrentVoicePrompt();
    setText(
      voiceChallengePromptEl,
      prompt || "Please read the displayed sentence clearly.",
    );
  }

  function getNextRequiredAngle() {
    const currentIndex = FACE_ANGLE_ORDER.indexOf(requiredAngle);
    if (currentIndex < 0) return FACE_ANGLE_ORDER[0];
    return FACE_ANGLE_ORDER[currentIndex + 1] || null;
  }

  function advanceAngleIfNeeded() {
    if (angleCounts[requiredAngle] < FACE_TARGET_PER_ANGLE) return;

    const nextAngle = getNextRequiredAngle();
    if (nextAngle) {
      playAngleCompleteSound();
      requiredAngle = nextAngle;
      updateFaceGuidance();
      setStatus(
        `Angle completed. Now collect ${FACE_TARGET_PER_ANGLE} samples for ${requiredAngle.toUpperCase()}.`,
      );
      return;
    }

    playAngleCompleteSound();
    faceEnrollmentCompleted = true;
    faceCaptureRunning = false;
    updateFaceGuidance();
    setStatus("Face enrollment completed successfully.");
  }

  function parsePoseCheckResult(result, currentRequiredAngle) {
    const normalizedStatus = String(result?.status || "")
      .trim()
      .toUpperCase();
    const normalizedReason = String(result?.reason || "")
      .trim()
      .toUpperCase();

    const accepted =
      result?.accepted === true ||
      result?.ok === true ||
      result?.passed === true ||
      normalizedStatus === "OK" ||
      normalizedStatus === "PASS" ||
      normalizedStatus === "ACCEPTED" ||
      normalizedReason === "OK";

    return {
      accepted,
      reason:
        result?.reason ||
        result?.message ||
        (accepted
          ? "OK"
          : `REQUIRE_${String(currentRequiredAngle).toUpperCase()}`),
      detectedAngle:
        result?.detected_angle || result?.angle || result?.pose || null,
    };
  }

  async function validateFaceFrame(faceB64, currentRequiredAngle) {
    const response = await apiIdentifyPoseCheck(faceB64, currentRequiredAngle);
    return parsePoseCheckResult(response, currentRequiredAngle);
  }

  function showFaceStep() {
    faceStepEl?.classList.remove("hidden");
    voiceStepEl?.classList.add("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 1 of 3");
    setText(stepTitleEl, "Face Enrollment");
    setText(
      stepDescriptionEl,
      "Collect 5 center, 5 left and 5 right face samples. Wrong angles will be rejected.",
    );

    updateFaceGuidance();
    updateFaceProgress();
  }

  function showVoiceStep() {
    stopCamera([videoEl]);

    faceCaptureRunning = false;
    
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.remove("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 2 of 3");
    setText(stepTitleEl, "Voice Enrollment");
    setText(
      stepDescriptionEl,
      `Record ${VOICE_TARGET_SAMPLES} voice samples by reading the shown sentence.`,
    );

    updateVoicePrompt();
    updateVoiceSampleProgress();
  }

  function showSecurityStep() {
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.add("hidden");
    securityStepEl?.classList.remove("hidden");
    completeStepEl?.classList.add("hidden");

    setText(stepIndicatorEl, "Step 3 of 3");
    setText(stepTitleEl, "Security Questions");

    setText(
      stepDescriptionEl,
      "Select 3 different security questions and enter your answers.",
    );
    loadSecurityQuestions();
  }

  async function loadSecurityQuestions() {
    try {
      const questions = await apiGetSecurityQuestions();

      const selects = [
        securityQuestion1El,
        securityQuestion2El,
        securityQuestion3El,
      ];

      for (const select of selects) {
        if (!select) continue;

        select.innerHTML = `
        <option value="">Select a question</option>
      `;

        for (const q of questions) {
          const option = document.createElement("option");

          option.value = q.question_id;
          option.textContent = q.question_text;

          select.appendChild(option);
        }
      }

      setText(securityEnrollStatusEl, "Questions loaded.");
    } catch (e) {
      console.error(e);
      setText(
        securityEnrollStatusEl,
        `Question load failed: ${e.message || "UNKNOWN_ERROR"}`,
      );
    }
  }

  function showCompleteStep(
    message = "Biometric enrollment completed successfully.",
  ) {
    faceStepEl?.classList.add("hidden");
    voiceStepEl?.classList.add("hidden");
    securityStepEl?.classList.add("hidden");
    completeStepEl?.classList.remove("hidden");

    setText(stepIndicatorEl, "Completed");
    setText(stepTitleEl, "Enrollment Completed");
    setText(
      stepDescriptionEl,
      "Your face and voice enrollment steps have been completed successfully.",
    );
    setText(completeStatusEl, message);
  }

  function updateStepButtons() {
    if (btnGoVoice) {
      btnGoVoice.disabled =
        !faceEnrollmentCompleted || faceCaptureRunning || faceDuplicateBlocked;
    }

    if (btnGoComplete) {
      btnGoComplete.disabled =
        !faceEnrollmentCompleted ||
        !voiceEnrollmentCompleted ||
        biometricSubmitCompleted ||
        faceDuplicateBlocked ||
        voiceDuplicateBlocked;
    }

    if (btnVoiceStart) {
      btnVoiceStart.disabled =
        voiceListening ||
        voiceEnrollmentCompleted ||
        biometricSubmitCompleted ||
        voiceDuplicateBlocked;
    }

    if (btnStartEnroll) {
      btnStartEnroll.disabled =
        biometricSubmitCompleted ||
        faceCaptureRunning ||
        faceEnrollmentCompleted ||
        faceDuplicateBlocked;
    }

    if (btnStartCam) {
      btnStartCam.disabled = faceCaptureRunning;
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
      if (faceDuplicateBlocked) {
        setStatus(faceDuplicateMessage || "Bu yüz zaten sistemde kayıtlı.");
        return;
      }

      if (faceEnrollmentCompleted) {
        setStatus("Face enrollment is already completed.");
        return;
      }

      if (faceCaptureRunning) {
        setStatus("Face enrollment is already running.");
        return;
      }

      const hasCamera = !!videoEl?.srcObject;
      if (!hasCamera) {
        setStatus("Start camera first.");
        return;
      }

      resetFaceEnrollmentState();
      faceCaptureRunning = true;
      updateFaceProgress();
      updateFaceGuidance();
      updateStepButtons();

      setStatus(
        `Face enrollment started. Please look ${requiredAngle.toUpperCase()}.`,
      );

      while (faceCaptureRunning && !faceEnrollmentCompleted) {
        const currentRequiredAngle = requiredAngle;
        const faceB64 = captureFrameBase64(videoEl, canvasEl);

        if (!faceB64) {
          setStatus("Frame capture failed. Trying again...");
          await sleep(FACE_CAPTURE_INTERVAL_MS);
          continue;
        }

        let poseResult;
        try {
          poseResult = await validateFaceFrame(faceB64, currentRequiredAngle);
        } catch (e) {
          console.error(e);
          faceCaptureRunning = false;
          setStatus(`Pose check failed: ${e.message || "UNKNOWN_ERROR"}`);
          updateStepButtons();
          return;
        }

        if (!poseResult.accepted) {
          setStatus(
            `Rejected frame for ${currentRequiredAngle.toUpperCase()}: ${
              poseResult.reason || "WRONG_POSE"
            }`,
          );
          await sleep(FACE_CAPTURE_INTERVAL_MS);
          continue;
        }

        faceSamplesByAngle[currentRequiredAngle].push({
          image_b64: faceB64,
          angle: currentRequiredAngle,
        });
        angleCounts[currentRequiredAngle] += 1;

        if (!faceDuplicateChecked && getTotalAcceptedFaceSamples() === 1) {
          try {
            const precheck = await apiPrecheckFace(username, faceB64);

            if (precheck?.duplicate) {
              faceDuplicateBlocked = true;
              faceDuplicateMessage = precheck?.matched_username
                ? `Bu yüz zaten ${precheck.matched_username} kullanıcısına kayıtlı.`
                : "Bu yüz zaten sistemde kayıtlı.";
              faceCaptureRunning = false;
              faceEnrollmentCompleted = false;

              setStatus(faceDuplicateMessage);
              updateStepButtons();
              return;
            }

            faceDuplicateChecked = true;
          } catch (e) {
            console.error(e);
            faceCaptureRunning = false;
            setStatus(`Face precheck failed: ${e.message || "UNKNOWN_ERROR"}`);
            updateStepButtons();
            return;
          }
        }

        updateFaceProgress();

        setStatus(
          `Accepted ${currentRequiredAngle.toUpperCase()} sample ${angleCounts[currentRequiredAngle]}/${FACE_TARGET_PER_ANGLE}`,
        );

        advanceAngleIfNeeded();
        updateStepButtons();

        await sleep(FACE_CAPTURE_INTERVAL_MS);
      }

      if (faceEnrollmentCompleted) {
        updateStepButtons();
        setTimeout(() => {
          showVoiceStep();
        }, 250);
      }
    } catch (e) {
      console.error(e);
      faceCaptureRunning = false;
      setStatus(`Face collection error: ${e.message || "UNKNOWN_ERROR"}`);
      updateStepButtons();
    }
  });

  // ---------- Voice ----------
  btnVoiceStart?.addEventListener("click", async () => {
    const minRecordMs = 2200;

    try {
      if (voiceDuplicateBlocked) {
        setVoiceStatus(
          voiceDuplicateMessage || "Bu ses zaten sistemde kayıtlı.",
        );
        return;
      }

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

      if (!voiceDuplicateChecked && voiceSamples.length === 0) {
        try {
          const precheck = await apiPrecheckVoice(username, b64);

          if (precheck?.duplicate) {
            voiceDuplicateBlocked = true;
            voiceDuplicateMessage = precheck?.matched_username
              ? `Bu ses zaten ${precheck.matched_username} kullanıcısına kayıtlı.`
              : "Bu ses zaten sistemde kayıtlı.";

            setVoiceStatus(voiceDuplicateMessage);
            updateStepButtons();
            return;
          }

          voiceDuplicateChecked = true;
        } catch (e) {
          console.error(e);
          setVoiceStatus(
            `Voice precheck failed: ${e.message || "UNKNOWN_ERROR"}`,
          );
          updateStepButtons();
          return;
        }
      }

      if (audioPreview) {
        audioPreview.src = URL.createObjectURL(blob);
        audioPreview.classList.remove("hidden");
      }

      setText(voiceTranscriptPreviewEl, speech?.transcript || promptText);

      voiceSamples.push({
        voice_wav_b64: b64,
        prompt_text: promptText,
        transcript_text: speech?.transcript || "",
      });

      updateVoiceSampleProgress();

      if (voiceSamples.length >= VOICE_TARGET_SAMPLES) {
        voiceEnrollmentCompleted = true;
        updateVoicePrompt();
        setVoiceStatus(
          `Voice samples completed (${voiceSamples.length}/${VOICE_TARGET_SAMPLES}).`,
        );
      } else {
        updateVoicePrompt();
        setVoiceStatus(
          `Sample ${voiceSamples.length}/${VOICE_TARGET_SAMPLES} saved.`,
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
        setVoiceStatus(
          `Voice recording failed: ${e.message || "UNKNOWN_ERROR"}`,
        );
      }
    } finally {
      voiceListening = false;
      updateStepButtons();
    }
  });

  // ---------- Navigation ----------
  btnGoVoice?.addEventListener("click", () => {
    if (faceDuplicateBlocked) {
      setStatus(faceDuplicateMessage || "Bu yüz zaten sistemde kayıtlı.");
      return;
    }

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

  btnBackToVoice?.addEventListener("click", () => {
    showVoiceStep();
  });

  // ---------- Voice -> Security ----------
  btnGoComplete?.addEventListener("click", () => {
    if (faceDuplicateBlocked) {
      setStatus(faceDuplicateMessage || "Bu yüz zaten sistemde kayıtlı.");
      return;
    }

    if (voiceDuplicateBlocked) {
      setVoiceStatus(voiceDuplicateMessage || "Bu ses zaten sistemde kayıtlı.");
      return;
    }

    if (!faceEnrollmentCompleted) {
      setStatus("Complete face enrollment first.");
      return;
    }

    if (!voiceEnrollmentCompleted) {
      setVoiceStatus("Complete voice enrollment first.");
      return;
    }

    showSecurityStep();
  });

  // ---------- Security + Final submit ----------
  btnSaveSecurityQuestions?.addEventListener("click", async () => {
    try {
      const faceSamples = getFlattenedFaceSamples();

      const q1 = Number(securityQuestion1El?.value);
      const q2 = Number(securityQuestion2El?.value);
      const q3 = Number(securityQuestion3El?.value);

      const a1 = (securityAnswer1El?.value || "").trim();
      const a2 = (securityAnswer2El?.value || "").trim();
      const a3 = (securityAnswer3El?.value || "").trim();

      if (!q1 || !q2 || !q3) {
        setText(securityEnrollStatusEl, "Please select 3 security questions.");
        return;
      }

      if (new Set([q1, q2, q3]).size !== 3) {
        setText(
          securityEnrollStatusEl,
          "Security questions must be different.",
        );
        return;
      }

      if (!a1 || !a2 || !a3) {
        setText(securityEnrollStatusEl, "All security answers are required.");
        return;
      }

      if (faceDuplicateBlocked) {
        setStatus(faceDuplicateMessage || "Bu yüz zaten sistemde kayıtlı.");
        return;
      }

      if (voiceDuplicateBlocked) {
        setVoiceStatus(
          voiceDuplicateMessage || "Bu ses zaten sistemde kayıtlı.",
        );
        return;
      }

      if (!faceEnrollmentCompleted) {
        setStatus("Complete face enrollment first.");
        return;
      }

      if (!voiceEnrollmentCompleted) {
        setVoiceStatus("Complete voice enrollment first.");
        return;
      }

      if (!faceSamples.length || faceSamples.length < FACE_TOTAL_TARGET) {
        setStatus("Face samples are missing.");
        return;
      }

      if (!voiceSamples.length || voiceSamples.length < VOICE_TARGET_SAMPLES) {
        setVoiceStatus("Voice samples are missing.");
        return;
      }

      biometricSubmitCompleted = false;
      updateStepButtons();

      setText(securityEnrollStatusEl, "Saving enrollment...");
      setStatus("Sending biometric enrollment...");
      setVoiceStatus("Submitting biometric data...");

      const response = await apiEnrollBiometric(
        username,
        role,
        faceSamples,
        voiceSamples,
      );

      if (!response?.success) {
        biometricSubmitCompleted = false;
        updateStepButtons();

        const rawMessage = String(response?.message || "ENROLLMENT_FAILED");

        setStatus(`Enrollment failed: ${rawMessage}`);
        setVoiceStatus(`Enrollment failed: ${rawMessage}`);
        setText(securityEnrollStatusEl, "Biometric enrollment failed.");
        return;
      }

      const userId = response.user_id;

      if (!userId) {
        setText(
          securityEnrollStatusEl,
          "User id not returned from enrollment.",
        );
        return;
      }

      await apiSaveSecurityAnswers({
        user_id: userId,
        answers: [
          { question_id: q1, answer: a1 },
          { question_id: q2, answer: a2 },
          { question_id: q3, answer: a3 },
        ],
      });

      biometricSubmitCompleted = true;
      updateStepButtons();

      const successMessage =
        response?.message || "Biometric enrollment completed successfully.";

      setStatus(successMessage);
      setVoiceStatus("Enrollment completed.");
      setText(securityEnrollStatusEl, "Security questions saved.");

      showCompleteStep(successMessage);
    } catch (e) {
      console.error(e);

      biometricSubmitCompleted = false;
      updateStepButtons();

      const msg = e?.message || "UNKNOWN_ERROR";

      setStatus(`Enrollment failed: ${msg}`);
      setVoiceStatus(`Enrollment failed: ${msg}`);
      setText(securityEnrollStatusEl, `Security save failed: ${msg}`);
    }
  });

  // ---------- Init ----------
  resetFaceEnrollmentState();
  resetVoiceEnrollmentState();

  updateFaceProgress();
  updateFaceGuidance();
  updateVoiceSampleProgress();
  updateVoicePrompt();

  setText(voiceTranscriptPreviewEl, "Waiting for phrase...");
  setStatus("Ready.");
  setVoiceStatus("Ready.");

  faceEnrollmentCompleted = false;
  voiceEnrollmentCompleted = false;
  biometricSubmitCompleted = false;
  faceCaptureRunning = false;
  voiceListening = false;

  updateStepButtons();
  showFaceStep();
}
