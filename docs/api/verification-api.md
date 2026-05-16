# Verification API

# Scope

This document covers:

- biometric verification-related API endpoints
- identification and verification flows
- fusion-based authentication behavior
- challenge-response validation
- liveness-related checks
- spoof-oriented analysis behavior
- verification-related request and response behavior

This document does NOT cover:

- frontend verification UI
- low-level biometric model internals
- infrastructure deployment
- database schema design
- enrollment persistence internals


---

# Purpose

The verification API layer is responsible for biometric authentication and identity-validation workflows.

The current prototype primarily supports:

- face identification
- voice verification
- fusion-based authentication decisions
- challenge-response validation
- pose validation
- blink validation
- security-question verification

Verification-related logic is handled on the backend rather than relying on frontend validation.


---

# Current Verification Endpoints

The current prototype primarily includes the following verification-related routes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/verify` | POST | Multi-modal biometric verification |
| `/identify` | POST | Face-based identification |
| `/identify/voice-challenge` | GET | Generate voice challenge |
| `/identify/voice-challenge/validate` | POST | Validate spoken challenge |
| `/identify/pose-check` | POST | Pose validation |
| `/identify/blink-check` | POST | Blink validation |
| `/identify/security-question` | GET | Retrieve security question |
| `/identify/security-answer` | POST | Validate security-question answer |

The current route structure may continue evolving as the prototype architecture matures.


---

# Verification Workflow

The current biometric verification flow may include:

1. face identification
2. voice verification
3. fusion-score calculation
4. challenge validation
5. spoof-oriented analysis
6. authentication decision generation

Verification behavior may vary depending on runtime configuration and verification conditions.


---

# POST /auth/verify

## Purpose

Performs multi-modal biometric verification using face and voice data.


## Current Verification Behavior

The current prototype may perform:

- face embedding extraction
- 1:N face identification
- voice embedding extraction
- voice-template comparison
- fusion-score calculation
- threshold-based authentication decisions
- spoof-oriented analysis


## Request Structure

Example requests may include:

```json
{
  "face_image_b64": "base64_image",
  "voice_wav_b64": "base64_audio"
}
```


## Verification Flow

The current verification flow primarily performs:

```text
face identification
→ voice verification
→ fusion scoring
→ spoof-oriented analysis
→ authentication decision
```


## Example Response

Example responses may include:

```json
{
  "verified": true,
  "fusion_score": 0.91,
  "spoof_score": 0.14
}
```

Actual response structures may vary across evolving prototype branches.


---

# Face Identification

## Endpoint

```text
POST /identify
```


## Purpose

Performs face-based user identification without requiring username input.


## Current Identification Behavior

The current prototype may perform:

- face embedding extraction
- similarity-based user comparison
- threshold-based identity selection
- 1:N biometric matching

The current implementation primarily uses in-process similarity comparison across stored biometric templates.


## Example Response

Example responses may include:

```json
{
  "identified": true,
  "username": "example_user",
  "similarity": 0.83
}
```


---

# Voice Challenge Workflow

## GET /identify/voice-challenge

Generates challenge-related voice prompts for verification workflows.

Example responses may include:

```json
{
  "challenge": "Say the number 4821"
}
```


## POST /identify/voice-challenge/validate

Validates spoken challenge responses.

The current prototype may perform:

- keyword matching
- numeric challenge validation
- speech-related heuristic checks

Example responses may include:

```json
{
  "valid": true,
  "score": 0.88
}
```


---

# Pose Validation

## Endpoint

```text
POST /identify/pose-check
```


## Purpose

Performs pose-related validation checks during verification workflows.


## Current Behavior

The current prototype may perform heuristic pose validation using:

- nose-position analysis
- orientation-related thresholds
- face-position heuristics

Example responses may include:

```json
{
  "pose_valid": true,
  "detected_pose": "left"
}
```


---

# Blink Validation

## Endpoint

```text
POST /identify/blink-check
```


## Purpose

Performs blink-related liveness checks during verification workflows.


## Current Behavior

The current prototype may perform:

- eye-aspect-ratio calculations
- threshold-based blink detection
- heuristic liveness checks

Example responses may include:

```json
{
  "blink_detected": true
}
```


---

# Security-Question Verification

## GET /identify/security-question

Returns a security question associated with the user.

Example responses may include:

```json
{
  "question_id": 2,
  "question": "What is your favorite city?"
}
```


## POST /identify/security-answer

Validates security-question answers.

The current prototype may perform:

- answer lookup
- hashed-answer comparison
- verification-result generation

Example responses may include:

```json
{
  "verified": true
}
```


---

# Fusion-Based Verification

The verification pipeline currently uses fusion-oriented authentication behavior.

Fusion scoring may combine:

- face similarity confidence
- voice similarity confidence
- challenge-validation behavior
- spoof-analysis feedback

Authentication decisions currently rely on configurable threshold behavior.


---

# Spoof-Oriented Analysis

The current prototype includes experimental spoof-analysis components.

Spoof-related behavior may depend on:

- runtime configuration
- local model availability
- threshold tuning
- device compatibility
- environment setup

Spoof-analysis behavior may continue evolving during ongoing development.


---

# Request & Payload Behavior

Verification-related APIs currently use:

- JSON request bodies
- base64-encoded face images
- base64-encoded WAV audio payloads

Verification payloads are processed on the backend for biometric analysis and authentication decisions.


---

# Current Prototype Limitations

The current verification implementation still contains several prototype-stage limitations.

Examples include:

- experimental spoof-analysis behavior
- partially evolving response standardization
- environment-dependent ML behavior
- evolving verification orchestration
- limited verification observability
- runtime-dependent verification performance

The current face-identification flow performs in-process similarity comparisons across stored user templates and may require future scalability improvements for larger datasets.


---

# ML & Runtime Dependencies

Verification functionality currently depends on several ML-related libraries and runtime components.

Examples include:

- InsightFace
- Resemblyzer
- MediaPipe
- librosa
- PyTorch

Missing packages or incompatible runtime environments may affect verification behavior.


---

# Experimental Components

Some verification-related behaviors are still experimental or evolving.

Examples may include:

- spoof-threshold tuning
- fusion-threshold tuning
- retry-related verification behavior
- challenge-related orchestration behavior
- runtime-dependent anti-spoof analysis

Experimental behavior may continue evolving during ongoing development.


---

# Security Considerations

The verification API architecture attempts to reduce authentication-related risks through:

- multi-modal verification
- challenge-response validation
- fusion-based authentication behavior
- pose-related validation
- blink-related liveness checks
- spoof-oriented analysis components

Security-sensitive verification behavior is enforced on the backend.


---

# Planned Improvements

Future verification API improvements may include:

- stronger response standardization
- improved verification observability
- improved verification scalability
- stronger verification orchestration
- expanded anti-spoof capabilities
- more modular verification pipelines


---

# Summary

The verification API layer currently provides:

- multi-modal biometric verification
- face-based identification
- voice verification
- fusion-oriented authentication behavior
- challenge-response validation
- pose-related validation
- blink-related liveness checks
- security-question verification

while remaining extensible for future verification-related improvements.