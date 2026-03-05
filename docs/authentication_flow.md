## Goal

Design a multi-modal biometric verification flow using:

- Face recognition
- Voice recognition
- Random challenge-response

The system should identify the user without requiring a username input.


## Verification Strategy

The system uses multi-modal biometric authentication:

1. Face identification (1:N search)
2. Voice verification
3. Fusion scoring

Face and voice are both required.


## Challenge Strategy

Verification uses a challenge-response mechanism.

Examples:

- Look left
- Look right
- Look up
- Look down
- Speak a phrase

A minimum number of challenges is required.
If the biometric confidence is not sufficient, additional challenges are generated.

This prevents spoofing and improves reliability.


## Adaptive Challenge Logic

Minimum challenges: 2
Maximum challenges: 5

Process:

1. Generate random challenge plan
2. Execute challenges
3. Evaluate fusion score
4. If score is below threshold:
   - generate additional challenge
5. Stop when threshold reached or max challenges exceeded


## State Machine

Verification flow is implemented as a state machine:

IDLE
→ CHALLENGE
→ FACE_CAPTURE
→ VOICE_CAPTURE
→ VERIFY
→ RESULT


## Security Considerations

- Prevent replay attacks
- Prevent photo spoofing
- Prevent voice playback attacks
- Use randomized challenges