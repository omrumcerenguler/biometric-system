# 🪟 Windows Setup Guide

This document explains the recommended setup process for running the project on Windows environments.

---

# ⚙️ Recommended Environment

Recommended:

- Windows 10 or Windows 11
- Python 3.10 or 3.11
- CPU-based inference environment
- Virtual environment (`venv`)

---

# 📦 Install Python

Download Python from:

```text
https://www.python.org/downloads/windows/
```

During installation:

✅ Enable:

```text
Add Python to PATH
```

---

# ⚙️ Create Virtual Environment

From the project root:

```bash
python -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

---

# 📥 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

# ⚠️ Visual C++ Redistributable

Some ML/audio dependencies may require Microsoft Visual C++ runtime libraries.

Install:

```text
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
```

This may be required for:

- PyTorch
- ONNX Runtime
- MediaPipe
- SoundFile
- NumPy-related native libraries

---

# 🎵 FFmpeg Installation

Some audio-processing pipelines may require FFmpeg.

Download:

```text
https://ffmpeg.org/download.html
```

Or install using package managers such as Chocolatey.

After installation:

- add FFmpeg to PATH
- restart terminal

Verify:

```bash
ffmpeg -version
```

---

# ▶️ Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

---

# ▶️ Start Frontend

From the project root:

```bash
python -m http.server 5500
```

Frontend:

```text
http://localhost:5500
```

---

# 🌐 Open Application

Portal login page:

```text
http://localhost:5500/clients/portal/pages/portal/login_portal.html
```

Biometric enrollment page:

```text
http://localhost:5500/clients/portal/pages/biometric/enroll.html
```

Biometric identification page:

```text
http://localhost:5500/clients/portal/pages/biometric/identify.html
```

---

# 🎥 Camera & Microphone Permissions

When opening the application in the browser:

- allow camera access
- allow microphone access

Without permissions:

- face verification will fail
- voice verification will fail

---

# ⚠️ Common Notes

## First Installation May Take Time

Some dependencies are large:

- torch
- onnxruntime
- mediapipe

Initial installation may take several minutes.

---

## Antivirus / Firewall Warnings

Some environments may show warnings for:

- local HTTP server
- microphone usage
- camera usage

This is expected for local biometric development environments.

---

# ⚠️ Prototype Disclaimer

This project is currently a prototype-stage research and engineering system.

Windows environments may require additional troubleshooting depending on:

- Python version
- CPU/GPU configuration
- installed runtime libraries
- audio subsystem configuration