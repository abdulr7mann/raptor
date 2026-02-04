# Phase 2: Response Pattern Learning - Research

**Researched:** 2026-02-04
**Domain:** API response pattern analysis for false positive elimination
**Confidence:** HIGH

## Summary

Phase 2 must teach the toolkit to distinguish between HTTP 200 responses that represent genuine success and HTTP 200 responses where the application rejected the request but returned a 200 status code with a failure body. Currently, scenarios S06, S09, and S13 use `self.is_success_status(evidence.response_status)` -- a simple 200-299 range check -- as the sole indicator of whether an attack succeeded. This produces 10 false positives against VAmPI because VAmPI (like many real APIs) returns HTTP 200 with `{"status": "fail", ...}` when operations are denied.

The solution is a two-part system: (1) a pre-scan learning pass that probes each endpoint and records what "success" and "failure" look like in the response body, and (2) a replacement for `is_success_status()` that checks both HTTP status code AND learned body patterns. The learning pass is fully automatic and integrated into the existing `PentestRunner.run()` flow before scenario execution. No new libraries are needed -- this is pure Python logic operating on JSON responses.

**Primary recommendation:** Build a `ResponsePatternLearner` class in `api_pentest/core/response_patterns.py` that runs as a pre-pass in the runner, learns per-endpoint success/failure body indicators, and exposes a `is_real_success(evidence)` method that scenarios use instead of `is_success_status()`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | N/A | Parse response bodies | Already used throughout codebase |
| Python stdlib `re` | N/A | Pattern matching in non-JSON responses | Already used in scenarios |
| Python stdlib `dataclasses` | N/A | Data structures for learned patterns | Consistent with existing models.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `logging` | N/A | Debug/verbose output of learned patterns | Consistent with codebase logging |
| Python stdlib `statistics` | N/A | Response length analysis (mean/stdev) | If using length-based differentiation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom JSON field analysis | jsonschema validation | Overkill -- we need field presence/value checks, not schema validation |
| Custom pattern matching | ML-based classification | Way too complex for a deterministic problem with clear signal fields |
| Per-endpoint learning | Global API-wide patterns | Per-endpoint is more accurate -- different endpoints may use different patterns |

**Installation:**
```bash
# No new dependencies needed -- pure Python stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  core/
    response_patterns.py    # NEW: ResponsePatternLearner + ResponsePattern dataclass
    models.py               # Evidence, Finding (unchanged)
    http_client.py          # PentestHttpClient (unchanged)
  runner.py                 # Modified: calls learner before scenarios
  scenarios/
    base_scenario.py        # Modified: adds is_real_success() using learned patterns
    s06_privileged_access.py   # Modified: replace is_success_status with is_real_success
    s09_business_flow.py       # Modified: replace is_success_status with is_real_success
    s13_unsafe_consumption.py  # Modified: replace is_success_status with is_real_success
```

### Pattern 1: Pre-Scan Learning Pass
**What:** Before any security tests run, the runner sends "baseline" requests to each endpoint and analyzes the responses to learn what success vs failure looks like for that API.
**When to use:** Always -- integrated into normal scan flow.
**How it works:**

The learning algorithm operates in three steps:

1. **Probe with valid credentials**: Send a normal request with valid auth to each endpoint using the same parameters from the parsed spec. Record the response body, status code, and content type.

2. **Probe with invalid/no credentials**: For auth-required endpoints, send a request without auth or with invalid auth. This deliberately triggers a failure response. Record how the API communicates "you are not authorized."

3. **Extract patterns**: Compare success and failure responses to identify the distinguishing signals.

```python
# Conceptual pattern -- not final implementation
@dataclass
class ResponsePattern:
    """Learned success/failure indicators for a single endpoint."""
    endpoint_key: str               # "GET:/users/v1"

    # Status field detection (e.g., {"status": "fail"})
    status_field: str | None        # JSON field name, e.g. "status"
    success_values: set[str]        # e.g. {"success"}
    failure_values: set[str]        # e.g. {"fail"}

    # Error indicator fields
    error_field: str | None         # e.g. "error", "message" (when present only on failures)

    # Response structure fingerprint
    success_keys: set[str] | None   # Top-level keys present in success responses
    failure_keys: set[str] | None   # Top-level keys present in failure responses

    # Fallback: response length analysis
    success_length_range: tuple[int, int] | None  # (min, max) observed success lengths
```

### Pattern 2: Hierarchical Signal Detection
**What:** Check response body signals in priority order -- explicit status fields first, then structural differences, then length as last resort.
**When to use:** When evaluating whether a response represents a real success.

The signal hierarchy (check in this order, stop at first match):

1. **Explicit status field** (HIGH confidence): JSON body has a field like `"status"` with value `"fail"` or `"success"`. This is the most reliable signal. VAmPI uses exactly this pattern.

2. **Error indicator field** (HIGH confidence): JSON body has an `"error"` or `"message"` field that only appears in failure responses. Many APIs use `{"error": "..."}` format.

3. **Structural difference** (MEDIUM confidence): Success responses have different top-level keys than failure responses. For example, success has `{"data": {...}}` while failure has `{"error": "..."}`.

4. **Known failure phrases** (MEDIUM confidence): Response body contains common failure phrases like "not authorized", "permission denied", "access denied", "forbidden", "not found", "not allowed", "invalid token", "expired".

5. **Response length anomaly** (LOW confidence, fallback only): If success responses are consistently 500+ bytes and this response is 50 bytes, it is likely a terse error message.

```python
def is_real_success(self, evidence: Evidence, endpoint_key: str) -> bool:
    """Check if response represents genuine application-level success."""
    # Must pass HTTP status check first
    if not (200 <= evidence.response_status < 300):
        return False

    pattern = self.patterns.get(endpoint_key)
    if pattern is None:
        # No learned pattern -- fall back to status-code-only (existing behavior)
        return True

    # Check explicit status field
    if pattern.status_field:
        body_json = self._parse_json(evidence.response_body)
        if body_json and pattern.status_field in body_json:
            value = str(body_json[pattern.status_field]).lower()
            if value in pattern.failure_values:
                return False
            if value in pattern.success_values:
                return True

    # Check error indicator field
    # ... (additional checks in priority order)

    return True  # Default: trust HTTP status code
```

### Pattern 3: Runner Integration Point
**What:** The learner runs after OAuth init and before scenario execution, within `PentestRunner.run()`.
**When to use:** Every scan.

```python
# In PentestRunner.run():
def run(self, scenario_ids=None):
    if not self.endpoints:
        self.parse_input()
    self.init_oauth()
    self.init_http()

    # NEW: Learn response patterns before running scenarios
    self.response_learner = ResponsePatternLearner(
        http_client=self.http,
        endpoints=self.endpoints,
        oauth_handler=self.oauth_a,
    )
    self.response_learner.learn()

    # Pass learner to each scenario
    for sid in selected:
        scenario = scenario_class()
        scenario.setup(
            endpoints=self.endpoints,
            oauth_handler=self.oauth_a,
            http_client=self.http,
            config=self.config,
            oauth_handler_b=self.oauth_b,
            response_learner=self.response_learner,  # NEW parameter
        )
```

### Anti-Patterns to Avoid
- **Global pattern, not per-endpoint:** Different endpoints on the same API can use different response formats. Always key patterns to the endpoint.
- **Machine learning / statistical classification:** The problem is deterministic -- APIs have explicit status fields. Don't over-engineer with ML when string matching suffices.
- **Blocking on non-JSON responses:** Not all responses are JSON. The learner must gracefully handle HTML, plain text, and empty bodies. Non-JSON responses should fall through to HTTP status code checking.
- **Modifying the HTTP client:** The learning logic should not touch `PentestHttpClient`. It uses the existing `request()` method and analyzes the `Evidence` objects returned.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing | Custom parser | `json.loads()` with try/except | Edge cases in JSON parsing are well-handled by stdlib |
| Response body extraction | Response object unpacking | `Evidence.response_body` | Already captured by the HTTP client |
| Endpoint keying | Custom URL normalization | `f"{method}:{url}"` | Already used in `BaseScenario.capture_baseline()` |
| Logging infrastructure | Custom output system | Python `logging` module | Already used throughout codebase |

**Key insight:** The entire learning system is string/JSON analysis on data already captured by the existing HTTP client. No new I/O, no new libraries, no new abstractions beyond a single new class.

## Common Pitfalls

### Pitfall 1: Learning from the Wrong Response
**What goes wrong:** The learner sends a request that triggers a different code path than what the scenario will test (e.g., sending GET to a POST-only endpoint, sending with wrong Content-Type).
**Why it happens:** The learning probe doesn't match the actual request shape the scenarios will use.
**How to avoid:** Use the same method, URL, headers, and body from the parsed endpoint spec for the "valid" probe. Use the endpoint's actual parameters, not generic ones.
**Warning signs:** Learned patterns don't match what scenarios see at runtime.

### Pitfall 2: Auth-Required Endpoints Without Token
**What goes wrong:** Some endpoints require auth. Without a valid token, the "success" probe returns an error, and the learner has no baseline for what success looks like.
**Why it happens:** OAuth handler not initialized, or token acquisition fails.
**How to avoid:** Check if the endpoint has security schemes. If token acquisition fails, skip learning for that endpoint and fall back to HTTP-status-only checking (existing behavior).
**Warning signs:** All patterns for auth-required endpoints show "no pattern learned."

### Pitfall 3: State-Dependent Endpoints
**What goes wrong:** POST /books/v1 succeeds the first time (book created) but returns `{"status": "fail", "message": "Book Already exists!"}` on the second call. If the learner probes before scenarios and the scenario probes again, the response differs.
**Why it happens:** The learning probe changes server state (creates resources, etc.).
**How to avoid:** For the learning pass, prefer GET endpoints for pattern learning. For POST/PUT/DELETE, learn from the "failure" probe primarily (send without auth to see the error format), and infer the success format from the API's general pattern.
**Warning signs:** POST/PUT endpoints show inconsistent patterns between learning and testing.

### Pitfall 4: Treating "HTTP 200 + Success Body" as Always Correct
**What goes wrong:** An endpoint returns HTTP 200 for everything (both success and failure) and the body analysis doesn't detect the failure because the status field uses a non-standard name.
**Why it happens:** Not all APIs use `"status"` as the field name. Some use `"success"`, `"ok"`, `"code"`, `"result"`, etc.
**How to avoid:** The learner should check a broad set of common status field names during analysis: `status`, `success`, `ok`, `error`, `code`, `result`, `errorCode`, `error_code`.
**Warning signs:** False positives persist for a particular API despite learning.

### Pitfall 5: Breaking Existing True Positives
**What goes wrong:** The new `is_real_success()` incorrectly suppresses a finding that was actually a real vulnerability (true positive becomes false negative).
**Why it happens:** Pattern matching is too aggressive -- e.g., any response containing the word "error" is treated as failure.
**How to avoid:** Only suppress findings when there is HIGH confidence the response indicates application-level failure. When in doubt, do NOT suppress. A false positive is annoying; a false negative is dangerous.
**Warning signs:** Previously-detected real vulnerabilities disappear from reports.

### Pitfall 6: Extra HTTP Requests Slowing Scan
**What goes wrong:** The learning pass doubles the number of HTTP requests, making scans noticeably slower.
**Why it happens:** Probing every endpoint twice (once with auth, once without).
**How to avoid:** Cache baselines (the existing `BaseScenario._baselines` dict does this). For the learning pass, make at most 2 requests per unique endpoint (valid + invalid). Share learned baselines with scenarios to avoid re-probing.
**Warning signs:** Scan time doubles or more.

## Code Examples

### VAmPI's Actual Response Pattern (Verified from OpenAPI spec and source code)

The VAmPI API uses a consistent pattern across all endpoints:

**Success response (HTTP 200):**
```json
{"status": "success", "message": "Successfully logged in.", "auth_token": "eyJ..."}
```

**Failure response (HTTP 200 -- this is the false positive source):**
```json
{"status": "fail", "message": "Password is not correct for the given username."}
```

**Failure response (HTTP 401):**
```json
{"status": "fail", "message": "Invalid token. Please log in again."}
```

The key field is `"status"` with values `"success"` or `"fail"`. The OpenAPI spec explicitly documents this as an enum: `{"enum": ["success", "fail"]}`.

### Current False Positive Code Path (S06 as example)

```python
# s06_privileged_access.py line 80 -- current code
if self.is_success_status(evidence.response_status):
    # This triggers for HTTP 200 + {"status": "fail"} -- FALSE POSITIVE
    accessible += 1
    self.log_finding(...)
```

VAmPI returns HTTP 200 with `{"status": "fail", "message": "Only Admins may delete users!"}` when a non-admin tries admin actions. The current code sees HTTP 200 and logs a finding.

### Where the Fix Goes (in scenarios)

```python
# AFTER: s06_privileged_access.py -- uses learned patterns
if self.is_real_success(evidence):
    # This correctly identifies HTTP 200 + {"status": "fail"} as NOT a success
    accessible += 1
    self.log_finding(...)
```

### Common Status Field Patterns Across APIs

From VAmPI spec analysis and web research, these are the most common status indicator patterns:

```python
# Status field names to check (ordered by frequency)
STATUS_FIELD_CANDIDATES = [
    "status",       # VAmPI, many Flask APIs
    "success",      # {"success": true/false}
    "ok",           # {"ok": true/false}
    "error",        # {"error": "message"} (present = failure)
    "code",         # {"code": 0} (0 = success, non-0 = failure)
    "result",       # {"result": "success"/"error"}
    "errorCode",    # {"errorCode": 0} or {"errorCode": "AUTH_FAILED"}
    "error_code",   # snake_case variant
]

# Failure value indicators (when found in status fields)
FAILURE_INDICATORS = {
    "fail", "failed", "failure",
    "error", "err",
    "false",  # boolean as string
    "denied", "unauthorized", "forbidden",
    "invalid",
}

# Success value indicators
SUCCESS_INDICATORS = {
    "success", "successful", "ok", "okay",
    "true",  # boolean as string
    "completed", "done",
}
```

### Error Phrase Detection for Non-Structured Responses

```python
# Common application-level failure phrases in response bodies
ERROR_PHRASES = [
    "not authorized",
    "permission denied",
    "access denied",
    "forbidden",
    "not allowed",
    "invalid token",
    "token expired",
    "authentication required",
    "login required",
    "insufficient privileges",
    "only admins",
    "admin only",
    "not found",
    "does not exist",
    "already exists",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTP status code only | Status code + body analysis | Industry standard since ~2020 | Eliminates largest class of API FPs |
| Manual false positive triage | Automated pattern learning | DAST tools adopted ~2022-2024 | Reduces human review time |
| Global API-wide patterns | Per-endpoint pattern learning | Current best practice | Handles inconsistent API designs |
| Static signature matching | Proof-based scanning (Invicti et al.) | 2023+ | Confirms exploitability, not just presence |

**Deprecated/outdated:**
- HTTP-status-only success checks: The single largest source of false positives in API security testing. All modern DAST tools check response bodies.

## Specific Codebase Findings

### Exact False Positive Locations

From code analysis, these are the specific `is_success_status()` calls that produce the 10 VAmPI false positives:

**S06 (Privileged Access) -- 4 FPs estimated:**
- `_test_admin_endpoint_access()` line 80: `if self.is_success_status(evidence.response_status)`
- `_test_horizontal_privilege_escalation()` line 139: `if self.is_success_status(evidence.response_status)`
- `_test_privilege_param_escalation()` line 201: `if self.is_success_status(evidence.response_status)`
- `_test_service_endpoint_access()` line 266: `if self.is_success_status(evidence.response_status)`

**S09 (Business Flow) -- 3-4 FPs estimated:**
- `_test_mass_creation()` line 80: `if self.is_success_status(evidence.response_status)`
- `_test_lifecycle_abuse()` line 138: `if self.is_success_status(evidence.response_status)`
- `_test_duplicate_creation()` line 188: `if self.is_success_status(ev1.response_status) and self.is_success_status(ev2.response_status)`
- `_test_business_logic()` line 256: `if self.is_success_status(evidence.response_status)`
- `_test_workflow_bypass()` line 309: `if self.is_success_status(evidence.response_status)`

**S13 (Unsafe Consumption) -- 2-3 FPs estimated:**
- `_test_content_type_mismatch()` line 75: `if self.is_success_status(evidence.response_status)`
- `_test_null_special()` line 340: `if self.is_success_status(evidence.response_status)`

### Existing Infrastructure to Leverage

1. **`BaseScenario.capture_baseline()`** (line 95-110): Already sends a "normal" request per endpoint and caches the result. The learner can reuse this mechanism.

2. **`BaseScenario._baselines`** dict: Already keys by `f"{endpoint.method}:{endpoint.url}"`. The pattern learner should use the same keying convention.

3. **`Evidence` dataclass**: Already captures `response_body` as a string and `response_status` as an int. No changes needed.

4. **`PentestRunner.run()` flow**: `parse_input() -> init_oauth() -> init_http() -> [scenarios]`. The learner slots in between `init_http()` and scenario execution.

5. **Existing logging**: All scenarios use `logging.getLogger(__name__)`. The learner should do the same.

### BaseScenario.setup() Signature

Current:
```python
def setup(self, endpoints, oauth_handler, http_client, config, oauth_handler_b=None):
```

Must change to accept `response_learner` parameter. The `is_real_success()` method should be added to BaseScenario so all 13 scenarios can use it, even though only S06/S09/S13 are the immediate targets.

## Open Questions

1. **How many endpoints warrant probing in the learning pass?**
   - What we know: VAmPI has ~12 endpoints. The learning pass should probe all of them.
   - What's unclear: For APIs with 500+ endpoints, probing all might be slow.
   - Recommendation: Probe all endpoints in Phase 2. Phase 5 (API Discovery) can add sampling/optimization for large APIs. Per CONTEXT.md, the user decided Phase 2 is a modular pre-step that Phase 5 absorbs later.

2. **Should is_real_success() replace is_success_status() globally or only in affected scenarios?**
   - What we know: S06, S09, S13 are the immediate targets with confirmed false positives.
   - What's unclear: Other scenarios (S03 IDOR, S07 Access Controls) also use `is_success_status()` and could benefit.
   - Recommendation: Add `is_real_success()` to BaseScenario and update ALL scenarios that use `is_success_status()` for attack validation. This prevents future false positives as new APIs are tested. Keep `is_success_status()` available for cases where HTTP-status-only checking is intentionally desired.

3. **How to handle the "valid probe" for state-mutating endpoints?**
   - What we know: POST/PUT/DELETE change server state. Probing them creates side effects.
   - What's unclear: Whether VAmPI specifically has POST endpoints that return different patterns after state changes.
   - Recommendation: For the learning pass, rely primarily on the "invalid probe" (no auth) to learn the failure format. For the success format, send the valid request only if the endpoint is GET, or infer from other endpoints on the same API that use the same response pattern.

## Sources

### Primary (HIGH confidence)
- `/home/abdulr7man/rb/vampi_openapi.json` -- VAmPI OpenAPI spec with explicit `{"enum": ["success", "fail"]}` in response schemas
- `/home/abdulr7man/rb/api_pentest/scenarios/s06_privileged_access.py` -- Exact false positive code path
- `/home/abdulr7man/rb/api_pentest/scenarios/s09_business_flow.py` -- Exact false positive code path
- `/home/abdulr7man/rb/api_pentest/scenarios/s13_unsafe_consumption.py` -- Exact false positive code path
- `/home/abdulr7man/rb/api_pentest/scenarios/base_scenario.py` -- `is_success_status()` and `capture_baseline()` implementations
- `/home/abdulr7man/rb/api_pentest/runner.py` -- Scan flow orchestration
- VAmPI source (GitHub erev0s/VAmPI, users.py, books.py) -- Confirmed HTTP 200 + `{"status": "fail"}` pattern

### Secondary (MEDIUM confidence)
- Invicti DAST false positive reduction: https://www.invicti.com/blog/web-security/reduce-dast-false-positives -- Proof-based scanning approach
- PortSwigger false positive best practices: https://portswigger.net/burp/documentation/dast/user-guide/working-with-scans/false-positives-best-practice -- Industry practices
- REST API error handling conventions: https://www.baeldung.com/rest-api-error-handling-best-practices -- Common response patterns
- RFC 7807/9457 Problem Details standard -- Emerging standard for error response format

### Tertiary (LOW confidence)
- Wallarm ML-based false positive reduction: https://lab.wallarm.com/reducing-false-positives-api-security-advanced-techniques-machine-learning/ -- ML approach (not applicable for our deterministic problem)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries needed, pure Python stdlib
- Architecture: HIGH -- Code paths fully traced, insertion points identified
- Pitfalls: HIGH -- Based on actual codebase analysis, not theoretical
- VAmPI pattern: HIGH -- Verified from OpenAPI spec AND VAmPI source code
- Generic API patterns: MEDIUM -- Based on web research of common conventions

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable -- no external dependencies to change)
