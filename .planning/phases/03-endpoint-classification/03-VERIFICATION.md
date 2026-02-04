---
phase: 03-endpoint-classification
verified: 2026-02-04T20:19:30+03:00
status: passed
score: 11/11 must-haves verified
---

# Phase 3: Endpoint Classification Verification Report

**Phase Goal:** The toolkit distinguishes public from protected endpoints and understands endpoint purpose, so it does not flag expected behavior as vulnerabilities

**Verified:** 2026-02-04T20:19:30+03:00
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every endpoint has a classification field (public, protected, or auth-endpoint) after parsing | ✓ VERIFIED | Endpoint dataclass has `classification: EndpointClassification = EndpointClassification.PROTECTED` field (models.py:62). Default is PROTECTED. |
| 2 | Classification uses three-tier priority: manual overrides > OpenAPI security definitions > path heuristics | ✓ VERIFIED | _classify() method (endpoint_classifier.py:73-100) implements priority chain: _check_overrides() → _check_auth_endpoint_path() → _classify_from_openapi() → _classify_from_path_patterns(). Manual override tested and confirmed to override global security. |
| 3 | VAmPI endpoints /, /books/v1, /createdb are classified as public | ✓ VERIFIED | Test run confirmed: GET / => public (no per-operation or global security defined), GET /books/v1 => public, GET /createdb => public. Classification leverages OpenAPI tier when spec has no global security. |
| 4 | VAmPI endpoint /users/v1/login is classified as auth-endpoint | ✓ VERIFIED | Test run confirmed: POST /users/v1/login => auth-endpoint (path heuristic: matches /login pattern). Auth-endpoint detection runs before OpenAPI tier per 03-01 decision D1. |
| 5 | Endpoints with security schemes are classified as protected | ✓ VERIFIED | _classify_from_openapi() checks endpoint.security_schemes (line 151-153). Test confirmed: endpoint with security_schemes=['bearerAuth'] => protected (OpenAPI security scheme: bearerAuth). |
| 6 | Default classification is protected when no signal matches | ✓ VERIFIED | _classify_from_path_patterns() returns PROTECTED with reason "default classification (no matching signal)" (line 183). Without spec, unknown paths get protected. With spec but no global security, they get public (explicit OpenAPI signal). |
| 7 | S07 no_auth_access skips endpoints classified as public | ✓ VERIFIED | _test_no_auth_access() (s07:63-69) checks `if self.is_public_endpoint(ep): continue` before making request. Logs skip at DEBUG with classification_reason. No findings logged for /, /books/v1, /createdb. |
| 8 | S07 malformed_token_access skips endpoints classified as public | ✓ VERIFIED | _test_malformed_token_access() (s07:115) filters test set: `test_eps = [ep for ep in self.endpoints if not self.is_public_endpoint(ep)][:5]`. Public endpoints excluded from malformed token test. |
| 9 | S08 sensitive_field_exposure filters out expected auth fields for auth-endpoint | ✓ VERIFIED | _test_sensitive_field_exposure() (s08:101-111) checks `if self.is_auth_endpoint(ep)` and filters field_matches against EXPECTED_AUTH_FIELDS. auth_token, access_token, refresh_token, token, session_token, session_id filtered for login endpoints. |
| 10 | Skipped tests are logged at DEBUG level with classification reason | ✓ VERIFIED | S07 no_auth_access logs: `logger.debug("Skipping no-auth test for %s %s: %s", ep.method, ep.url, ep.classification_reason)` (s07:65-68). S08 logs: `logger.debug("Skipping sensitive field finding for auth-endpoint...")` (s08:107-111). |
| 11 | All other S07 and S08 tests continue to run unchanged for protected endpoints | ✓ VERIFIED | Only 2 S07 tests modified (no_auth_access, malformed_token_access). Other 3 tests (undocumented_methods, cors_misconfiguration, debug_endpoint_probing) unchanged. Only 1 S08 test modified (sensitive_field_exposure). Other 3 tests (verbose_error_detection, response_header_info_leak, cross_role_field_comparison) unchanged. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api_pentest/core/endpoint_classifier.py` | EndpointClassifier with three-tier classification strategy | ✓ VERIFIED | 194 lines. Contains EndpointClassifier class with classify_all(), _classify(), _check_overrides(), _check_auth_endpoint_path(), _classify_from_openapi(), _classify_from_path_patterns(), _has_global_security(). No stub patterns. |
| `api_pentest/core/models.py` | EndpointClassification enum and classification fields on Endpoint | ✓ VERIFIED | 176 lines. EndpointClassification enum with PUBLIC, PROTECTED, AUTH_ENDPOINT (lines 39-42). Endpoint dataclass has classification (default PROTECTED) and classification_reason fields (lines 62-63). |
| `api_pentest/runner.py` | Classifier invocation between parse and scenario execution | ✓ VERIFIED | 319 lines. Imports EndpointClassifier (line 7). Calls classifier.classify_all() in run() after response_learner.learn() and before scenario loop (lines 160-165). _get_raw_spec() method provides OpenAPI spec (lines 293-319). |
| `api_pentest/scenarios/base_scenario.py` | is_public_endpoint() and is_auth_endpoint() helper methods | ✓ VERIFIED | 226 lines. Imports EndpointClassification (line 9). Has is_public_endpoint() (lines 220-222) and is_auth_endpoint() (lines 224-226) methods. Simple attribute checks. |
| `api_pentest/scenarios/s07_access_controls.py` | Classification-aware no_auth_access and malformed_token_access tests | ✓ VERIFIED | 334 lines. _test_no_auth_access() uses is_public_endpoint() with skip-and-continue (line 64). _test_malformed_token_access() filters test_eps to exclude public (line 115). Old "public-no-auth" in ep.tags check removed. |
| `api_pentest/scenarios/s08_api_responses.py` | Classification-aware sensitive_field_exposure test | ✓ VERIFIED | 367 lines. EXPECTED_AUTH_FIELDS constant (lines 59-62). _test_sensitive_field_exposure() uses is_auth_endpoint() to filter field_matches (lines 101-111). Only auth fields filtered; non-auth sensitive fields (password, ssn) still flagged. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| runner.py | endpoint_classifier.py | import and classify_all() call | ✓ WIRED | Import on line 7. Call on line 165 after response_learner.learn(), before scenarios. |
| endpoint_classifier.py | models.py | uses EndpointClassification enum and Endpoint fields | ✓ WIRED | Imports EndpointClassification and Endpoint (line 15). Sets endpoint.classification and endpoint.classification_reason in classify_all() (lines 58-59). |
| base_scenario.py | models.py | imports EndpointClassification | ✓ WIRED | Import on line 9. Used in is_public_endpoint() and is_auth_endpoint() checks. |
| s07_access_controls.py | base_scenario.py | calls self.is_public_endpoint(ep) | ✓ WIRED | Used in _test_no_auth_access() (line 64) and _test_malformed_token_access() (line 115). |
| s08_api_responses.py | base_scenario.py | calls self.is_auth_endpoint(ep) | ✓ WIRED | Used in _test_sensitive_field_exposure() (line 101) to filter expected auth fields. |

### Requirements Coverage

Phase 3 requirements from REQUIREMENTS.md:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DISC-03: Classify endpoints as public vs protected using OpenAPI security definitions | ✓ SATISFIED | EndpointClassifier._classify_from_openapi() uses OpenAPI security metadata. VAmPI endpoints correctly classified. |
| VALID-01: Validate test results against API profile (don't flag public endpoints for missing auth) | ✓ SATISFIED | S07 no_auth_access and malformed_token_access skip public endpoints. No findings logged for /, /books/v1, /createdb. |
| VALID-03: Context-aware finding validation (login endpoints returning tokens is expected, not data exposure) | ✓ SATISFIED | S08 sensitive_field_exposure filters EXPECTED_AUTH_FIELDS for auth-endpoint classified endpoints. /users/v1/login returning auth_token no longer flagged. |
| FIX-02: Fix false positives from public endpoints flagged for no auth (4 findings) | ✓ SATISFIED | S07 skips auth tests for public endpoints. 3 FPs from no_auth_access (/, /books/v1, /createdb) + 1 FP from malformed_token_access (/) eliminated. |
| FIX-03: Fix false positive from login endpoint returning auth_token (1 finding) | ✓ SATISFIED | S08 filters auth_token from findings when endpoint is classified as auth-endpoint. 1 FP from POST /users/v1/login eliminated. |

Total: 5/5 requirements satisfied

### Anti-Patterns Found

**None.** No blocker, warning, or notable anti-patterns detected.

Scanned files:
- api_pentest/core/endpoint_classifier.py (194 lines)
- api_pentest/core/models.py (176 lines)
- api_pentest/runner.py (319 lines)
- api_pentest/scenarios/base_scenario.py (226 lines)
- api_pentest/scenarios/s07_access_controls.py (334 lines)
- api_pentest/scenarios/s08_api_responses.py (367 lines)

Checks:
- No TODO/FIXME/placeholder comments found
- No empty return stubs (return None in classifier is legitimate for optional conditions)
- No console.log-only implementations
- All exports present and used
- All methods substantive (well above minimum line thresholds)

### Human Verification Required

None. All must-haves are structurally verifiable.

The phase eliminates false positives by skipping irrelevant tests and filtering expected fields. This is structural logic that can be verified by code inspection and unit testing, not runtime behavior requiring human observation.

### Verification Notes

**1. Classification Priority Chain**

Tested three-tier priority:
- Manual override beats OpenAPI security: ✓ (public override applied despite global security)
- OpenAPI security beats path heuristics: ✓ (security_schemes forces protected even if path matches public pattern)
- Path heuristics provide fallback: ✓ (/login classified as auth-endpoint, /createdb as public)

**2. Auth-Endpoint Detection Before OpenAPI Tier**

Per 03-01 decision D1, auth-endpoint path detection runs as an early check before the OpenAPI security tier. This is correct because auth-endpoint classification is about endpoint *purpose* (returns credentials), not security requirement. Verified in code: _check_auth_endpoint_path() called after overrides but before _classify_from_openapi() (lines 88-91).

**3. Default Classification Context**

Default behavior is context-aware:
- With OpenAPI spec + no global security: public (explicit "no security" signal from spec)
- With OpenAPI spec + global security: protected (inherits global security)
- Without spec (Postman) or no matches: protected (conservative default)

This is correct per plan. The "default is protected" refers to the fallback when no classification signal matches, not to all OpenAPI cases.

**4. False Positive Elimination**

Verified FP elimination targets:
- S07 no_auth_access on GET /: ✓ (skipped, public)
- S07 no_auth_access on GET /books/v1: ✓ (skipped, public)
- S07 no_auth_access on GET /createdb: ✓ (skipped, public)
- S07 malformed_token_access on GET /: ✓ (excluded from test set, public)
- S08 sensitive_field_exposure on POST /users/v1/login: ✓ (auth_token filtered, auth-endpoint)

Total: 5 FPs eliminated, matching Phase 3 success criteria.

**5. Non-Auth Tests Unchanged**

Verified that only auth-related tests were modified:
- S07: 2/5 tests modified (no_auth_access, malformed_token_access)
- S07: 3/5 tests unchanged (undocumented_methods, cors_misconfiguration, debug_endpoint_probing)
- S08: 1/4 tests modified (sensitive_field_exposure)
- S08: 3/4 tests unchanged (verbose_error_detection, response_header_info_leak, cross_role_field_comparison)

This is correct per 03-02 decision D1: method restriction and CORS tests are about data access control, not authentication, so they should run for all endpoints.

---

_Verified: 2026-02-04T20:19:30+03:00_
_Verifier: Claude (gsd-verifier)_
