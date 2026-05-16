# Response Format

# Scope

This document covers:

- API response philosophy
- success response structures
- error response structures
- validation-related responses
- authentication-related responses
- HTTP status code conventions
- current response-format limitations

This document does NOT cover:

- frontend UI rendering
- low-level exception handling internals
- infrastructure logging pipelines
- database schema behavior
- endpoint-specific business logic


---

# Response Philosophy

The backend architecture aims to provide structured and predictable API responses across authentication, enrollment, verification, and administrative endpoints.

Consistent response behavior helps improve:

- frontend integration
- debugging
- maintainability
- client-side validation
- API readability

The current prototype still contains partially evolving response behavior across some endpoints.


---

# General Response Structure

The backend architecture aims to standardize responses using a structure similar to:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Typical response sections include:

| Field | Purpose |
|---|---|
| success | Indicates whether the request succeeded |
| data | Contains returned response data |
| error | Contains error information if the request fails |

The current prototype may still contain endpoint-specific response variations during ongoing development.


---

# Success Responses

Successful API operations typically return:

- `success: true`
- response-related data
- appropriate HTTP status codes

Example:

```json
{
  "success": true,
  "data": {
    "message": "Authentication successful"
  },
  "error": null
}
```

Some endpoints may additionally return:

- JWT tokens
- similarity scores
- enrollment status information
- verification metadata
- challenge-related feedback


---

# Error Responses

Failed requests typically return:

- `success: false`
- error-related information
- appropriate HTTP error status codes

Example:

```json
{
  "success": false,
  "data": null,
  "error": "Authentication failed"
}
```

Some endpoints currently rely on FastAPI exception handling behavior rather than fully centralized response formatting.


---

# Validation Errors

Validation-related failures may occur when:

- required fields are missing
- malformed biometric data is submitted
- unsupported payload formats are received
- request structures are invalid

Example:

```json
{
  "success": false,
  "data": null,
  "error": "Invalid request payload"
}
```

The backend currently uses FastAPI and Pydantic for request validation.


---

# FastAPI Validation Responses

Some validation-related responses currently follow FastAPI’s default validation structure.

Example:

```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

Validation-response standardization is still evolving within the current prototype.


---

# Authentication Errors

Authentication-related failures may occur when:

- JWT tokens are missing
- invalid bearer tokens are provided
- token validation fails
- authentication expires

Example:

```json
{
  "detail": "Unauthorized"
}
```

Protected endpoints require valid JWT bearer authentication.


---

# Authorization Errors

Authorization-related failures may occur when:

- insufficient privileges are detected
- non-admin users access protected administrative routes
- role validation fails

Example:

```json
{
  "detail": "Forbidden"
}
```

Administrative operations require elevated authorization roles.


---

# Verification-Related Responses

Biometric verification endpoints may return additional verification-related metadata.

Examples may include:

- authentication decisions
- similarity confidence values
- liveness-related feedback
- spoof-oriented analysis results
- retry recommendations

The exact response structure may vary across evolving prototype endpoints.


---

# Enrollment-Related Responses

Enrollment endpoints may return registration-related information.

Examples may include:

- enrollment success status
- biometric registration progress
- enrollment validation feedback
- enrollment completion metadata


---

# HTTP Status Code Conventions

The backend attempts to use standard HTTP status codes.

Common examples include:

| Status Code | Meaning |
|---|---|
| 200 | Successful request |
| 400 | Invalid request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Resource not found |
| 422 | Validation error |
| 500 | Internal server error |

Some endpoints in the current prototype may still contain partially evolving error-handling behavior.


---

# Current Prototype Limitations

The current response-format implementation still contains several prototype-stage limitations.

Examples include:

- partially inconsistent response formatting
- endpoint-specific response variations
- evolving validation behavior
- incomplete response standardization
- mixed FastAPI exception handling behavior

The architecture is still transitioning toward more centralized response handling.


---

# Experimental & Evolving Responses

Some API response structures are still evolving.

Examples may include:

- spoof-related confidence responses
- fusion-scoring metadata
- retry-related verification feedback
- challenge-response metadata

These structures may continue evolving as the prototype architecture matures.


---

# Planned Improvements

Future response-format improvements may include:

- stronger response standardization
- centralized error handling
- reusable response utilities
- improved validation consistency
- improved verification metadata organization
- enhanced API observability support


---

# Summary

The backend architecture aims to provide structured and predictable API responses for biometric authentication workflows.

The current prototype includes:

- success and error response handling
- JWT-related authentication responses
- verification-related metadata
- enrollment-related response behavior
- FastAPI and Pydantic-based validation handling

while remaining extensible for future response-standardization improvements.