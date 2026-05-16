# Authentication API

# Scope

This document covers:

- authentication-related API endpoints
- JWT-based authentication behavior
- token validation
- protected route behavior
- biometric verification endpoints
- authentication-related request and response behavior

This document does NOT cover:

- detailed biometric algorithms
- enrollment internals
- infrastructure deployment
- frontend authentication UI
- low-level database implementation details


---

# Purpose

The authentication API layer is responsible for:

- user authentication
- JWT token generation
- protected API access
- biometric verification workflows
- authenticated user validation

Authentication logic is enforced on the backend rather than relying on frontend validation behavior.


---

# Current Authentication Endpoints

The current prototype primarily includes the following authentication-related routes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/login` | POST | User authentication and JWT generation |
| `/auth/verify` | POST | Multi-modal biometric verification |
| `/auth/me/biometric-status` | GET | Retrieve biometric enrollment status |

The current route structure may continue evolving as the prototype architecture matures.


---

# JWT Authentication

The backend currently uses JWT-based bearer authentication for protected API access.

JWT tokens are generated after successful login operations.

Protected routes validate:

- token authenticity
- token expiration
- authenticated user identity
- client-aware authentication context

JWT payloads currently include values such as:

- username (`sub`)
- role
- client
- expiration timestamp (`exp`)


---

# Client-Aware Authentication

The current prototype supports client-aware authentication behavior.

Authentication flows may use request headers such as:

```text
X-Client
```

Examples may include:

- `portal`
- `bank`

Client-aware authentication is used to separate authentication contexts between different client applications.


---

# POST /auth/login

## Purpose

Authenticates a user and generates a JWT bearer token.


## Request Structure

Example request:

```json
{
  "username": "example_user",
  "password": "example_password"
}
```


## Authentication Behavior

The backend currently:

- validates submitted credentials
- generates JWT access tokens
- associates authentication with a client context
- returns token-related authentication information


## Example Success Response

```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```


## Example Error Response

```json
{
  "detail": "Invalid credentials"
}
```


## Current Prototype Notes

The current authentication implementation is still evolving as the biometric authentication architecture matures.

Authentication behavior currently prioritizes biometric workflow integration and JWT-based protected access.


---

# POST /auth/verify

## Purpose

Performs multi-modal biometric verification using face and voice data.


## Verification Flow

The current verification flow primarily includes:

1. face identification
2. voice verification
3. fusion-based scoring
4. spoof-oriented analysis
5. authentication decision generation


## Request Structure

Biometric verification requests may include:

- base64-encoded face images
- base64-encoded WAV audio payloads

Example structure:

```json
{
  "face_image_b64": "base64_image",
  "voice_wav_b64": "base64_audio"
}
```


## Verification Behavior

The current prototype may perform:

- face embedding extraction
- 1:N face identification
- voice embedding comparison
- fusion-score calculation
- spoof-oriented analysis
- threshold-based authentication decisions


## Example Verification Response

Example responses may include:

```json
{
  "verified": true,
  "fusion_score": 0.91,
  "spoof_score": 0.12
}
```

Actual response structures may vary across evolving verification branches.


## Spoof-Oriented Analysis

The verification pipeline currently includes experimental spoof-analysis components.

Current spoof behavior may depend on:

- runtime configuration
- local model availability
- threshold configuration
- environment setup

Experimental spoof-analysis behavior may continue evolving.


---

# GET /auth/me/biometric-status

## Purpose

Returns biometric enrollment status information for the authenticated user.


## Authentication Requirements

This endpoint requires:

- valid JWT bearer authentication
- successful current-user extraction


## Example Response

Example responses may include:

```json
{
  "face_enrolled": true,
  "voice_enrolled": true
}
```

Response structures may continue evolving during ongoing development.


---

# Protected Route Behavior

Protected authentication routes currently use backend authentication dependencies.

Authentication dependencies currently perform:

- bearer token extraction
- JWT decoding
- token validation
- current-user lookup
- role-aware authorization

Requests with missing or invalid tokens may return:

```json
{
  "detail": "Unauthorized"
}
```


---

# Authentication Dependencies

The backend currently uses centralized authentication dependencies for protected-route enforcement.

Examples include:

- `get_current_user`
- `require_admin`

These dependencies are responsible for validating authentication and authorization requirements before endpoint execution.


---

# Request & Payload Behavior

Authentication-related APIs currently use:

- JSON request bodies
- base64-encoded image payloads
- base64-encoded WAV audio payloads
- JWT bearer headers

The current prototype may still contain partially evolving request-validation behavior.


---

# Current Prototype Limitations

The current authentication API implementation still contains several prototype-stage limitations.

Examples include:

- partially evolving response standardization
- experimental spoof-analysis behavior
- evolving verification orchestration
- partially evolving authentication flows
- incomplete API versioning

Authentication-related behavior may continue evolving as the biometric verification architecture matures.


---

# Experimental Components

Some authentication-related behaviors are currently experimental.

Examples include:

- spoof-oriented analysis
- fusion-threshold tuning
- retry-related verification behavior
- challenge-response orchestration behavior

Experimental behavior may vary depending on runtime configuration and environment setup.


---

# Security Considerations

The authentication API architecture attempts to reduce authentication risks through:

- JWT-based protected access
- backend-enforced authorization
- challenge-response verification
- fusion-oriented verification logic
- spoof-analysis components

Security-sensitive authentication behavior is enforced on the backend.


---

# Planned Improvements

Future authentication API improvements may include:

- stronger response standardization
- improved authentication observability
- stronger verification orchestration
- expanded authentication telemetry
- improved verification consistency
- versioned authentication routes
- stronger client-isolation mechanisms


---

# Summary

The authentication API layer currently provides:

- JWT-based authentication
- protected API access
- multi-modal biometric verification
- client-aware authentication behavior
- fusion-oriented verification logic
- spoof-analysis components
- authenticated biometric-status retrieval

while remaining extensible for future authentication-related improvements.