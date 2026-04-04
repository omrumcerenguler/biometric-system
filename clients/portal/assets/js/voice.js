
let audioContext = null;
let mediaStream = null;
let sourceNode = null;
let processorNode = null;

let chunks = [];
let sampleRate = 16000; // target sample rate
let isRecording = false;

function downsampleBuffer(buffer, inRate, outRate) {
  if (outRate === inRate) return buffer;

  const ratio = inRate / outRate;
  const newLen = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLen);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let sum = 0;
    let count = 0;

    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      sum += buffer[i];
      count += 1;
    }

    result[offsetResult] = count > 0 ? sum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function floatTo16BitPCM(float32) {
  const out = new Int16Array(float32.length);

  for (let i = 0; i < float32.length; i += 1) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  return out;
}

function encodeWav(int16, sr) {
  const buffer = new ArrayBuffer(44 + int16.length * 2);
  const view = new DataView(buffer);

  function writeString(offset, str) {
    for (let i = 0; i < str.length; i += 1) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + int16.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sr, true);
  view.setUint32(28, sr * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, "data");
  view.setUint32(40, int16.length * 2, true);

  let offset = 44;
  for (let i = 0; i < int16.length; i += 1, offset += 2) {
    view.setInt16(offset, int16[i], true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onloadend = () => {
      const dataUrl = reader.result;
      resolve(String(dataUrl).split(",")[1]);
    };

    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export async function startVoiceRecording() {
  if (isRecording) return;

  chunks = [];
  isRecording = true;

  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
    video: false,
  });

  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const inRate = audioContext.sampleRate;

  sourceNode = audioContext.createMediaStreamSource(mediaStream);

  // Lightweight demo approach
  processorNode = audioContext.createScriptProcessor(4096, 1, 1);

  processorNode.onaudioprocess = (e) => {
    if (!isRecording) return;

    const input = e.inputBuffer.getChannelData(0);
    const down = downsampleBuffer(input, inRate, sampleRate);
    chunks.push(down);
  };

  sourceNode.connect(processorNode);
  processorNode.connect(audioContext.destination);
}

export async function stopVoiceRecording() {
  if (!isRecording) {
    throw new Error("NOT_RECORDING");
  }

  isRecording = false;

  if (processorNode) {
    processorNode.disconnect();
  }

  if (sourceNode) {
    sourceNode.disconnect();
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
  }

  if (audioContext) {
    await audioContext.close().catch(() => {});
  }

  processorNode = null;
  sourceNode = null;
  mediaStream = null;
  audioContext = null;

  const length = chunks.reduce((acc, c) => acc + c.length, 0);

  if (length === 0) {
    throw new Error("EMPTY_RECORDING");
  }

  const merged = new Float32Array(length);
  let offset = 0;

  for (const c of chunks) {
    merged.set(c, offset);
    offset += c.length;
  }

  // minimum 1.5 seconds to avoid very weak embeddings
  const minSamples = sampleRate * 1.5;
  if (merged.length < minSamples) {
    throw new Error("RECORDING_TOO_SHORT");
  }

  const int16 = floatTo16BitPCM(merged);
  const wavBlob = encodeWav(int16, sampleRate);

  return wavBlob;
}

export async function stopVoiceRecordingToBase64() {
  const blob = await stopVoiceRecording();
  const b64 = await blobToBase64(blob);
  return { blob, b64 };
}

export async function recognizeSpeechOnce({ lang = "tr-TR", timeoutMs = 10000 } = {}) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    throw new Error("SPEECH_RECOGNITION_UNSUPPORTED");
  }

  return new Promise((resolve, reject) => {
    const recognition = new SpeechRecognition();
    let done = false;

    const finish = (fn, value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try {
        recognition.stop();
      } catch {}
      fn(value);
    };

    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event?.results?.[0]?.[0]?.transcript?.trim() || "";
      if (!transcript) {
        finish(reject, new Error("SPEECH_EMPTY"));
        return;
      }
      finish(resolve, transcript);
    };

    recognition.onerror = (event) => {
      const code = event?.error
        ? `SPEECH_${String(event.error).toUpperCase()}`
        : "SPEECH_ERROR";
      finish(reject, new Error(code));
    };

    recognition.onnomatch = () => {
      finish(reject, new Error("SPEECH_NO_MATCH"));
    };

    const timer = setTimeout(() => {
      finish(reject, new Error("SPEECH_TIMEOUT"));
    }, timeoutMs);

    recognition.start();
  });
}