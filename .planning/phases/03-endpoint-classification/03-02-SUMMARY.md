---
phase: 03-endpoint-classification
plan: 02
subsystem: scenarios
tags: [false-positive-elimination, s07, s08, endpoint-classification, base-scenario]
depends_on:
  requires: [03-01-endpoint-classification-infrastructure]
  provides: [classification-aware-S07, classification-aware-S08, BaseScenario-helpers]
  affects: [04-prerequisite-aware-testing]
tech-stack:
  added: []
  patterns: [skip-and-continue-for-public, filter-expected-fields-for-auth]
key-files:
  created: []
  modified:
    - api_pentest/scenarios/base_scenario.py
    - api_pentest/scenarios/s07_access_controls.py
    - api_pentest/scenarios/s08_api_responses.py
decisions:
  - id: 03-02-D1
    decision: "Only no_auth_access and malformed_token_access skip public endpoints; undocumented_methods, CORS, debug tests unchanged"
    rationale: "Per RESEARCH.md open questions: method restriction and CORS are about data access control, not authentication. Skipping those would suppress legitimate findings."
  - id: 03-02-D2
    decision: "EXPECTED_AUTH_FIELDS is a class constant on S08, not on BaseScenario"
    rationale: "Only S08 needs this set. Keeping it local avoids polluting the base class with scenario-specific constants."
metrics:
  duration: 3min
  completed: 2026-02-04
---

# Phase 03 Plan 02: Scenario Classification Integration Summary

**Classification-aware S07 and S08 eliminating 5 targeted false positives: 3 from no_auth_access on public endpoints, 1 from malformed_token_access on public endpoint, 1 from sensitive_field_exposure on auth-endpoint.**

## What Was Done

### Task 1: BaseScenario Classification Helpers
Added `EndpointClassification` to the import statement in `base_scenario.py` and two helper methods:

- `is_public_endpoint(endpoint)` -- returns True when `endpoint.classification == EndpointClassification.PUBLIC`
- `is_auth_endpoint(endpoint)` -- returns True when `endpoint.classification == EndpointClassification.AUTH_ENDPOINT`

Placed after `is_auth_failure()`. All scenarios inherit these methods. Simple attribute checks with no complex logic.

### Task 2: S07 Auth Tests Skip Public Endpoints
Updated two methods in `s07_access_controls.py`:

**`_test_no_auth_access()`**: Replaced the old `"public-no-auth" in ep.tags` check with `self.is_public_endpoint(ep)` at the top of the endpoint loop. Public endpoints are skipped via `continue` before any HTTP request is made. The classification reason is logged at DEBUG level for audit trail. This eliminates 3 FPs:
- GET / (public, no per-operation or global security)
- GET /books/v1 (public, no per-operation or global security)
- GET /createdb (public, no per-operation or global security)

**`_test_malformed_token_access()`**: Changed endpoint selection from `self.endpoints[:5]` to `[ep for ep in self.endpoints if not self.is_public_endpoint(ep)][:5]`. This excludes public endpoints like GET / from the malformed token test. Eliminates 1 FP on GET /.

Three non-auth tests unchanged: `_test_undocumented_methods`, `_test_cors_misconfiguration`, `_test_debug_endpoints`.

### Task 3: S08 Sensitive Field Filtering for Auth-Endpoints
Updated `_test_sensitive_field_exposure()` in `s08_api_responses.py`:

Added `EXPECTED_AUTH_FIELDS` class constant containing `{auth_token, access_token, refresh_token, token, session_token, session_id}`.

After `SENSITIVE_FIELD_PATTERNS.findall(body)` returns matches, if the endpoint is classified as `AUTH_ENDPOINT`, the matches are filtered to remove expected auth fields. If no matches remain after filtering, a DEBUG log is emitted and no finding is logged. If unexpected sensitive fields remain (e.g., password, ssn), the finding is still logged.

This eliminates 1 FP: POST /users/v1/login returning `auth_token` in its response body is expected behavior for a login endpoint.

The `SENSITIVE_DATA_PATTERNS` check (SSN, credit card, base64 keys) is unchanged and applies to all endpoints including auth-endpoints. Other test methods (`verbose_error_detection`, `response_header_info_leak`, `cross_role_field_comparison`) are unchanged.

## Verified Results

All 8 verification checks pass:
1. `BaseScenario.is_public_endpoint` exists: True
2. `BaseScenario.is_auth_endpoint` exists: True
3. S07 imports clean: OK
4. S08 imports clean: OK
5. No `"public-no-auth" in ep.tags` in S07: 0 matches (removed)
6. `is_public_endpoint` found in S07: 2 occurrences (no_auth_access + malformed_token_access)
7. `is_auth_endpoint` found in S08: 1 occurrence (sensitive_field_exposure)
8. `EXPECTED_AUTH_FIELDS` found in S08: 2 occurrences (definition + usage)

## FP Elimination Summary

| FP | Scenario | Test | Endpoint | Cause | Fix |
|----|----------|------|----------|-------|-----|
| 1 | S07 | no_auth_access | GET / | Public endpoint, no auth needed | Skip via is_public_endpoint |
| 2 | S07 | no_auth_access | GET /books/v1 | Public endpoint, no auth needed | Skip via is_public_endpoint |
| 3 | S07 | no_auth_access | GET /createdb | Public endpoint, no auth needed | Skip via is_public_endpoint |
| 4 | S07 | malformed_token_access | GET / | Public endpoint, accepts any token | Filter from test_eps |
| 5 | S08 | sensitive_field_exposure | POST /users/v1/login | Login returns auth_token by design | Filter EXPECTED_AUTH_FIELDS for auth-endpoint |

Total: 5 FPs eliminated, matching Phase 3 success criteria.

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Only auth-related S07 tests skip public endpoints | Non-auth tests (undocumented methods, CORS, debug probing) test controls orthogonal to authentication |
| EXPECTED_AUTH_FIELDS on S08 class, not BaseScenario | Scenario-specific constant; only S08 sensitive field test needs it |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| fb0e3e6 | feat | Add classification helper methods to BaseScenario |
| a6d46fa | feat | Update S07 to skip auth tests for public endpoints |
| 83b632e | feat | Update S08 to filter expected auth fields for auth-endpoints |

## Next Phase Readiness

Phase 3 is complete. All 5 targeted FPs are eliminated:
- S07 no_auth_access: 3 FPs eliminated (public endpoint skip)
- S07 malformed_token_access: 1 FP eliminated (public endpoint filtered from test set)
- S08 sensitive_field_exposure: 1 FP eliminated (auth fields filtered for auth-endpoint)

Phase 4 (Prerequisite-Aware Testing) can proceed. It targets 4 FPs from S02 rate limit bypass tests where no rate limiting exists. The classification infrastructure from Phase 3 is available but Phase 4 focuses on precondition detection, a different mechanism.
