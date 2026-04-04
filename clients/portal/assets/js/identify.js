import { byId, setText } from "./dom.js";
import {
  startCamera,
  stopCamera,
  captureFrameBase64,
} from "./camera.js?v=20260314-camera-mirror";
import {
  apiIdentifyFace,
  apiAuthVerify,
  apiIdentifyVoiceChallenge,
  apiValidateIdentifyVoiceChallenge,
  apiIdentifyPoseCheck,
  apiIdentifyBlinkCheck,
} from "./api.js";
import {
  recognizeSpeechOnce,
  startVoiceRecording,
  stopVoiceRecordingToBase64,
} from "./voice.js";

/**
 * Identify page flow:
 * Face capture -> /identify (1:N) -> user found
 * Voice/liveness sequence -> /auth/verify (face + voice)
 */
export function initIdentify() {
  const MAX_VOICE_VERIFY_ATTEMPTS = 3;

  // --- step helper ---
  const stepIds = ["step-face", "step-liveness", "step-result"];
  function showStep(idToShow) {
    stepIds.forEach((id) => {
      const el = byId(id);
      if (!el) return;
      el.classList.toggle("hidden", id !== idToShow);
    });
  }

  // --- elements ---
  const videoEl = byId("video");
  const livenessVideoEl = byId("livenessVideo");
  const canvasEl = byId("canvas");

  const faceStatusEl = byId("faceStatus");
  const statusTextEl = byId("statusText");

  const btnCamStart = byId("btnCamStart");
  const btnFaceCapture = byId("btnFaceCapture");
  const btnBack = byId("btnBack");

  const identifyChallengePromptEl = byId("identifyChallengePrompt");
  const identifyChallengeAnswerEl = byId("identifyChallengeAnswer");
  const livenessStatusEl = byId("livenessStatus");
  const btnCaptureChallengeAnswer = byId("btnCaptureChallengeAnswer");
  const btnRefreshIdentifyChallenge = byId("btnRefreshIdentifyChallenge");
  const btnCheckTurnRight = byId("btnCheckTurnRight");
  const btnCheckTurnLeft = byId("btnCheckTurnLeft");
  const btnCheckBlink = byId("btnCheckBlink");
  const btnLivenessContinue = byId("btnLivenessContinue");

  const btnRestartResult = byId("btnRestartResult");

  const decisionEl = byId("result-decision");
  const faceScoreEl = byId("face-score");
  const voiceScoreEl = byId("voice-score");
  const fusionScoreEl = byId("fusion-score");
  const spoofScoreEl = byId("spoof-score");
  const spoofDecisionEl = byId("spoof-decision");

  const identifiedUserBanner = byId("identifiedUserBanner");
  const identifiedUserName = byId("identifiedUserName");
  const flowDebugStepEl = byId("flowDebugStep");
  const flowDebugStatusEl = byId("flowDebugStatus");
  const flowDebugReasonEl = byId("flowDebugReason");
  const flowDebugScoreEl = byId("flowDebugScore");
  const flowDebugHistoryEl = byId("flowDebugHistory");

  // --- state ---
  let faceB64 = null;
  let faceScore = 0;
  let identifiedUser = null;
  let identifiedUserId = null;
  let isFaceStepPassed = false;
  let isVoiceAnswerPassed = false;
  let isVoiceRetryMode = false;
  let voiceVerifyAttempts = 0;
  let identifyChallengeId = null;
  let identifyChallengePrompt = "";
  let identifyChallengeExpectedKeywords = [];
  let identifyChallengeExpectedNumbers = [];
  let challengeVoiceB64 = null;
  let livenessOrder = [];
  let livenessStepIndex = 0;
  let flowDebugHistory = [];

  function getCaptureVideoEl() {
    const livenessStepEl = byId("step-liveness");
    if (
      livenessStepEl &&
      !livenessStepEl.classList.contains("hidden") &&
      livenessVideoEl
    ) {
      return livenessVideoEl;
    }
    return videoEl;
  }

  // --- status helpers ---
  function setFaceStatus(msg) {
    if (faceStatusEl) setText(faceStatusEl, msg);
    console.log("[FACE]", msg);
  }

  function setStatus(msg) {
    if (statusTextEl) setText(statusTextEl, msg);
    console.log("[STATUS]", msg);
  }

  function setLivenessStatus(msg) {
    if (livenessStatusEl) setText(livenessStatusEl, msg);
    console.log("[LIVENESS]", msg);
  }

  function flowStepName(task) {
    if (task === "answer") return "challenge_answer";
    if (task === "turn_right") return "turn_right";
    if (task === "turn_left") return "turn_left";
    if (task === "blink") return "blink";
    return "done";
  }

  function setFlowDebug(step, status, reason = "-", score = "-") {
    if (typeof step === "object" && step !== null) {
      const debug = step;
      const similarityScore =
        debug.similarity !== undefined ? debug.similarity : debug.score;

      if (flowDebugStepEl) setText(flowDebugStepEl, debug.debug_step || "-");
      if (flowDebugStatusEl) setText(flowDebugStatusEl, debug.status || "-");
      if (flowDebugReasonEl) setText(flowDebugReasonEl, debug.reason || "-");

      if (flowDebugScoreEl) {
        if (similarityScore !== undefined && similarityScore !== null) {
          flowDebugScoreEl.textContent = similarityScore;
        } else {
          flowDebugScoreEl.textContent = "0.0";
        }
      }

      if (byId("debugYaw"))
        setText(byId("debugYaw"), debug.yaw !== undefined ? debug.yaw : "-");
      if (byId("debugBlur"))
        setText(
          byId("debugBlur"),
          debug.blur_score !== undefined ? debug.blur_score : "-",
        );
      if (byId("debugBBox"))
        setText(
          byId("debugBBox"),
          debug.bbox_size !== undefined ? debug.bbox_size : "-",
        );
      if (byId("debugNoseX"))
        setText(
          byId("debugNoseX"),
          debug.nose_x_ratio !== undefined ? debug.nose_x_ratio : "-",
        );

      flowDebugHistory.unshift(
        `${debug.debug_step || "-"} | ${debug.status || "-"} | ${debug.reason || "-"} | ${
          similarityScore !== undefined ? similarityScore : "0.0"
        }`,
      );
      flowDebugHistory = flowDebugHistory.slice(0, 8);

      if (flowDebugHistoryEl) {
        flowDebugHistoryEl.innerHTML = flowDebugHistory.join("<br>");
      }

      console.log(
        `[FLOW] step=${debug.debug_step || "-"} status=${debug.status || "-"} reason=${
          debug.reason || "-"
        } score=${similarityScore !== undefined ? similarityScore : "0.0"}`,
      );
      return;
    }

    if (flowDebugStepEl) setText(flowDebugStepEl, step || "-");
    if (flowDebugStatusEl) setText(flowDebugStatusEl, status || "-");
    if (flowDebugReasonEl) setText(flowDebugReasonEl, reason || "-");
    if (flowDebugScoreEl) setText(flowDebugScoreEl, score || "-");

    flowDebugHistory.unshift(
      `${step || "-"} | ${status || "-"} | ${reason || "-"} | ${score || "-"}`,
    );
    flowDebugHistory = flowDebugHistory.slice(0, 8);

    if (flowDebugHistoryEl) {
      flowDebugHistoryEl.innerHTML = flowDebugHistory.join("<br>");
    }

    console.log(
      `[FLOW] step=${step || "-"} status=${status || "-"} reason=${reason || "-"} score=${score || "-"}`,
    );
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function taskLabel(task) {
    if (task === "answer") return "Ekrandaki cümleyi oku";
    if (task === "turn_right") return "Basini SAGA cevir ve kontrol et";
    if (task === "turn_left") return "Basini SOLA cevir ve kontrol et";
    if (task === "blink") return "Goz kirp ve kontrol et";
    return "-";
  }

  function currentTask() {
    return livenessOrder[livenessStepIndex] || null;
  }

  function shuffledTasks(tasks) {
    const arr = [...tasks];
    for (let i = arr.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function initSequentialLivenessOrder() {
    livenessOrder = shuffledTasks([
      "answer",
      "turn_right",
      "turn_left",
      "blink",
    ]);
    livenessStepIndex = 0;
    isVoiceAnswerPassed = false;
    isVoiceRetryMode = false;
    setFlowDebug("liveness_order", "info", livenessOrder.join(" -> "));
    updateLivenessUI();
  }

  function initVoiceRetryOrder() {
    livenessOrder = ["answer"];
    livenessStepIndex = 0;
    isVoiceAnswerPassed = false;
    isVoiceRetryMode = true;
    updateLivenessUI();
  }

  function stepDone(task) {
    if (currentTask() !== task) {
      setLivenessStatus(
        `Sira hatasi. Simdi yapman gereken: ${taskLabel(currentTask())}`,
      );
      setFlowDebug(
        flowStepName(currentTask()),
        "failed",
        "STEP_ORDER_MISMATCH",
      );
      return false;
    }

    setFlowDebug(flowStepName(task), "passed", "OK");

    if (task === "answer") {
      isVoiceAnswerPassed = true;
    }

    livenessStepIndex += 1;
    updateLivenessUI();
    return true;
  }

  function updateLivenessUI() {
    if (!isFaceStepPassed) {
      if (btnCaptureChallengeAnswer) btnCaptureChallengeAnswer.disabled = true;
      if (btnCheckTurnRight) btnCheckTurnRight.disabled = true;
      if (btnCheckTurnLeft) btnCheckTurnLeft.disabled = true;
      if (btnCheckBlink) btnCheckBlink.disabled = true;
      if (btnLivenessContinue) btnLivenessContinue.disabled = true;
      if (btnRefreshIdentifyChallenge)
        btnRefreshIdentifyChallenge.disabled = true;
      if (identifyChallengeAnswerEl) identifyChallengeAnswerEl.disabled = true;
      return;
    }

    const task = currentTask();
    const finished = !task;

    if (btnCaptureChallengeAnswer)
      btnCaptureChallengeAnswer.disabled = task !== "answer";
    if (btnCheckTurnRight) btnCheckTurnRight.disabled = task !== "turn_right";
    if (btnCheckTurnLeft) btnCheckTurnLeft.disabled = task !== "turn_left";
    if (btnCheckBlink) btnCheckBlink.disabled = task !== "blink";
    if (btnLivenessContinue) btnLivenessContinue.disabled = !finished;
    if (btnRefreshIdentifyChallenge)
      btnRefreshIdentifyChallenge.disabled = task !== "answer";
    if (identifyChallengeAnswerEl)
      identifyChallengeAnswerEl.disabled = task !== "answer";

    if (btnCaptureChallengeAnswer)
      btnCaptureChallengeAnswer.style.display = task === "answer" ? "" : "none";
    if (btnRefreshIdentifyChallenge)
      btnRefreshIdentifyChallenge.style.display =
        task === "answer" ? "" : "none";
    if (identifyChallengeAnswerEl)
      identifyChallengeAnswerEl.style.display = task === "answer" ? "" : "none";
    if (identifyChallengePromptEl)
      identifyChallengePromptEl.style.display = task === "answer" ? "" : "none";
    if (btnCheckTurnRight)
      btnCheckTurnRight.style.display = task === "turn_right" ? "" : "none";
    if (btnCheckTurnLeft)
      btnCheckTurnLeft.style.display = task === "turn_left" ? "" : "none";
    if (btnCheckBlink)
      btnCheckBlink.style.display = task === "blink" ? "" : "none";
    if (btnLivenessContinue)
      btnLivenessContinue.style.display = finished ? "" : "none";

    if (finished) {
      if (isVoiceRetryMode) {
        setLivenessStatus(
          "Voice challenge tamamlandi. Tekrar dogrulama icin Complete Verification'a basin.",
        );
        setFlowDebug("done", "waiting", "READY_FOR_RETRY_VERIFY");
      } else {
        setLivenessStatus(
          "Tum sira kontrolleri tamamlandi. Continue to Voice.",
        );
        setFlowDebug("done", "waiting", "READY_FOR_VERIFY");
      }
      return;
    }

    setFlowDebug(flowStepName(task), "waiting", "USER_ACTION_REQUIRED");
    setLivenessStatus(
      `Adim ${livenessStepIndex + 1}/${livenessOrder.length}: ${taskLabel(task)}`,
    );
  }

  async function captureBurstFrames({ count = 10, intervalMs = 90 } = {}) {
    const frames = [];
    for (let i = 0; i < count; i += 1) {
      const frame = captureFrameBase64(getCaptureVideoEl(), canvasEl);
      if (frame) frames.push(frame);
      await sleep(intervalMs);
    }
    return frames;
  }

  function isVoiceRelatedFailure(reason) {
    const r = String(reason || "").toUpperCase();
    return r.startsWith("VOICE_");
  }

  async function handleVoiceVerifyFailure(reason, res) {
    voiceVerifyAttempts += 1;
    const remaining = MAX_VOICE_VERIFY_ATTEMPTS - voiceVerifyAttempts;

    const voiceScore = (res?.voice_score ?? 0).toFixed(3);
    const faceScoreVal = (res?.face_score ?? 0).toFixed(3);
    const fusionScoreVal = (res?.fusion_score ?? 0).toFixed(3);

    setFlowDebug(
      "done",
      "failed",
      `${reason}_ATTEMPT_${voiceVerifyAttempts}`,
      voiceScore,
    );

    const scoreBox = document.getElementById("voiceVerifyScoreBox");
    const vvFace = document.getElementById("vvFaceScore");
    const vvVoice = document.getElementById("vvVoiceScore");
    const vvFusion = document.getElementById("vvFusionScore");
    const vvReason = document.getElementById("vvReason");

    if (scoreBox) scoreBox.style.display = "";
    if (vvFace) setText(vvFace, faceScoreVal);
    if (vvVoice) setText(vvVoice, voiceScore);
    if (vvFusion) setText(vvFusion, fusionScoreVal);
    if (vvReason) setText(vvReason, reason);

    if (remaining <= 0) {
      setLivenessStatus(
        "Voice verification 3 kez basarisiz oldu. Islem basa donuyor.",
      );
      setStatus("VOICE_RETRY_LIMIT_EXCEEDED");
      restart();
      return;
    }

    challengeVoiceB64 = null;
    isVoiceAnswerPassed = false;

    setLivenessStatus(
      `Ses eslesmesi basarisiz. Skor: ${voiceScore}. Kalan hak: ${remaining}. Voice challenge adimini tekrar yapin.`,
    );

    await loadIdentifyChallenge({ voiceRetryOnly: true });
  }

  async function loadIdentifyChallenge({ voiceRetryOnly = false } = {}) {
    try {
      const ch = await apiIdentifyVoiceChallenge();

      identifyChallengeId = ch?.challenge_id || null;
      identifyChallengePrompt =
        ch?.prompt || "Lutfen ekrandaki cumleyi okuyun.";
      identifyChallengeExpectedKeywords = Array.isArray(ch?.expected_keywords)
        ? ch.expected_keywords
        : [];
      identifyChallengeExpectedNumbers = Array.isArray(ch?.expected_numbers)
        ? ch.expected_numbers
        : [];

      setText(identifyChallengePromptEl, identifyChallengePrompt);

      if (identifyChallengeAnswerEl) {
        identifyChallengeAnswerEl.value = "";
      }

      challengeVoiceB64 = null;
      isVoiceAnswerPassed = false;

      if (voiceRetryOnly) {
        initVoiceRetryOrder();
      } else {
        initSequentialLivenessOrder();
      }
    } catch (e) {
      console.error(e);
      identifyChallengeId = null;
      identifyChallengePrompt = "";
      identifyChallengeExpectedKeywords = [];
      identifyChallengeExpectedNumbers = [];
      setText(identifyChallengePromptEl, "Challenge unavailable.");
      setLivenessStatus("Challenge load failed.");
    }
  }

  // --- initial UI ---
  showStep("step-face");
  if (btnLivenessContinue) btnLivenessContinue.style.display = "none";
  setFlowDebug("face_front", "waiting", "START_CAMERA_AND_CAPTURE");

  // -----------------------
  // 1) Camera
  // -----------------------
  btnCamStart?.addEventListener("click", async () => {
    try {
      setFaceStatus("Requesting camera...");
      await startCamera(videoEl);
      setFaceStatus("Camera ready.");
    } catch (e) {
      console.error(e);
      setFaceStatus(`Camera error: ${e.message || "UNKNOWN_ERROR"}`);
    }
  });

  // -----------------------
  // 2) Capture Face + Identify
  // -----------------------
  btnFaceCapture?.addEventListener("click", async () => {
    try {
      faceB64 = captureFrameBase64(videoEl, canvasEl);
      isFaceStepPassed = false;

      if (!faceB64) {
        setFaceStatus("Face frame not captured. Start camera first.");
        setFlowDebug("face_front", "failed", "NO_FACE_FRAME");
        return;
      }

      setFaceStatus("Identifying face...");
      const idRes = await apiIdentifyFace(faceB64);

      if (!idRes?.identified) {
        identifiedUser = null;
        setFlowDebug(idRes);

        const reason = (idRes?.reason || "").toUpperCase();

        if (reason === "EYES_CLOSED") {
          setFaceStatus(
            "Eyes look closed. Please keep your eyes open and try again.",
          );
          return;
        }
        if (reason === "NO_FACE_DETECTED") {
          setFaceStatus(
            "Face not detected clearly. Please center your full face in frame.",
          );
          return;
        }
        if (reason === "MULTIPLE_FACES_DETECTED") {
          setFaceStatus(
            "Multiple faces detected. Keep only one face in frame.",
          );
          return;
        }
        if (reason === "FACE_NOT_FRONTAL") {
          setFaceStatus(
            "Please look straight at the camera (frontal face required).",
          );
          return;
        }
        if (reason === "EYES_NOT_CLEAR") {
          setFaceStatus(
            "Eye state is not clear. Keep your full face visible and eyes open.",
          );
          return;
        }
        if (reason === "NO_MATCH") {
          setFaceStatus(
            "Face not matched. Look straight at camera and try again.",
          );
          return;
        }

        setFaceStatus(
          "Identification failed. Please align your face and try again.",
        );
        return;
      }

      identifiedUser = idRes.username || `user_id=${idRes.user_id}`;
      identifiedUserId = Number(idRes.user_id ?? 0) || null;
      faceScore = Number(idRes.similarity ?? 0);

      setFaceStatus(
        `Identified: ${identifiedUser} (score ${faceScore.toFixed(3)})`,
      );
      setFlowDebug("face_front", "passed", "IDENTIFIED", faceScore.toFixed(3));

      isFaceStepPassed = true;
      voiceVerifyAttempts = 0;

      showStep("step-liveness");
      await startCamera(livenessVideoEl);
      await loadIdentifyChallenge();

      if (identifiedUserName) setText(identifiedUserName, identifiedUser);
      if (identifiedUserBanner) identifiedUserBanner.style.display = "block";
    } catch (e) {
      console.error(e);
      setFaceStatus(`Identify failed: ${e.message || "UNKNOWN_ERROR"}`);
      setFlowDebug("face_front", "failed", "REQUEST_ERROR");
    }
  });

  // -----------------------
  // 3) Liveness actions
  // -----------------------
  btnCaptureChallengeAnswer?.addEventListener("click", async () => {
    try {
      if (!isFaceStepPassed) {
        setLivenessStatus(
          "Once frontal face capture adimini basariyla tamamlayin.",
        );
        setFlowDebug("face_front", "failed", "FACE_STEP_REQUIRED");
        return;
      }

      if (currentTask() !== "answer") {
        setLivenessStatus(
          `Sira hatasi. Simdi yapman gereken: ${taskLabel(currentTask())}`,
        );
        setFlowDebug(
          flowStepName(currentTask()),
          "failed",
          "STEP_ORDER_MISMATCH",
        );
        return;
      }

      if (!identifyChallengeId) {
        setLivenessStatus("Challenge not ready.");
        setFlowDebug("voice_answer", "failed", "CHALLENGE_NOT_READY");
        return;
      }

      if (btnCaptureChallengeAnswer) btnCaptureChallengeAnswer.disabled = true;

      let answerText = (identifyChallengeAnswerEl?.value || "").trim();
      const startedAt = Date.now();
      const minRecordMs = 1800;

      setLivenessStatus(
        "Challenge cumlesi dinleniyor ve ses kimligi icin kaydediliyor...",
      );
      await startVoiceRecording();

      if (!answerText) {
        answerText = await recognizeSpeechOnce({
          lang: "tr-TR",
          timeoutMs: 10000,
        });
        if (identifyChallengeAnswerEl)
          identifyChallengeAnswerEl.value = answerText;
      }

      const elapsed = Date.now() - startedAt;
      if (elapsed < minRecordMs) {
        await sleep(minRecordMs - elapsed);
      }

      const { b64 } = await stopVoiceRecordingToBase64();
      challengeVoiceB64 = b64;

      const v = await apiValidateIdentifyVoiceChallenge({
        challenge_id: identifyChallengeId,
        answer_text: answerText,
        expected_keywords: identifyChallengeExpectedKeywords,
        expected_numbers: identifyChallengeExpectedNumbers,
      });

      if (!v?.passed) {
        isVoiceAnswerPassed = false;
        challengeVoiceB64 = null;

        const reason = String(
          v?.reason || "CHALLENGE_ANSWER_INVALID",
        ).toUpperCase();

        if (reason === "TOO_SHORT") {
          setLivenessStatus(
            "Cumle cok kisa algilandi. Ekrandaki cumleyi tam ve net sekilde tekrar okuyun.",
          );
        } else {
          setLivenessStatus(
            "Challenge cevabi gecersiz. Ekrandaki cumleyi tekrar okuyun.",
          );
        }

        setFlowDebug(
          "voice_answer",
          "failed",
          reason,
          `${v?.total_hits ?? 0}/${v?.total_expected ?? 0}`,
        );
        return;
      }

      setLivenessStatus(
        `Challenge cevabi kabul edildi. Ses kimligi on-izlemesi hesaplaniyor...`,
      );
      stepDone("answer");

      try {
        const previewRes = await apiAuthVerify({
          face_image_b64: faceB64,
          voice_wav_b64: challengeVoiceB64,
        });

        const previewScore = (previewRes?.voice_score ?? 0).toFixed(3);
        const previewFace = (previewRes?.face_score ?? 0).toFixed(3);

        setFlowDebug(
          "voice_preview",
          previewRes?.decision === "ACCEPTED" ||
            previewRes?.decision === "GRANTED"
            ? "passed"
            : "info",
          `SES_BENZERLIGI: ${previewScore} | YUZ: ${previewFace}`,
          previewScore,
        );

        setLivenessStatus(
          `Challenge kabul edildi. Ses benzerlik on-izlemesi: ${previewScore}. Sonraki adima gec.`,
        );
      } catch (_previewErr) {
        setLivenessStatus("Challenge cevabi kabul edildi. Sonraki adima gec.");
      }
    } catch (e) {
      console.error(e);
      try {
        await stopVoiceRecordingToBase64();
      } catch {}

      isVoiceAnswerPassed = false;
      challengeVoiceB64 = null;
      setLivenessStatus(
        `Speech capture failed: ${e.message || "UNKNOWN_ERROR"}`,
      );
      setFlowDebug("voice_answer", "failed", "SPEECH_CAPTURE_FAILED");
    } finally {
      updateLivenessUI();
    }
  });

  btnRefreshIdentifyChallenge?.addEventListener("click", async () => {
    if (currentTask() !== "answer") {
      setLivenessStatus(
        "Yeni challenge sadece voice challenge adiminda alinabilir.",
      );
      setFlowDebug(
        flowStepName(currentTask()),
        "failed",
        "INVALID_REFRESH_STEP",
      );
      return;
    }

    await loadIdentifyChallenge({ voiceRetryOnly: livenessOrder.length === 1 });
  });

  identifyChallengeAnswerEl?.addEventListener("input", () => {
    updateLivenessUI();
  });

  btnCheckTurnRight?.addEventListener("click", async () => {
    try {
      if (!isFaceStepPassed) {
        setLivenessStatus("Bu adim icin once face adimi tamamlanmali.");
        setFlowDebug("turn_right", "failed", "FACE_STEP_REQUIRED");
        return;
      }

      if (currentTask() !== "turn_right") {
        setLivenessStatus(
          `Sira hatasi. Simdi yapman gereken: ${taskLabel(currentTask())}`,
        );
        setFlowDebug(
          flowStepName(currentTask()),
          "failed",
          "STEP_ORDER_MISMATCH",
        );
        return;
      }

      const frame = captureFrameBase64(getCaptureVideoEl(), canvasEl);
      if (!frame) {
        setLivenessStatus("Start camera first.");
        setFlowDebug("turn_right", "failed", "NO_FACE_FRAME");
        return;
      }

      const res = await apiIdentifyPoseCheck(
        frame,
        "right",
        faceB64,
        identifiedUserId,
      );
      if (!res?.passed) {
        const reason =
          res?.reason ||
          ((res?.detected_turn || "none") === "none"
            ? "POSE_NOT_RIGHT"
            : `DETECTED_${String(res?.detected_turn || "none").toUpperCase()}`);

        if (String(reason).toUpperCase() === "POSE_NOT_ENOUGH_TURN") {
          setLivenessStatus(
            "RIGHT turn yetersiz. Basini biraz daha saga cevirip tekrar dene.",
          );
        } else {
          setLivenessStatus(
            `RIGHT turn failed (${reason}, detected: ${res?.detected_turn || "none"}).`,
          );
        }

        setFlowDebug(
          "turn_right",
          "failed",
          reason,
          res?.similarity != null ? Number(res.similarity).toFixed(3) : "-",
        );
        return;
      }

      setLivenessStatus("RIGHT turn check passed.");
      setFlowDebug(
        "turn_right",
        "passed",
        "OK",
        res?.similarity != null ? Number(res.similarity).toFixed(3) : "-",
      );
      stepDone("turn_right");
    } catch (e) {
      console.error(e);
      setLivenessStatus(
        `RIGHT turn check failed: ${e.message || "UNKNOWN_ERROR"}`,
      );
      setFlowDebug("turn_right", "failed", "POSE_CHECK_ERROR");
    }
  });

  btnCheckTurnLeft?.addEventListener("click", async () => {
    try {
      if (!isFaceStepPassed) {
        setLivenessStatus("Bu adim icin once face adimi tamamlanmali.");
        setFlowDebug("turn_left", "failed", "FACE_STEP_REQUIRED");
        return;
      }

      if (currentTask() !== "turn_left") {
        setLivenessStatus(
          `Sira hatasi. Simdi yapman gereken: ${taskLabel(currentTask())}`,
        );
        setFlowDebug(
          flowStepName(currentTask()),
          "failed",
          "STEP_ORDER_MISMATCH",
        );
        return;
      }

      const frame = captureFrameBase64(getCaptureVideoEl(), canvasEl);
      if (!frame) {
        setLivenessStatus("Start camera first.");
        setFlowDebug("turn_left", "failed", "NO_FACE_FRAME");
        return;
      }

      const res = await apiIdentifyPoseCheck(
        frame,
        "left",
        faceB64,
        identifiedUserId,
      );
      if (!res?.passed) {
        const reason =
          res?.reason ||
          ((res?.detected_turn || "none") === "none"
            ? "POSE_NOT_LEFT"
            : `DETECTED_${String(res?.detected_turn || "none").toUpperCase()}`);

        if (String(reason).toUpperCase() === "POSE_NOT_ENOUGH_TURN") {
          setLivenessStatus(
            "LEFT turn yetersiz. Basini biraz daha sola cevirip tekrar dene.",
          );
        } else {
          setLivenessStatus(
            `LEFT turn failed (${reason}, detected: ${res?.detected_turn || "none"}).`,
          );
        }

        setFlowDebug(
          "turn_left",
          "failed",
          reason,
          res?.similarity != null ? Number(res.similarity).toFixed(3) : "-",
        );
        return;
      }

      setLivenessStatus("LEFT turn check passed.");
      setFlowDebug(
        "turn_left",
        "passed",
        "OK",
        res?.similarity != null ? Number(res.similarity).toFixed(3) : "-",
      );
      stepDone("turn_left");
    } catch (e) {
      console.error(e);
      setLivenessStatus(
        `LEFT turn check failed: ${e.message || "UNKNOWN_ERROR"}`,
      );
      setFlowDebug("turn_left", "failed", "POSE_CHECK_ERROR");
    }
  });

  btnCheckBlink?.addEventListener("click", async () => {
    try {
      if (!isFaceStepPassed) {
        setLivenessStatus("Bu adim icin once face adimi tamamlanmali.");
        setFlowDebug("blink", "failed", "FACE_STEP_REQUIRED");
        return;
      }

      if (currentTask() !== "blink") {
        setLivenessStatus(
          `Sira hatasi. Simdi yapman gereken: ${taskLabel(currentTask())}`,
        );
        setFlowDebug(
          flowStepName(currentTask()),
          "failed",
          "STEP_ORDER_MISMATCH",
        );
        return;
      }

      setLivenessStatus(
        "Blink kontrolu icin kisa video aliniyor... Lutfen bir kez goz kirpin.",
      );
      const frames = await captureBurstFrames({ count: 20, intervalMs: 70 });

      if (frames.length < 6) {
        setLivenessStatus("Blink kontrolu icin yeterli frame alinamadi.");
        setFlowDebug("blink", "failed", "INSUFFICIENT_FRAMES");
        return;
      }

      const res = await apiIdentifyBlinkCheck(
        frames,
        faceB64,
        identifiedUserId,
      );
      if (!res?.passed) {
        const reason = String(
          res?.reason || "BLINK_NOT_DETECTED",
        ).toUpperCase();

        if (reason === "BLINK_NOT_DETECTED") {
          setLivenessStatus(
            "Blink algilanamadi. Gozlerinizi bir kez belirgin sekilde kirpip tekrar deneyin.",
          );
        } else {
          setLivenessStatus(`Blink check failed (${reason}).`);
        }

        setFlowDebug(
          "blink",
          "failed",
          reason,
          res?.drop_ratio != null ? Number(res.drop_ratio).toFixed(3) : "-",
        );
        return;
      }

      setLivenessStatus("BLINK check passed.");
      setFlowDebug(
        "blink",
        "passed",
        "OK",
        res?.drop_ratio != null ? Number(res.drop_ratio).toFixed(3) : "-",
      );
      stepDone("blink");
    } catch (e) {
      console.error(e);
      setLivenessStatus(`BLINK check failed: ${e.message || "UNKNOWN_ERROR"}`);
      setFlowDebug("blink", "failed", "BLINK_CHECK_ERROR");
    }
  });

  btnLivenessContinue?.addEventListener("click", async () => {
    try {
      if (!isFaceStepPassed) {
        setLivenessStatus(
          "Frontal face capture basarisiz. Once ilk adimi tamamlayin.",
        );
        setFlowDebug("done", "failed", "FACE_STEP_REQUIRED");
        return;
      }

      if (!isVoiceAnswerPassed) {
        setLivenessStatus(
          "Voice challenge adimi basarisiz. Once challenge cevabini tekrar tamamlayin.",
        );
        setFlowDebug("done", "failed", "VOICE_STEP_REQUIRED");
        return;
      }

      if (!identifyChallengeId) {
        setLivenessStatus("Challenge not ready.");
        setFlowDebug("done", "failed", "CHALLENGE_NOT_READY");
        return;
      }

      if (currentTask()) {
        setLivenessStatus(`Once su adimi tamamla: ${taskLabel(currentTask())}`);
        setFlowDebug(
          flowStepName(currentTask()),
          "failed",
          "STEP_NOT_COMPLETED",
        );
        return;
      }

      if (!challengeVoiceB64) {
        setLivenessStatus(
          "Challenge sesi kaydedilemedi. Cevap adimini tekrar yapin.",
        );
        setFlowDebug("voice_answer", "failed", "VOICE_NOT_RECORDED");
        return;
      }

      setLivenessStatus("Liveness tamamlandi. Ses kimligi dogrulaniyor...");

      const res = await apiAuthVerify({
        face_image_b64: faceB64,
        voice_wav_b64: challengeVoiceB64,
      });

      const decision = String(res.decision || "").toUpperCase();
      const reason = String(res.reason || "UNKNOWN").toUpperCase();

      if (
        decision !== "ACCEPTED" &&
        decision !== "GRANTED" &&
        reason === "VOICE_NOT_MATCHED"
      ) {
        await handleVoiceVerifyFailure(reason, res);
        return;
      }

      setText(decisionEl, res.decision || "-");
      setText(faceScoreEl, (res.face_score ?? faceScore ?? 0).toFixed(3));
      setText(voiceScoreEl, (res.voice_score ?? 0).toFixed(3));
      setText(fusionScoreEl, (res.fusion_score ?? 0).toFixed(3));
      setStatus(res.reason || "DONE");
      setText(
        spoofScoreEl,
        res.spoof_score != null ? Number(res.spoof_score).toFixed(3) : "-",
      );
      setText(spoofDecisionEl, res.spoof_decision || "-");

      setFlowDebug(
        "done",
        res.decision === "ACCEPTED" || res.decision === "GRANTED" ? "passed" : "failed",
        `${res.reason || "DONE"} | SPOOF: ${res.spoof_decision || "-"} | SCORE: ${
          res.spoof_score != null ? Number(res.spoof_score).toFixed(3) : "-"
        }`,
        (res.fusion_score ?? 0).toFixed(3),
      );

      showStep("step-result");

      if (res.decision === "ACCEPTED" || res.decision === "GRANTED") {
        voiceVerifyAttempts = 0;
        const confirmedUser = res.identified_user || identifiedUser || "User";
        localStorage.setItem("portalUsername", confirmedUser);

        setTimeout(() => {
          window.location.href = "../portal/dashboard_portal.html";
        }, 2000);
      }
    } catch (e) {
      console.error(e);
      setLivenessStatus(`Verification failed: ${e.message || "UNKNOWN_ERROR"}`);
      setFlowDebug("done", "failed", "VERIFY_FAILED");
    }
  });

  // -----------------------
  // 5) Restart
  // -----------------------
  function restart() {
    stopCamera([videoEl, livenessVideoEl]);

    faceB64 = null;
    faceScore = 0;
    identifiedUser = null;
    identifiedUserId = null;
    isFaceStepPassed = false;
    isVoiceAnswerPassed = false;
    isVoiceRetryMode = false;
    voiceVerifyAttempts = 0;
    identifyChallengeId = null;
    identifyChallengePrompt = "";
    identifyChallengeExpectedKeywords = [];
    identifyChallengeExpectedNumbers = [];
    challengeVoiceB64 = null;
    livenessOrder = [];
    livenessStepIndex = 0;
    flowDebugHistory = [];

    const scoreBox = document.getElementById("voiceVerifyScoreBox");
    if (scoreBox) scoreBox.style.display = "none";

    setFaceStatus("");
    setLivenessStatus("");
    setStatus("");

    if (identifiedUserBanner) identifiedUserBanner.style.display = "none";
    if (identifiedUserName) setText(identifiedUserName, "");
    if (identifyChallengeAnswerEl) identifyChallengeAnswerEl.value = "";
    setText(identifyChallengePromptEl, "Challenge question loading...");
    setFlowDebug("face_front", "waiting", "RESTARTED");

    if (btnLivenessContinue) btnLivenessContinue.disabled = true;

    showStep("step-face");
  }

  // -----------------------
  // 6) Back
  // -----------------------
  btnBack?.addEventListener("click", (e) => {
    e.preventDefault();
    window.location.assign("../portal/login_portal.html");
  });

  btnRestartResult?.addEventListener("click", restart);
  window.restartVerify = restart;

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      restart();
      return;
    }

    const navEntry = performance.getEntriesByType("navigation")[0];
    if (navEntry && navEntry.type === "back_forward") {
      restart();
    }
  });
}
