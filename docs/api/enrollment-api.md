# Enrollment API

# Scope

This document covers:

- biometric enrollment-related API endpoints
- face and voice enrollment behavior
- enrollment validation flows
- duplicate-check behavior
- enrollment-related request and response behavior
- security-question enrollment flows

This document does NOT cover:

- detailed biometric algorithms
- frontend enrollment UI
- infrastructure deployment
- low-level database schema design
- authentication verification internals


---

# Purpose

The enrollment API layer is responsible for biometric registration workflows.

The current prototype primarily supports:

- face enrollment
- voice enrollment
- biometric precheck validation
- duplicate biometric detection
- security-question registration
- multi-sample enrollment processing

Enrollment-related logic is handled on the backend rather than relying on frontend validation.


---

# Current Enrollment Endpoints

The current prototype primarily includes the following enrollment-related routes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/enroll/precheck/face` | POST | Face duplicate precheck |
| `/enroll/precheck/voice` | POST | Voice duplicate precheck |
| `/enroll/biometric` | POST | Full biometric enrollment |
| `/enroll/security-questions` | GET | Retrieve available security questions |
| `/enroll/security-answers` | POST | Save security-question answers |

The current route structure may continue evolving as the prototype architecture matures.


---

# Enrollment Workflow

The current biometric enrollment workflow may include:

1. face precheck validation
2. voice precheck validation
3. face sample collection
4. voice sample collection
5. embedding extraction
6. enrollment validation
7. biometric persistence

The current prototype uses multi-sample biometric registration behavior.


---

# Face Precheck

## Endpoint

```text
POST /enroll/precheck/face
```


## Purpose

Checks whether submitted face data may already exist in the biometric database.


## Request Structure

Example requests may include:

```json
{
  "face_image_b64": "base64_image"
}
```


## Current Behavior

The current prototype may perform:

- base64 image decoding
- face embedding extraction
- normalized vector generation
- similarity-based duplicate checking

Duplicate checking currently relies on similarity-threshold logic.


## Example Response

```json
{
  "duplicate_detected": false,
  "similarity": 0.32
}
```

Actual response structures may vary across evolving prototype branches.


---

# Voice Precheck

## Endpoint

```text
POST /enroll/precheck/voice
```


## Purpose

Checks whether submitted voice data may already exist in the biometric database.


## Request Structure

Example requests may include:

```json
{
  "voice_wav_b64": "base64_audio"
}
```


## Current Behavior

The current prototype may perform:

- base64 WAV decoding
- voice embedding extraction
- normalized vector generation
- similarity-based duplicate checking


## Example Response

```json
{
  "duplicate_detected": false,
  "similarity": 0.27
}
```


---

# POST /enroll/biometric

## Purpose

Performs full biometric registration using multiple face and voice samples.


## Enrollment Inputs

The current enrollment flow may include:

- username
- role
- face samples
- voice samples
- angle-tagged face images


## Example Request Structure

Example requests may include:

```json
{
  "username": "example_user",
  "role": "user",
  "face_samples": [],
  "voice_samples": []
}
```

Actual request structures may vary depending on the frontend enrollment implementation.


---

# Face Enrollment Behavior

The current prototype may perform:

- face embedding extraction
- pose-aware enrollment validation
- angle-based sample grouping
- normalized vector generation
- aggregated embedding processing

Enrollment validation currently expects multiple face samples from different orientations.

Examples may include:

- center-facing samples
- left-facing samples
- right-facing samples


---

# Voice Enrollment Behavior

The current prototype may perform:

- WAV decoding
- voice embedding extraction
- multi-sample voice processing
- normalized voice-vector generation

Voice enrollment currently relies on multiple voice samples for registration.


---

# Enrollment Validation

Enrollment validation may include:

- minimum sample-count validation
- pose-related validation
- embedding-quality validation
- duplicate-check validation

Enrollment behavior may continue evolving as the biometric architecture matures.


---

# Security-Question Enrollment

## GET /enroll/security-questions

Returns available security questions for enrollment-related setup.

Example response:

```json
[
  {
    "id": 1,
    "question": "What is your favorite color?"
  }
]
```


## POST /enroll/security-answers

Stores security-question answers associated with the user.

Example request:

```json
{
  "answers": [
    {
      "question_id": 1,
      "answer": "blue"
    }
  ]
}
```

The current prototype may use hashed-answer validation behavior for security-question workflows.


---

# Request & Payload Behavior

Enrollment-related APIs currently use:

- JSON request bodies
- base64-encoded face images
- base64-encoded WAV audio payloads

Biometric payloads are processed on the backend for embedding extraction and validation.


---

# Enrollment Persistence

The current prototype stores biometric enrollment information in the backend database.

Current enrollment persistence may include:

- face embedding data
- voice embedding data
- enrollment metadata
- security-question associations

Biometric vectors are currently stored as serialized float-vector byte data.


---

# Current Prototype Limitations

The current enrollment implementation still contains several prototype-stage limitations.

Examples include:

- partially evolving response standardization
- experimental enrollment-validation behavior
- evolving enrollment orchestration
- limited enrollment observability
- environment-dependent ML processing behavior

Enrollment behavior currently depends on locally available ML models and runtime dependencies.


---

# ML & Runtime Dependencies

Enrollment functionality currently depends on several ML-related libraries and runtime components.

Examples include:

- InsightFace
- Resemblyzer
- MediaPipe
- librosa
- PyTorch

Missing packages or incompatible runtime environments may affect enrollment behavior.


---

# Experimental Components

Some enrollment-related behaviors are still experimental or evolving.

Examples may include:

- duplicate-threshold tuning
- pose-validation tuning
- enrollment-quality heuristics
- spoof-oriented enrollment checks

Experimental behavior may continue evolving during ongoing development.


---

# Security Considerations

The enrollment API architecture attempts to reduce enrollment-related risks through:

- duplicate biometric checks
- multi-sample enrollment validation
- pose-aware enrollment behavior
- backend-controlled biometric processing

Security-sensitive enrollment behavior is enforced on the backend.


---

# Planned Improvements

Future enrollment API improvements may include:

- stronger response standardization
- improved enrollment observability
- stronger enrollment orchestration
- improved enrollment validation consistency
- expanded anti-spoof enrollment behavior
- more modular enrollment processing


---

# Summary

The enrollment API layer currently provides:

- face enrollment
- voice enrollment
- biometric duplicate prechecks
- multi-sample biometric registration
- security-question registration
- pose-aware enrollment behavior
- backend-controlled biometric processing

while remaining extensible for future enrollment-related improvements.