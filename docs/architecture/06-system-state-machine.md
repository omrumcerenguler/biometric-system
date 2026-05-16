# System State Machine

# Scope

This document covers:

- verification state transitions
- runtime orchestration flow
- challenge sequencing
- retry behavior
- failure transitions
- session-oriented verification flow
- enrollment state progression

This document does NOT cover:

- biometric model internals
- frontend UI behavior
- infrastructure deployment
- database schema design
- low-level biometric algorithms


---

# Why Use a State Machine?

The authentication system contains multiple sequential verification stages that must execute in a controlled and predictable order.

Using a state-driven architecture helps:

- organize authentication flow
- simplify orchestration logic
- reduce inconsistent behavior
- improve maintainability
- improve debugging and monitoring
- support future extensibility

The state machine controls how the system transitions between enrollment and verification stages.


---

# State Machine Goals

The state machine architecture aims to provide:

- predictable authentication flow
- controlled biometric processing
- centralized verification orchestration
- safer error handling
- modular state transitions
- extensible verification pipelines


---

# Verification Session Lifecycle

Each authentication attempt operates as a temporary verification session.

The verification session may contain:

- current verification state
- challenge sequence
- temporary biometric signals
- liveness validation results
- spoof-related confidence
- retry counters
- session metadata

The session lifecycle ends after authentication completion or failure termination.


---

# High-Level Verification Flow

The authentication process follows multiple sequential states.

```text
IDLE
→ CHALLENGE_GENERATION
→ FACE_CAPTURE
→ FACE_LIVENESS_CHECK
→ VOICE_CAPTURE
→ VOICE_SPOOF_CHECK
→ FUSION_VERIFY
→ CONDITIONAL_RETRY (optional)
→ RESULT
```

Each state performs a specific validation or processing responsibility.


---

# State Descriptions

## IDLE

The system waits for a verification request.

Responsibilities:

- initialize verification session
- prepare authentication context
- reset temporary verification state


## CHALLENGE_GENERATION

The system generates verification challenges.

Examples:

- blink request
- directional head movement
- voice phrase prompt

The generated challenge sequence may vary between sessions.


## FACE_CAPTURE

The system captures facial frames from the camera.

Responsibilities:

- detect face presence
- collect face frames
- prepare frames for analysis
- validate basic capture quality


## FACE_LIVENESS_CHECK

The system evaluates whether the captured face interaction belongs to a live user.

Current liveness-related checks include:

- blink validation
- pose validation
- temporal interaction checks


## VOICE_CAPTURE

The system records voice samples.

Responsibilities:

- collect audio
- validate audio availability
- associate voice data with challenge prompts


## VOICE_SPOOF_CHECK

The system evaluates potential voice spoofing risks.

Examples:

- prerecorded audio detection
- synthetic voice detection
- abnormal voice analysis

Current spoof evaluation is partially experimental.


## FUSION_VERIFY

The system combines multiple biometric verification signals.

Signals include:

- face similarity
- voice similarity
- liveness confidence
- spoof confidence
- challenge completion validity

The fusion stage generates the final authentication confidence.


## CONDITIONAL_RETRY

The system may request additional verification steps when authentication confidence is insufficient.

Retry scenarios may include:

- insufficient face visibility
- unstable voice quality
- low fusion confidence
- uncertain spoof confidence
- incomplete challenge execution

The retry state attempts to reduce unnecessary false rejections.


## RESULT

The system generates the final authentication result.

Possible outcomes:

- ACCEPTED
- REJECTED
- RETRY REQUIRED

The result is returned to the client application.


---

# Verification Transition Logic

Each state transition depends on validation success.

Example:

```text
FACE_CAPTURE
→ success → FACE_LIVENESS_CHECK
→ failure → CONDITIONAL_RETRY or RESULT(REJECTED)
```

The architecture supports conditional branching depending on:

- biometric confidence
- challenge completion
- spoof confidence
- retry limits
- verification consistency


---

# Conditional State Branching

The verification flow may conditionally alter verification behavior based on runtime validation results.

Examples include:

- requesting additional challenges
- escalating liveness validation
- retrying biometric capture
- terminating suspicious sessions

This allows more flexible verification flow handling.


---

# Enrollment State Flow

The enrollment process also follows staged state transitions.

Example enrollment flow:

```text
INITIALIZE
→ FACE_ENROLLMENT
→ VOICE_ENROLLMENT
→ QUALITY_VALIDATION
→ EMBEDDING_EXTRACTION
→ PERSISTENCE
→ ENROLLMENT_COMPLETED
```

Enrollment stages ensure biometric quality before persistence.


---

# Challenge-Response State Behavior

Challenge-response validation is integrated into multiple states.

Examples:

- blink challenge during liveness validation
- directional movement during face capture
- phrase repetition during voice verification

Challenge interactions help validate real-time user participation.


---

# Error Handling States

The architecture supports failure-aware transitions.

Examples:

- invalid face capture
- missing voice input
- low biometric confidence
- spoof detection failures
- challenge timeout

The system may:

- retry the current state
- request additional input
- terminate authentication


---

# Timeout & Session Termination

The architecture may terminate verification sessions under certain conditions.

Examples include:

- excessive retry attempts
- prolonged inactivity
- repeated challenge failures
- suspicious interaction behavior

This helps reduce abuse and inconsistent verification behavior.


---

# Retry Logic

The verification architecture supports controlled retry behavior.

Retry scenarios may include:

- insufficient face visibility
- low voice quality
- failed challenge completion
- unstable liveness confidence

Retries help improve authentication robustness without immediately rejecting the user.


---

# Current Implementation

The current prototype includes staged biometric processing logic covering:

- face capture
- blink validation
- pose verification
- voice capture
- fusion-based scoring
- challenge-response interaction

The current implementation behaves similarly to a state-driven verification flow even if some orchestration logic is still evolving.


---

# Partially Implemented Components

The following state-management features are partially implemented or still evolving:

- more conditional challenge sequencing behavior
- more flexible retry orchestration
- advanced spoof-driven branching
- centralized state orchestration
- advanced verification session management


---

# Planned Improvements

Future improvements may include:

- explicit state orchestration engine
- asynchronous verification states
- distributed verification coordination
- more adaptive state-transition strategies
- passive liveness states
- continuous authentication states
- risk-based verification branching


---

# Architectural Advantages

Using a state-machine approach provides several advantages:

- cleaner orchestration logic
- modular authentication stages
- easier debugging
- improved observability
- extensible verification workflows
- easier future expansion


---

# Summary

The system uses a staged authentication architecture that behaves similarly to a state machine.

The verification flow moves through controlled biometric validation stages including:

- challenge generation
- face capture
- liveness validation
- voice verification
- spoof analysis
- fusion-based decision making
- conditional retry handling

This architecture improves authentication consistency, modularity, and scalability while supporting future expansion of the biometric verification pipeline.