---
status: complete
phase: 03-endpoint-classification
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-05T12:00:00Z
updated: 2026-02-05T12:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Public Endpoints Not Flagged for Missing Auth
expected: Run a scan against VAmPI and check the output. The endpoints GET /, GET /books/v1, and GET /createdb should NOT be flagged for "missing authentication" or "no auth access" in S07 findings. They are public endpoints.
result: pass
verified: GET / -> public, GET /books/v1 -> public, GET /createdb -> public. S07._test_no_auth_access() calls is_public_endpoint() and skips these endpoints.

### 2. Login Endpoint Not Flagged for Data Exposure (auth_token)
expected: Run a scan against VAmPI and check S08 findings. POST /users/v1/login returning auth_token in the response should NOT be flagged as "sensitive field exposure". The auth_token is expected from a login endpoint.
result: pass
verified: POST /users/v1/login -> auth-endpoint (path heuristic). S08._test_sensitive_field_exposure() filters EXPECTED_AUTH_FIELDS {auth_token, access_token, refresh_token, token, session_token, session_id} for auth-endpoints.

### 3. Classification Logged in Scan Output
expected: When running with DEBUG or INFO logging, you should see a message like "Classified N endpoints: X public, Y protected, Z auth-endpoint" showing that endpoint classification is happening before security tests run.
result: pass
verified: EndpointClassifier.classify_all() logs summary at INFO level. Classification runs after response learning and before scenario loop in runner.

### 4. Protected Endpoints Still Tested
expected: Endpoints with security requirements (e.g., GET /users/v1 with bearerAuth) should still be tested by S07 auth tests. Only public endpoints are skipped. Check that protected endpoint auth tests still run and produce findings if vulnerabilities exist.
result: pass
verified: GET /users/v1 -> protected (OpenAPI security scheme: bearerAuth). S07 only skips public endpoints; protected endpoints pass through to auth tests.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
