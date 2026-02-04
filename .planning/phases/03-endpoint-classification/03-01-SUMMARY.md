---
phase: 03-endpoint-classification
plan: 01
subsystem: classification
tags: [endpoint-classification, openapi, heuristics, enum, dataclass]
depends_on:
  requires: [02-response-pattern-learning]
  provides: [EndpointClassifier, EndpointClassification enum, classification fields on Endpoint, runner wiring]
  affects: [03-02, 04-prerequisite-aware-testing, 05-api-discovery]
tech-stack:
  added: []
  patterns: [three-tier-priority-chain, purpose-based-classification, audit-trail-fields]
key-files:
  created:
    - api_pentest/core/endpoint_classifier.py
  modified:
    - api_pentest/core/models.py
    - api_pentest/runner.py
decisions:
  - id: 03-01-D1
    decision: "Auth-endpoint path detection runs before OpenAPI security tier"
    rationale: "Auth-endpoint is about purpose (returns credentials), not security requirement. A login endpoint with no security definition in the spec is still an auth-endpoint. Without this, OpenAPI tier classifies /login as PUBLIC before heuristics get a chance."
  - id: 03-01-D2
    decision: "Classification default is PROTECTED"
    rationale: "Conservative default -- unknown endpoints assumed to need auth. Only classify as PUBLIC or AUTH_ENDPOINT with positive signal."
  - id: 03-01-D3
    decision: "_get_raw_spec() re-loads input file via InputDetector rather than caching during parse_input()"
    rationale: "Avoids modifying parse_input() flow. InputDetector already caches internally. Re-load is lightweight JSON parse."
metrics:
  duration: 3min
  completed: 2026-02-04
---

# Phase 03 Plan 01: Endpoint Classification Infrastructure Summary

**EndpointClassifier with three-tier priority (overrides > OpenAPI security > path heuristics) plus EndpointClassification enum on Endpoint dataclass, wired into runner after response learning.**

## What Was Done

### Task 1: EndpointClassification Enum and Fields
Added `EndpointClassification` enum to `models.py` with three values: `PUBLIC`, `PROTECTED`, `AUTH_ENDPOINT`. Added `classification` (default: PROTECTED) and `classification_reason` (default: empty string) fields to the `Endpoint` dataclass. The enum is placed before the Endpoint class. No existing behavior changed.

### Task 2: EndpointClassifier Module
Created `api_pentest/core/endpoint_classifier.py` with the `EndpointClassifier` class implementing a three-tier classification strategy:

1. **Manual overrides**: Reads `endpoint_overrides` from config, matches path, returns classification.
2. **OpenAPI security definitions**: Checks `public-no-auth` tag, `security_schemes`, and global security inheritance.
3. **Path-pattern heuristics**: Regex matching for auth-endpoint patterns (/login, /signin, /authenticate, /auth/token, /oauth/token, /token, /session) and public patterns (/register, /health, /createdb, /docs, etc.), plus root path detection.

Auth-endpoint path detection runs as an early check before the OpenAPI tier because auth-endpoint classification is about endpoint purpose (returns credentials), not security requirement. This ensures `/users/v1/login` is correctly classified as `auth-endpoint` even when the OpenAPI spec has no security definition for it.

`classify_all()` iterates all endpoints, sets classification and reason, and logs a summary at INFO level.

### Task 3: Runner Integration
Imported `EndpointClassifier` in `runner.py` and added classification invocation in the `run()` method after `response_learner.learn()` and before the scenario loop. Added `_get_raw_spec()` method that re-loads the input file via `InputDetector`, checks if it's an OpenAPI/Swagger format, and returns the raw spec dict (or None for Postman). Result is cached.

## Verified Results

VAmPI endpoint classifications:
- `GET /` -> public (no per-operation or global security defined)
- `GET /books/v1` -> public (no per-operation or global security defined)
- `GET /createdb` -> public (no per-operation or global security defined)
- `POST /users/v1/login` -> auth-endpoint (path heuristic: matches /login pattern)
- `GET /users/v1` -> protected (OpenAPI security scheme: bearerAuth)

Additional verified edge cases:
- Manual override takes priority over all other tiers
- Global security makes untagged endpoints protected
- Postman (no spec) falls through to heuristic-only classification
- `public-no-auth` tag from OpenAPI parser is recognized

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Auth-endpoint detection order in three-tier strategy**
- **Found during:** Task 2 verification
- **Issue:** The plan specified auth-endpoint detection inside the path-heuristic tier (tier 3), but the OpenAPI tier (tier 2) classified `/users/v1/login` as PUBLIC first (no security defined, no global security). The heuristic tier never ran for login.
- **Fix:** Moved auth-endpoint path detection to run as an early check after manual overrides but before the OpenAPI security tier. Auth-endpoint is about purpose, not security requirement, so it correctly takes precedence.
- **Files modified:** `api_pentest/core/endpoint_classifier.py`
- **Commit:** 076d33a

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Auth-endpoint path detection before OpenAPI tier | Purpose-based classification (returns credentials) is independent of security requirement. Without this, OpenAPI says "no security = public" and login never gets classified as auth-endpoint. |
| PROTECTED as default | Conservative -- assume auth needed unless positive signal says otherwise |
| _get_raw_spec() via InputDetector | Avoids modifying parse_input(); InputDetector handles format detection and loading cleanly |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 480039f | feat | Add EndpointClassification enum and classification fields to Endpoint |
| 076d33a | feat | Create EndpointClassifier with three-tier classification strategy |
| c192861 | feat | Wire EndpointClassifier into runner between learning and scenarios |

## Next Phase Readiness

Plan 03-02 can proceed immediately. The classification infrastructure is complete:
- `EndpointClassification` enum is available for import
- `Endpoint.classification` field is populated before scenarios run
- S07 and S08 can check `ep.classification` to skip irrelevant tests
- BaseScenario helper methods (`is_public_endpoint`, `is_auth_endpoint`) should be added in 03-02
