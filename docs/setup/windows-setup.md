# 🪟 Windows Setup Guide

This document explains the recommended setup process for running the project on Windows environments.

The project is a prototype-stage multi-modal biometric authentication system that uses:

- FastAPI backend
- HTML/CSS/Vanilla JavaScript frontend
- face recognition
- voice verification
- liveness checks
- ML/audio dependencies

---

# ⚙️ Recommended Environment

Recommended:

- Windows 10 or Windows 11
- Python 3.10 or Python 3.11
- CPU-based inference environment
- Virtual environment (`venv`)
- Google Chrome or Microsoft Edge

> Python 3.10 or 3.11 is recommended because some ML/audio packages may not work reliably with newer Python versions.

---

# 📦 Install Python

Download Python from:

```text
https://www.python.org/downloads/windows/
```

During installation, make sure to enable:

```text
Add Python to PATH
```

After installation, open a new terminal and verify:

```bash
python --version
```

If multiple Python versions are installed, use the Python launcher:

```bash
py --version
```

Recommended virtual environment creation with Python 3.11:

```bash
py -3.11 -m venv venv
```

---

# 📦 Install Git

Download and install Git for Windows:

```text
https://git-scm.com/download/win
```

Verify installation:

```bash
git --version
```

Clone the repository:

```bash
git clone https://github.com/gulinkale/biometric-system.git
cd biometric-system
```

---

# ⚙️ Create Virtual Environment

From the project root:

```bash
python -m venv venv
```

Or, if multiple Python versions exist:

```bash
py -3.11 -m venv venv
```

---

# ▶️ Activate Virtual Environment

## Option 1: Command Prompt

```cmd
venv\Scripts\activate.bat
```

## Option 2: PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, the terminal should show:

```text
(venv)
```

---

# 📥 Install Dependencies

Go to the backend folder:

```bash
cd backend
```

Upgrade pip tools first:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Install project dependencies:

```bash
pip install -r requirements.txt
```

Some dependencies may take time to install, especially:

- torch
- onnxruntime
- mediapipe
- insightface
- librosa
- soundfile
- resemblyzer

---

# 🔐 Configure Environment Variables

Create a `.env` file inside the `backend/` directory.

If `.env.example` exists:

```cmd
copy .env.example .env
```

If not, create the file manually:

```text
backend/.env
```

Example minimum configuration:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

Depending on the current backend configuration, additional variables may be required, such as:

```env
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FEATURE_ENC_KEY_B64=your-fernet-key
```

> Do not commit real secrets, database passwords, or encryption keys to GitHub.

The project may not start correctly without a valid database connection.

---

# ⚠️ Visual C++ Redistributable

Some ML/audio dependencies may require Microsoft Visual C++ runtime libraries.

Install the latest supported Visual C++ Redistributable:

```text
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
```

This may be required for:

- PyTorch
- ONNX Runtime
- MediaPipe
- SoundFile
- NumPy-related native libraries
- OpenCV-related native libraries

If dependency installation fails with C++ build errors, you may also need:

- Microsoft C++ Build Tools
- Windows 10/11 SDK

This is usually only needed when pip cannot find a prebuilt wheel.

---

# 🎵 FFmpeg Installation

Some audio-processing pipelines may require FFmpeg.

Download FFmpeg:

```text
https://ffmpeg.org/download.html
```

Or install using Windows package managers.

Using Winget:

```bash
winget install Gyan.FFmpeg
```

Using Chocolatey:

```bash
choco install ffmpeg
```

After installation:

- add FFmpeg to PATH if it was not added automatically
- restart the terminal

Verify:

```bash
ffmpeg -version
```

---

# 🧠 Model Files / First Run Notes

Some ML libraries may download model files during the first run.

Examples:

- InsightFace face recognition models
- ONNX Runtime model cache
- voice embedding model files
- optional anti-spoofing model files

Make sure the machine has internet access during the first run.

If the project expects local model files, verify that the required files exist before starting the backend.

For example, if voice anti-spoofing is enabled, the project may expect a local model file such as:

```text
backend/models/AASIST.pth
```

If the model file is missing, either:

- place the required model file in the expected path
- or disable spoof enforcement in the environment configuration

---

# ▶️ Start Backend

Open a terminal.

From the project root:

```bash
cd backend
```

Make sure the virtual environment is active:

```text
(venv)
```

Start the FastAPI backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

If Swagger opens successfully, the backend is running.

---

# ▶️ Start Frontend

Open a second terminal.

Go to the project root directory.

Important:

```text
Run this command from the project root, not from the backend folder.
```

Start the frontend server:

```bash
python -m http.server 5500
```

Frontend URL:

```text
http://localhost:5500
```

Do not open HTML files directly with `file://`, because camera, microphone, and API calls may not work correctly.

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

Recommended browsers:

- Google Chrome
- Microsoft Edge

If permissions were denied accidentally, reset them from the browser site settings.

---

# ✅ Verify Installation

Check Python:

```bash
python --version
```

Check pip:

```bash
pip --version
```

Check Git:

```bash
git --version
```

Check FFmpeg:

```bash
ffmpeg -version
```

Check backend:

```text
http://127.0.0.1:8000/docs
```

Check frontend:

```text
http://localhost:5500
```

---

# ⚠️ Common Notes

## First Installation May Take Time

Some dependencies are large:

- torch
- onnxruntime
- mediapipe
- insightface
- librosa

Initial installation may take several minutes.

---

## Antivirus / Firewall Warnings

Some environments may show warnings for:

- local HTTP server
- backend API server
- microphone usage
- camera usage

This is expected for local biometric development environments.

If the frontend cannot reach the backend, verify that the backend is running on:

```text
http://127.0.0.1:8000
```

Also check that the frontend JavaScript uses the same backend API base URL.

---

## Recommended Project Location

Avoid placing the project inside paths with:

- very long folder names
- special characters
- synced folders such as OneDrive

Recommended example:

```text
C:\Projects\Biometric_System
```

This can help prevent path-related issues with ML model loading or dependency installation.

---

# 🛠️ Troubleshooting

## Virtual Environment Activation Fails

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then:

```powershell
.\venv\Scripts\Activate.ps1
```

Alternatively, use Command Prompt:

```cmd
venv\Scripts\activate.bat
```

---

## Dependency Installation Fails

Try upgrading pip tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Then reinstall:

```bash
pip install -r requirements.txt
```

If the error mentions C++ build tools, install:

- Visual C++ Redistributable
- Microsoft C++ Build Tools

---

## Backend Does Not Start

Check:

- virtual environment is active
- dependencies are installed
- `.env` file exists inside `backend/`
- `DATABASE_URL` is valid
- port `8000` is not already in use

Try:

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Frontend Cannot Connect to Backend

Check:

- backend is running
- frontend was started from the project root
- browser URL starts with `http://localhost:5500`
- backend URL is `http://127.0.0.1:8000`
- firewall is not blocking local connections

---

## Camera or Microphone Does Not Work

Check:

- browser permissions
- Windows privacy settings
- camera/microphone device availability
- another app is not already using the camera or microphone

Windows settings:

```text
Settings > Privacy & security > Camera
Settings > Privacy & security > Microphone
```

Make sure browser access is allowed.

---

# ⚠️ Prototype Disclaimer

This project is currently a prototype-stage research and engineering system.

Windows environments may require additional troubleshooting depending on:

- Python version
- CPU/GPU configuration
- installed runtime libraries
- audio subsystem configuration
- browser permissions
- local model availability
- database configuration

The system is not intended to be used as a production-ready biometric authentication platform without additional security hardening, scalability improvements, and cross-platform validation.