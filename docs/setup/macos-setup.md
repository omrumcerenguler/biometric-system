# 🍎 macOS Setup Guide

This document explains the recommended setup process for running the project on macOS environments.

---

# ⚙️ Recommended Environment

Recommended:

- macOS
- Apple Silicon (M-series) or Intel Mac
- Python 3.10 or 3.11
- Virtual environment (`venv`)

The project has primarily been tested on Apple Silicon environments.

---

# 📦 Install Python

Recommended installation method:

```text
https://www.python.org/downloads/macos/
```

Or via Homebrew:

```bash
brew install python
```

Verify:

```bash
python3 --version
```

---

# ⚙️ Create Virtual Environment

From the project root:

```bash
python3 -m venv venv
```

Activate:

```bash
source venv/bin/activate
```

---

# 📥 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

# 🎵 Install FFmpeg

Install using Homebrew:

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

---

# 🔊 Install libsndfile

Some audio-processing libraries depend on libsndfile.

Install:

```bash
brew install libsndfile
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
python3 -m http.server 5500
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

macOS may request:

- camera permissions
- microphone permissions

Grant access from:

```text
System Settings → Privacy & Security
```

Without permissions:

- face verification will fail
- voice verification will fail

---

# 🍎 Apple Silicon Notes

The project has primarily been tested on Apple Silicon environments.

Some ML dependencies may behave differently on:

- Intel Macs
- older macOS versions

---

# ⚠️ Common Notes

## First Installation May Take Time

Some dependencies are large:

- torch
- onnxruntime
- mediapipe

Initial installation may take several minutes.

---

## Native Dependency Behavior

Some ML/audio libraries rely on native runtime components and platform-specific wheels.

Behavior may vary depending on:

- macOS version
- Python version
- CPU architecture

---

# ⚠️ Prototype Disclaimer

This project is currently a prototype-stage research and engineering system.

Some biometric, audio, and ML components remain experimental and may require additional troubleshooting depending on the local environment.