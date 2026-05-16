# 🔐 Multi-Modal Biometric Authentication System

A modular biometric authentication platform built with FastAPI, computer vision, and voice-processing technologies.

The project combines:

- face-based biometric identification
- voice-based verification
- challenge-response authentication
- liveness verification
- experimental anti-spoofing mechanisms

into a reusable multi-modal authentication architecture.

The system is designed as a prototype-stage biometric authentication platform with a modular backend and lightweight frontend clients.

---

# 🚀 Features

## Face Recognition

- Real-time face enrollment
- Face embedding extraction
- 1:N face identification via server-side comparison
- Multi-frame enrollment capture
- Pose-aware verification
- Face similarity scoring

---

## Voice Verification

- Voice embedding extraction
- Speaker similarity verification
- Audio preprocessing pipeline
- Experimental voice challenge-response verification
- Experimental voice anti-spoofing integration

---

## Liveness & Challenge Verification

- Blink detection
- Head pose verification
- Directional challenge flow
- Multi-step verification pipeline
- Randomized challenge-response structure

---

## Authentication & Backend

- JWT-based authentication
- Role-aware protected endpoints
- Modular FastAPI backend
- REST-based API architecture
- Async database integration
- Experimental multi-client authentication direction (`X-Client` architecture)

---

## Frontend

- Lightweight modular frontend
- Vanilla JavaScript architecture
- Browser-based camera capture using `getUserMedia`
- Enrollment and identification interfaces
- Portal-oriented authentication flow

---

# 🧠 Current Architecture

The system currently follows a modular architecture composed of:

- FastAPI backend service
- Browser-based frontend clients
- Face processing pipeline
- Voice processing pipeline
- Enrollment workflow
- Identification workflow
- Experimental spoof-detection components

The project is evolving toward a reusable multi-client biometric authentication architecture.

---

# 🔄 Verification Flow

## Enrollment Flow

1. User authentication
2. Face capture sequence
3. Multi-frame enrollment
4. Voice sample collection
5. Embedding extraction
6. Biometric template storage

---

## Verification Flow

1. User opens biometric verification
2. Camera and/or microphone capture begins
3. Face verification pipeline executes
4. Voice verification pipeline executes
5. Liveness checks are evaluated
6. Fusion confidence is computed
7. Verification decision is returned

---

# 🏗️ Project Structure

```text
Biometric_System/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── requirements.txt
│   └── app/main.py
│
├── clients/
│   ├── portal/
│   │   ├── assets/
│   │   │   ├── css/
│   │   │   └── js/
│   │   │
│   │   ├── pages/
│   │   │   ├── portal/
│   │   │   │   └── login_portal.html
│   │   │   │
│   │   │   └── biometric/
│   │   │       ├── enroll.html
│   │   │       └── identify.html
│   │
│   └── bank/
│
├── docs/
│
└── README.md
```

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Database | SQLite / PostgreSQL |
| ORM | SQLAlchemy |
| Authentication | JWT |
| Face Processing | InsightFace |
| Computer Vision | OpenCV, MediaPipe |
| Audio Processing | Librosa, SoundFile |
| Voice Embeddings | Resemblyzer |
| ML Runtime | PyTorch, ONNX Runtime |

---

# ⚙️ Prerequisites

- Python 3.10 (recommended)
- Python 3.11 (supported)
- pip
- virtual environment support (`venv`)

Some system-level runtime dependencies may also be required depending on the operating system.

Examples include:

- `ffmpeg`
- `libsndfile`
- Visual C++ Redistributable (Windows)

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/gulinkale/biometric-system.git
cd biometric-system
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3️⃣ Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---


## 4️⃣ Configure Environment Variables

Create a `.env` file inside the `backend/` directory.

Example:

### macOS / Linux

```bash
cp .env.example .env
```

### Windows

```bash
copy .env.example .env
```

Currently, the primary required environment variable for startup is:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

The current development environment uses a shared Supabase database instance with existing user records.

---

# 🗄️ Development Database

The current development environment uses a shared Supabase database instance.

Development and testing currently assume:

- an existing configured database
- existing biometric records
- pre-created user/admin accounts

Database connection settings are loaded through environment variables.

---

# ▶️ Running the Project

## 1️⃣ Start Backend

In the first terminal:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend will run on:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 2️⃣ Start Frontend

Open a second terminal in the project root directory:

```bash
python -m http.server 5500
```

Frontend will run on:

```text
http://localhost:5500
```

---

## 3️⃣ Open Application

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

# 🌐 Main API Endpoints

## Authentication

- `POST /auth/login`
- `POST /auth/verify`
- `GET /auth/me/biometric-status`

---

## Enrollment

- `POST /enroll/biometric`
- `POST /enroll/precheck/face`
- `POST /enroll/precheck/voice`

---

## Identification

- `POST /identify/`
- `GET /identify/voice-challenge`
- `POST /identify/pose-check`
- `POST /identify/blink-check`

---

# 📁 Documentation

Additional documentation can be found inside the `docs/` directory.

Documentation currently includes:

- architecture notes
- API documentation
- authentication roadmap
- enrollment roadmap
- migration planning
- audit reports
- service architecture evolution

---

# ⚠️ Environment Notes

The project has been tested primarily on:

- macOS (Apple Silicon)
- CPU-based inference environments

Some ML/audio dependencies may require additional runtime setup on Windows environments.

Additional OS-specific setup instructions may be provided separately.

---

# ⚠️ Security & Scalability Notes

This project is currently a prototype-stage research and engineering project.

Several components remain experimental or intentionally simplified for development and educational purposes.

Current limitations include:

- prototype-oriented authentication flows
- experimental anti-spoofing logic
- linear 1:N identification scaling
- limited cross-platform validation
- non-production deployment assumptions

Large-scale deployments would require additional optimizations such as:

- vector indexing
- ANN search structures
- distributed inference pipelines
- scalable biometric template storage

The current implementation should not be considered production-ready without additional security hardening, scalability improvements, and infrastructure validation.

---

# 📌 Current Status

The project currently represents a:

> prototype-stage reusable biometric authentication platform

The system already demonstrates:

- reusable service-oriented architecture concepts
- modular biometric processing pipelines
- multi-modal authentication logic
- client-isolated authentication direction

Some advanced components remain experimental, particularly:

- anti-spoofing
- advanced voice challenge verification
- broader cross-platform validation

---

# 📚 Research & Educational Scope

This project is intended for:

- software engineering research
- biometric authentication experimentation
- modular authentication architecture exploration
- prototype-stage system development
- educational and architectural study

It is not currently intended as a production-ready enterprise authentication platform.