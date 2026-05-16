# API Overview

# Scope

This document covers:

- API-first backend architecture
- endpoint organization
- authentication-related API behavior
- API communication structure
- request and response conventions
- current backend API stack
- prototype-stage API limitations

This document does NOT cover:

- detailed biometric algorithms
- frontend implementation details
- infrastructure deployment
- low-level database internals
- endpoint-specific business logic


---

# API Philosophy

The system is designed as an API-first biometric authentication platform.

The backend acts as the primary authentication engine, while frontend applications operate as API consumers.

The API architecture aims to provide:

- reusable biometric authentication services
- frontend-independent verification workflows
- modular endpoint organization
- structured API communication
- extensible authentication behavior

The backend is responsible for authentication, verification, authorization, and biometric-processing workflows.


---

# API-First Architecture

The backend is designed so that biometric operations can be accessed independently from a specific frontend implementation.

The APIs may be accessed through:

- web applications
- mobile applications
- Postman
- curl
- third-party systems
- external services

The frontend portal is treated as one possible API client rather than the owner of authentication logic.


---

# Current API Structure

The current backend prototype primarily organizes endpoints into the following categories:

| Category | Purpose |
|---|---|
| Authentication APIs | Login and token-based authentication |
| Enrollment APIs | Biometric registration |
| Verification APIs | Biometric verification |
| Identification APIs | Username-free biometric identification |
| Administrative APIs | Protected administrative operations |

The backend currently exposes REST-style HTTP endpoints through a FastAPI-based architecture.


---

# Current Endpoint Organization

The current backend implementation primarily uses the following route groups:

| Route Group | Purpose |
|---|---|
| `/auth` | Authentication and verification |
| `/enroll` | Biometric enrollment |
| `/identify` | Identification and liveness-related operations |
| `/admin` | Administrative functionality |

The current route structure may continue evolving as the prototype architecture matures.


---

# Authentication Strategy

Protected API endpoints currently use JWT-based bearer authentication.

Authentication responsibilities include:

- token generation
- token validation
- current-user extraction
- role-aware authorization

Protected routes require valid bearer tokens.

Some administrative operations additionally require elevated authorization roles.


---

# Client-Aware Authentication

The current prototype supports client-aware authentication behavior.

The backend currently supports concepts such as:

- client-specific user ownership
- client-aware authentication flows
- client-specific login behavior

The current implementation may rely on request headers such as `X-Client` for client-aware behavior.


---

# Request & Response Behavior

The backend currently exchanges JSON-based request and response payloads.

Biometric operations may use:

- base64-encoded face images
- base64-encoded WAV audio payloads
- structured JSON request bodies

The architecture aims to provide increasingly standardized API responses, although some endpoints still contain partially evolving response behavior.


---

# Current Backend Stack

The current backend prototype primarily uses:

- FastAPI
- Pydantic
- SQLAlchemy
- JWT-based authentication
- PostgreSQL compatibility
- SQLite-based development support

Biometric processing currently relies on components such as:

- InsightFace
- Resemblyzer
- MediaPipe
- PyTorch-based spoof-analysis components


---

# Experimental Components

Some API behaviors are still experimental or evolving.

Examples include:

- spoof-oriented verification behavior
- fusion-scoring behavior
- challenge-response orchestration
- retry-related verification behavior
- anti-spoof evaluation components

Experimental behavior may continue evolving as the prototype architecture matures.


---

# Current Prototype Limitations

The current prototype still contains several evolving areas and implementation limitations.

Examples include:

- partially evolving response standardization
- evolving API structure
- incomplete API versioning
- experimental spoof-analysis behavior
- evolving verification orchestration behavior
- partially evolving observability support

The architecture currently prioritizes biometric verification workflows and modular backend experimentation.


---

# API Versioning

The architecture is designed to support future API versioning strategies.

Example future structure:

```text
/api/v1/auth/login
/api/v1/enroll/biometric
/api/v1/identify/verify
```

The current prototype does not yet fully implement versioned route organization.


---

# Frontend Independence

The backend APIs are designed to remain reusable across different client applications.

The current frontend implementation acts as one possible API consumer.

The backend authentication logic is intended to remain centralized and reusable independently from frontend UI behavior.


---

# Current Security Model

The API architecture currently includes:

- JWT-based authentication
- role-aware authorization
- protected administrative routes
- challenge-response verification
- fusion-based verification logic
- spoof-oriented analysis components

Security-sensitive logic is enforced on the backend rather than relying on frontend validation.


---

# Planned Improvements

Future API-related improvements may include:

- stronger response standardization
- centralized error handling
- improved API observability
- stronger request validation
- expanded administrative APIs
- versioned API organization
- more modular orchestration behavior
- stronger client-isolation mechanisms


---

# Summary

The backend follows an API-first biometric authentication architecture built around reusable backend services.

The current prototype API layer includes:

- JWT-based authentication
- biometric enrollment
- biometric verification
- username-free identification workflows
- challenge-response validation
- fusion-oriented verification behavior
- protected administrative operations

while remaining extensible for future architectural improvements.