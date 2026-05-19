# ADR-003: Standardized Error Response Contract

**Status:** Accepted  
**Date:** 2026-05-19  
**Author:** Agic Technology srl

---

## Context

The Fabric Universal Connector backend exposes four WDK endpoints consumed by the Fabric orchestration layer plus any future ISV tooling. Without a consistent error shape, callers must parse free-text `detail` strings and cannot distinguish between retryable and non-retryable conditions. FastAPI's default `HTTPException` model (`{"detail": "..."}`) is not expressive enough for operational observability.

---

## Decision

All non-2xx responses from this backend MUST include a JSON body with the following shape:

```json
{
  "error_code": "MACHINE_READABLE_CODE",
  "message": "Human-readable explanation",
  "details": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_code` | `string` | yes | SCREAMING_SNAKE_CASE identifier. Stable across releases. Callers may switch on this. |
| `message` | `string` | yes | English sentence. May change between releases — do not parse programmatically. |
| `details` | `object` | no | Structured supplementary data (e.g., `{"entity": "contact", "retry_after": 60}`). Omitted when empty. |

### Defined error codes

| Code | HTTP status | Meaning |
|------|-------------|---------|
| `UNAUTHORIZED` | 401 | Missing, expired, or invalid Bearer token |
| `FORBIDDEN` | 403 | Valid token but insufficient permissions |
| `JOB_NOT_FOUND` | 404 | `jobInstanceId` does not exist in the tracker |
| `CONFIG_NOT_CONFIGURED` | 400 | Connector item definition state is not `configured` |
| `CONFIG_VALIDATION_ERROR` | 400 | Item definition is malformed or missing required fields |
| `CONFIG_LOAD_ERROR` | 502 | Could not retrieve item definition from Fabric Items API |
| `AUTH_ERROR` | 502 | Source system authentication failed (MSAL / Fabric Connection) |
| `MAX_RETRIES_EXCEEDED` | 502 | Transient source errors exhausted all retry attempts |
| `ERROR_THRESHOLD_EXCEEDED` | 500 | Too many entities failed; run aborted by error threshold policy |
| `RATE_LIMIT_EXCEEDED` | 429 | Client exceeded per-IP request rate (60 req/min on start_job) |
| `UNEXPECTED_ERROR` | 500 | Unhandled exception; see container logs for stack trace |

### Non-error codes (informational)

The following are not errors but are returned in the WDK contract response body:

- `IN_PROGRESS` — job is running
- `COMPLETED` — job finished successfully (or partially — see entity-level results)
- `FAILED` — job finished with a fatal error
- `CANCELLED` — job was cancelled before completion

---

## Consequences

**Positive:**
- Fabric's job scheduler can distinguish retryable (5xx) from client errors (4xx) without parsing strings
- ISV monitoring dashboards can group incidents by `error_code`
- On-call engineers get machine-readable triage without reading container logs first
- Audit trail: `error_code` is emitted in the JSON log `extra` field alongside `job_instance_id`

**Negative / Trade-offs:**
- Existing callers that match on `detail` strings must be updated (no current external callers)
- WDK's `StartJobResponse` and `JobStatusResponse` shapes are dictated by the Fabric contract — the error body applies only to non-200 responses

---

## Implementation notes

The standardized shape is currently enforced by the `ConnectorFatalError` → `update_status(error_code=...)` pipeline in `app/api/jobs.py`. HTTP-level errors (401, 404, 429) currently use FastAPI's default `HTTPException` `{"detail": "..."}` format and should be migrated in a follow-up PR to emit `{"error_code": "...", "message": "...", "details": {}}` instead.

Priority of that migration: Medium (Fabric's scheduler does not parse the error body — it uses the HTTP status code only).

---

## Alternatives considered

**Alternative A — Use RFC 7807 Problem Details (`application/problem+json`):**  
Standard format with `type` (URI), `title`, `status`, `detail`, `instance`. Rejected because the URI-based `type` field adds complexity without benefit since Fabric's WDK contract does not specify a particular error media type.

**Alternative B — Keep FastAPI defaults (`{"detail": "..."}`):**  
Simple but not machine-parseable. Insufficient for observability requirements. Rejected.
