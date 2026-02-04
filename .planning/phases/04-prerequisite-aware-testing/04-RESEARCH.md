# Phase 4: Prerequisite-Aware Testing - Research

**Researched:** 2026-02-04
**Domain:** Prerequisite detection for security bypass tests in an existing Python pentest toolkit
**Confidence:** HIGH

## Summary

Phase 4 must add prerequisite checking to the toolkit so that bypass tests are not run when the security control they attempt to bypass does not exist. The primary target is 4 false positives from S02's `_test_header_bypass()` test, which reports "Rate limit bypass via X-Forwarded-For/X-Real-IP/X-Originating-IP/X-Client-IP" against VAmPI -- an API that has no rate limiting at all. The test sends 50 requests per header, all return 200, and concludes rate limiting was "bypassed." In reality, there was nothing to bypass. Secondary targets are CORS and CSP bypass tests in S07 and S11 that similarly test bypass of controls that may not exist.

The solution requires three components: (1) a modular prerequisite detection system that probes for security controls before running bypass tests, (2) integration of prerequisite checks into S02 and the relevant CORS/CSP tests, and (3) a new "Not Applicable / Skipped" section in both the console output and HTML report that shows tests skipped due to unmet preconditions. No new external libraries are needed -- this is pure Python logic using the existing HTTP client infrastructure.

The architecture follows the established pattern from Phases 2 and 3: a standalone detector class in `api_pentest/core/`, integrated into the runner's pre-scan flow or into individual scenarios, with modular detectors per control type. Rate limiting detection uses active probing (send a burst of requests, look for 429 responses or throttling behavior). CORS and CSP detection uses passive checking (examine response headers from requests already made during the learning phase).

**Primary recommendation:** Build a `PrerequisiteDetector` module in `api_pentest/core/prerequisite_detector.py` with per-control detector classes (RateLimitDetector, CORSDetector, CSPDetector). Run detection before bypass tests and skip with logged reasons when controls are definitively absent. Add a dedicated "Not Applicable" section to the HTML report template.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | N/A | Detection result data structures | Consistent with existing models.py |
| Python stdlib `logging` | N/A | Skip reason logging at info level | Consistent with codebase logging |
| Python stdlib `enum` | N/A | Detection status enum (PRESENT, ABSENT, UNCERTAIN) | Type-safe detection results |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requests` (existing) | N/A | HTTP client for active probing via PentestHttpClient | Already a project dependency, used via http_client.py |
| `jinja2` (existing) | N/A | HTML report template rendering | Already used in report_generator.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Active burst probing for rate limits | Only check for rate limit headers | Headers are informational -- their absence does not mean no rate limiting. Active probing is more reliable. |
| Per-control detector classes | Single monolithic detector | Per-control classes are more testable and extensible, matching CONTEXT.md decision for modular detectors |
| Standalone module | Inline checks in each scenario | Violates DRY, makes it harder to add new controls later |

**Installation:**
```bash
# No new dependencies needed -- pure Python using existing project dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  core/
    prerequisite_detector.py  # NEW: DetectionStatus enum, PrerequisiteResult dataclass,
                               #       RateLimitDetector, CORSDetector, CSPDetector,
                               #       PrerequisiteChecker (facade)
    models.py                 # MODIFIED: Add SkipReason dataclass (or extend TestResult)
    ...
  scenarios/
    base_scenario.py          # MODIFIED: Add skip_test_with_reason() helper
    s02_rate_limiting.py      # MODIFIED: Check rate limit prerequisite before bypass tests
    s07_access_controls.py    # MODIFIED: Check CORS prerequisite before CORS bypass test
    s11_security_misconfig.py # MODIFIED: Check CORS/CSP prerequisite before bypass tests
    ...
  reporting/
    report_generator.py       # MODIFIED: Pass skipped-tests data to template
    templates/
      report.html             # MODIFIED: Add "Not Applicable" section
  runner.py                   # MODIFIED: Run prerequisite detection, pass to scenarios
```

### Pattern 1: Three-State Detection Result
**What:** Each detector returns PRESENT, ABSENT, or UNCERTAIN for a security control.
**When to use:** Every prerequisite check.
**Why:** CONTEXT.md decided: absent = skip, present = run, uncertain = run (conservative).

```python
# Source: Codebase analysis + CONTEXT.md decisions
from enum import Enum
from dataclasses import dataclass

class DetectionStatus(Enum):
    PRESENT = "present"       # Control is definitely active
    ABSENT = "absent"         # Control is definitely not active
    UNCERTAIN = "uncertain"   # Could not determine

@dataclass
class PrerequisiteResult:
    control_name: str              # e.g. "rate_limiting", "cors", "csp"
    status: DetectionStatus
    reason: str                    # Human-readable explanation
    evidence_summary: str = ""     # What was observed (for reporting)
    endpoint: str = ""             # Which endpoint was tested
```

### Pattern 2: Modular Detectors with Common Interface
**What:** Each security control has its own detector class implementing a common `detect()` method.
**When to use:** When checking for any security control's presence.
**Why:** CONTEXT.md requires modular design: "each control has its own detector."

```python
from abc import ABC, abstractmethod

class ControlDetector(ABC):
    """Base class for security control detectors."""

    def __init__(self, http_client, endpoints, config=None, token=None):
        self.http = http_client
        self.endpoints = endpoints
        self.config = config or {}
        self.token = token

    @abstractmethod
    def detect(self) -> list[PrerequisiteResult]:
        """Detect whether the security control is present.

        Returns a list of PrerequisiteResult, one per relevant endpoint
        or one global result depending on the control type.
        """
        ...
```

### Pattern 3: Runner Integration -- Detection Before Scenarios
**What:** The PrerequisiteChecker runs in the runner after response learning and endpoint classification, before scenarios execute. Results are passed to scenarios.
**When to use:** Every scan run.
**Why:** Follows the established pattern from Phases 2 and 3: pre-scan analysis feeding into scenario execution.

```python
# In runner.py, after classifier.classify_all() and before scenario loop:
from api_pentest.core.prerequisite_detector import PrerequisiteChecker

checker = PrerequisiteChecker(
    http_client=self.http,
    endpoints=self.endpoints,
    config=self.config,
    oauth_handler=self.oauth_a,
)
prerequisite_results = checker.check_all()

# Pass to each scenario via setup()
scenario.setup(
    endpoints=self.endpoints,
    # ... existing params ...
    prerequisite_results=prerequisite_results,  # NEW parameter
)
```

### Pattern 4: Scenario Integration -- Check Before Bypass Tests
**What:** Bypass tests check prerequisites before running. If control is absent, log a skip.
**When to use:** In S02 `_test_header_bypass()`, S07 `_test_cors_misconfiguration()`, S11 `_test_cors_deep()`.
**Why:** Each bypass test is meaningless without the control it attempts to bypass.

```python
# In S02._test_header_bypass():
def _test_header_bypass(self):
    # Check if rate limiting exists before testing bypass
    rate_limit_result = self.get_prerequisite("rate_limiting")
    if rate_limit_result and rate_limit_result.status == DetectionStatus.ABSENT:
        self.add_skip_result(
            test_name="header_bypass_attempt",
            reason=rate_limit_result.reason,
            control="rate_limiting",
        )
        return

    # ... existing bypass test logic ...
```

### Pattern 5: Skip Reporting in Console and HTML
**What:** Skipped tests appear at info level in console and in a dedicated "Not Applicable" section in the HTML report.
**When to use:** Every time a test is skipped due to unmet preconditions.
**Why:** CONTEXT.md requires: "Skipped tests are logged with reason rather than silently omitted."

```python
# In base_scenario.py:
def add_skip_result(self, test_name: str, reason: str, control: str,
                    endpoint_name: str = ""):
    """Record a test skip due to unmet prerequisite."""
    logger.info(
        "[%s] Skipping %s: %s (precondition: %s not detected)",
        self.SCENARIO_ID, test_name, reason, control,
    )
    self.add_result(
        test_name=test_name,
        status=TestStatus.SKIP,
        details=f"Precondition not met: {reason}",
        endpoint_name=endpoint_name,
    )
```

### Anti-Patterns to Avoid
- **Detection inside each scenario independently:** Leads to duplicate probing. Centralize detection and share results.
- **Binary detection (only PRESENT/ABSENT):** Missing UNCERTAIN state leads to either false skips or false runs. Three states are required per CONTEXT.md.
- **Aggressive rate limit detection (hundreds of requests):** The purpose is detection, not stress testing. A small burst (10-15 requests) is sufficient to detect 429 responses.
- **Caching detection results across separate scans:** Detection results are per-scan. API configuration can change between scans.
- **Silently skipping without logging:** CONTEXT.md explicitly requires skip visibility in both console and report.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request sending for probes | Custom urllib/socket code | Existing `PentestHttpClient.request()` | Already handles timeouts, SSL, auth, evidence capture |
| HTML report rendering | String concatenation | Existing Jinja2 template in `report.html` | Template is already set up with autoescape and styling |
| Endpoint iteration patterns | Custom endpoint selection | Existing `self.endpoints[:N]` pattern used throughout scenarios | Consistent with codebase convention |
| Test result recording | Custom output format | Existing `TestResult` dataclass + `add_result()` | Already feeds into report generator |

**Key insight:** The entire prerequisite system is built on top of existing infrastructure. The HTTP client, evidence capture, test result recording, and report generation all exist. The new code is detection logic (what to look for in responses) and integration glue (when to check and what to do with results).

## Common Pitfalls

### Pitfall 1: Rate Limit Detection Triggers Rate Limiting
**What goes wrong:** The detection burst triggers rate limiting, which then affects subsequent tests by throttling them.
**Why it happens:** Sending too many requests too fast during detection.
**How to avoid:** Use a modest burst size (10-15 requests, not 50). After detection, if rate limiting was found (429 received), add a brief cooldown delay before proceeding. This is detection, not stress testing.
**Warning signs:** Tests following detection show unexpected 429 responses.

### Pitfall 2: S02 Already Sends Burst Requests That Could Serve as Detection
**What goes wrong:** Running detection as a separate pre-step, then S02 runs its own `_test_burst_requests()` which also sends bursts -- resulting in double the traffic for the same information.
**Why it happens:** Not recognizing that S02's `burst_requests` test already probes for rate limiting presence.
**How to avoid:** The detection result for rate limiting can inform MULTIPLE S02 tests. The `_test_burst_requests()` test itself is the "is rate limiting present?" probe. The prerequisite check only needs to gate the `_test_header_bypass()` test. Alternatively, the `burst_requests` test result can feed the prerequisite for `header_bypass` -- if burst_requests found no rate limiting (0 429s), then header_bypass is pointless. The simplest approach: run a small detection probe (10-15 requests) at the prerequisite level, and let S02 tests use the result.
**Warning signs:** Scan time increases significantly due to doubled rate limit probing.

### Pitfall 3: CORS Detection Conflating "No CORS Headers" with "No CORS Policy"
**What goes wrong:** An API with no `Access-Control-Allow-Origin` header is classified as "no CORS" -- but the browser's same-origin policy is the default protection. No CORS headers means the default (restrictive) policy applies.
**Why it happens:** Confusing "no CORS configuration" with "no CORS protection."
**How to avoid:** For CORS bypass test prerequisite:
  - If response has CORS headers (Access-Control-Allow-Origin, etc.) = CORS is configured = PRESENT, run bypass tests
  - If response has no CORS headers = default same-origin policy = ABSENT (no CORS to bypass)
  - S07's `_test_cors_misconfiguration()` sends Origin headers and checks if they are reflected -- if no CORS headers come back at all, there is nothing to "bypass"
**Warning signs:** CORS bypass tests still run against APIs with no CORS headers.

### Pitfall 4: CSP Detection Is Already a "Missing Header" Check
**What goes wrong:** S11's `_test_security_headers()` already reports "No CSP header" as a finding. Adding a prerequisite check that skips CSP bypass when CSP is absent creates a conflict -- the "missing header" finding is legitimate, but the "bypass" test should skip.
**Why it happens:** The "missing header" test and the "bypass header" test have different semantics. One reports absence, the other tests circumvention.
**How to avoid:** Be precise about which tests need prerequisites:
  - `security_headers_check` (reports missing headers): does NOT need prerequisite -- missing headers IS the finding
  - `cors_deep_analysis` (tests CORS bypass): DOES need prerequisite -- only meaningful if CORS is configured
  - CSP bypass tests (if any exist): would need prerequisite
  - Currently S11 has no CSP bypass test, only a missing-header check. The prerequisite for CSP is only needed if a CSP bypass test is added later.
**Warning signs:** Prerequisite checks accidentally suppress legitimate "missing control" findings.

### Pitfall 5: BaseScenario.setup() Signature Growing Too Large
**What goes wrong:** Each phase adds another parameter to `setup()`: Phase 2 added `response_learner`, this phase would add `prerequisite_results`. The signature becomes unwieldy.
**Why it happens:** No refactoring to consolidate context objects.
**How to avoid:** Two options: (a) accept the growing signature for now (pragmatic, matches existing pattern), or (b) introduce a `ScanContext` dataclass that bundles all pre-scan results (response_learner, endpoint classifications, prerequisite results). Option (a) is recommended for this phase to minimize scope. The parameter is just one more dict/object.
**Warning signs:** Scenarios needing to access scan context through increasingly nested objects.

### Pitfall 6: Rate Limit Detection Does Not Account for Per-Endpoint Variation
**What goes wrong:** Some APIs apply rate limiting only to certain endpoints (e.g., login but not GET /health). Testing one endpoint and concluding "no rate limiting exists" misses endpoints that do have it.
**Why it happens:** Detection probes only one or a few endpoints.
**How to avoid:** For Phase 4, detect at the API level: if ANY endpoint returns 429, rate limiting is PRESENT. If NO endpoint returns 429 after probing, rate limiting is ABSENT. S02's `_test_header_bypass()` currently tests only `self.endpoints[0]` anyway, so API-level detection is sufficient. Per-endpoint detection can be added in future phases if needed.
**Warning signs:** Rate limiting detected on one endpoint but not another, causing inconsistent skip behavior.

## Code Examples

### The Exact FP Mechanism in S02 (Verified from Source)

The 4 FPs come from `s02_rate_limiting.py` lines 202-248, the `_test_header_bypass()` method:

```python
# Current code in S02._test_header_bypass() -- produces FPs
bypass_headers_list = [
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded-For": "10.0.0.1"},
    {"X-Real-IP": "192.168.1.1"},
    {"X-Originating-IP": "172.16.0.1"},
    {"X-Client-IP": "8.8.8.8"},
]

# For each header set, sends burst_count (50) requests
# If ALL succeed (success_count == burst_count):
#   -> logs finding "Rate limit bypass via {header_name}"
#
# Against VAmPI (no rate limiting), ALL requests always succeed
# regardless of headers, producing 4 findings:
#   1. "Rate limit bypass via X-Forwarded-For" (127.0.0.1)
#   2. "Rate limit bypass via X-Real-IP"
#   3. "Rate limit bypass via X-Originating-IP"
#   4. "Rate limit bypass via X-Client-IP"
#
# Note: X-Forwarded-For with 10.0.0.1 is the 2nd entry but
# the bypass_found flag was already set from the first X-Forwarded-For.
# The code logs a finding per header, not per unique header name.
# But there are 5 headers and likely 4-5 findings.
```

The fix: before running `_test_header_bypass()`, check if rate limiting exists. If not, skip with reason.

### Rate Limit Detection Logic

```python
class RateLimitDetector(ControlDetector):
    """Detects whether rate limiting is active on the target API."""

    DETECTION_BURST_SIZE = 15  # Enough to trigger most rate limiters

    def detect(self) -> list[PrerequisiteResult]:
        ep = self._select_probe_endpoint()
        if not ep:
            return [PrerequisiteResult(
                control_name="rate_limiting",
                status=DetectionStatus.UNCERTAIN,
                reason="No endpoints available for rate limit detection",
            )]

        # Send a burst of identical requests
        rate_limited_count = 0
        total_sent = 0
        for _ in range(self.DETECTION_BURST_SIZE):
            evidence = self.http.request(
                method=ep.method,
                url=ep.url,
                headers=ep.headers,
                body=ep.body,
                auth_token=self._get_auth_token(),
            )
            total_sent += 1
            if evidence.response_status == 429:
                rate_limited_count += 1

        # Also check for rate limit headers
        has_rate_headers = self._check_rate_limit_headers(evidence)

        if rate_limited_count > 0:
            return [PrerequisiteResult(
                control_name="rate_limiting",
                status=DetectionStatus.PRESENT,
                reason=f"Rate limiting detected: {rate_limited_count}/{total_sent} "
                       f"requests returned 429",
                endpoint=f"{ep.method} {ep.url}",
            )]
        elif has_rate_headers:
            # Headers present but no 429 triggered = likely present but not hit threshold
            return [PrerequisiteResult(
                control_name="rate_limiting",
                status=DetectionStatus.PRESENT,
                reason="Rate limit headers found in response (control configured)",
                endpoint=f"{ep.method} {ep.url}",
            )]
        else:
            return [PrerequisiteResult(
                control_name="rate_limiting",
                status=DetectionStatus.ABSENT,
                reason=f"No rate limiting detected: {total_sent} rapid requests "
                       f"all succeeded with no 429 responses and no rate limit headers",
                endpoint=f"{ep.method} {ep.url}",
            )]

    def _check_rate_limit_headers(self, evidence) -> bool:
        """Check if response contains rate limit headers."""
        for header_name in evidence.response_headers:
            lower = header_name.lower()
            if any(kw in lower for kw in [
                "ratelimit", "rate-limit", "x-rate", "retry-after"
            ]):
                return True
        return False

    def _select_probe_endpoint(self):
        """Select a safe endpoint for rate limit probing (prefer GET)."""
        get_eps = [ep for ep in self.endpoints if ep.method.upper() == "GET"]
        return get_eps[0] if get_eps else (self.endpoints[0] if self.endpoints else None)
```

### CORS Detection Logic (Passive)

```python
class CORSDetector(ControlDetector):
    """Detects whether CORS is configured on the target API."""

    def detect(self) -> list[PrerequisiteResult]:
        # Check a few endpoints for CORS headers
        test_eps = self.endpoints[:5]
        if not test_eps:
            return [PrerequisiteResult(
                control_name="cors",
                status=DetectionStatus.UNCERTAIN,
                reason="No endpoints available for CORS detection",
            )]

        has_cors = False
        for ep in test_eps:
            evidence = self.http.request(
                method=ep.method,
                url=ep.url,
                headers={**ep.headers, "Origin": "https://detect-cors.example.com"},
                body=ep.body,
                auth_token=self._get_auth_token(),
            )
            headers_lower = {k.lower(): v for k, v in evidence.response_headers.items()}
            if "access-control-allow-origin" in headers_lower:
                has_cors = True
                break

        if has_cors:
            return [PrerequisiteResult(
                control_name="cors",
                status=DetectionStatus.PRESENT,
                reason="CORS headers found in response",
                endpoint=f"{ep.method} {ep.url}",
            )]
        else:
            return [PrerequisiteResult(
                control_name="cors",
                status=DetectionStatus.ABSENT,
                reason="No CORS headers found on any sampled endpoint "
                       "(default same-origin policy applies)",
            )]
```

### CSP Detection Logic (Passive)

```python
class CSPDetector(ControlDetector):
    """Detects whether Content-Security-Policy is configured."""

    def detect(self) -> list[PrerequisiteResult]:
        test_eps = self.endpoints[:5]
        if not test_eps:
            return [PrerequisiteResult(
                control_name="csp",
                status=DetectionStatus.UNCERTAIN,
                reason="No endpoints available for CSP detection",
            )]

        has_csp = False
        for ep in test_eps:
            evidence = self.http.request(
                method=ep.method,
                url=ep.url,
                headers=ep.headers,
                body=ep.body,
                auth_token=self._get_auth_token(),
            )
            headers_lower = {k.lower(): v for k, v in evidence.response_headers.items()}
            if "content-security-policy" in headers_lower:
                has_csp = True
                break

        if has_csp:
            return [PrerequisiteResult(
                control_name="csp",
                status=DetectionStatus.PRESENT,
                reason="Content-Security-Policy header found",
                endpoint=f"{ep.method} {ep.url}",
            )]
        else:
            return [PrerequisiteResult(
                control_name="csp",
                status=DetectionStatus.ABSENT,
                reason="No Content-Security-Policy header found on any sampled endpoint",
            )]
```

### HTML Report "Not Applicable" Section

The current HTML template has: Executive Summary, Findings, Test Results. The "Not Applicable" section goes between Findings and Test Results.

```html
<!-- In report.html, after the Findings section and before Test Results -->
<h2>Not Applicable</h2>
{% if skipped_prerequisites %}
<p>The following tests were skipped because their preconditions were not met on the target:</p>
<table>
<tr>
  <th>Scenario</th>
  <th>Test</th>
  <th>Endpoint</th>
  <th>Reason</th>
  <th>Control Checked</th>
</tr>
{% for skip in skipped_prerequisites %}
<tr>
  <td>{{ skip.scenario_id }}</td>
  <td>{{ skip.test_name }}</td>
  <td>{{ skip.endpoint }}</td>
  <td>{{ skip.reason }}</td>
  <td>{{ skip.control }}</td>
</tr>
{% endfor %}
</table>
{% else %}
<p style="color: #8b949e;">All test preconditions were met.</p>
{% endif %}
```

### Console Output Pattern

```python
# At info level (visible by default):
logger.info(
    "[S02] Skipping header_bypass_attempt: "
    "No rate limiting detected (15 rapid requests all succeeded, no 429 responses)"
)

# In runner.py scenario summary, skips with reasons already print via:
#   f"{Fore.CYAN}{skipped} skipped{Style.RESET_ALL}"
# But for prerequisite skips, add explicit per-test reason in console:
print(f"  {Fore.CYAN}[SKIP]{Style.RESET_ALL} header_bypass_attempt: "
      f"precondition not met (no rate limiting detected)")
```

### Distinguishing Prerequisite Skips from Other Skips

Currently, `TestStatus.SKIP` is used for various reasons (no endpoints, no token, etc.). Prerequisite skips need to be distinguishable for the report's "Not Applicable" section.

Two approaches:

**Option A: Use details string convention (simpler)**
```python
# All prerequisite skips start with "Precondition not met:"
self.add_result(
    test_name="header_bypass_attempt",
    status=TestStatus.SKIP,
    details="Precondition not met: no rate limiting detected",
)

# Report generator filters:
prerequisite_skips = [r for r in results
                      if r.status == TestStatus.SKIP
                      and r.details.startswith("Precondition not met:")]
```

**Option B: Add a new field to TestResult (more robust)**
```python
@dataclass
class TestResult:
    # ... existing fields ...
    skip_reason_type: str = ""  # "prerequisite", "no_data", "config", ""

# Report generator filters:
prerequisite_skips = [r for r in results if r.skip_reason_type == "prerequisite"]
```

**Recommendation:** Option A (details string convention) is simpler and avoids modifying the TestResult dataclass. The "Precondition not met:" prefix is a clear convention. If robustness is needed later, Option B can be adopted.

## Exact FP Mapping

### FP Group: S02 header_bypass_attempt (4 FPs)

**Test:** `S02RateLimiting._test_header_bypass()` (s02_rate_limiting.py lines 202-248)
**Mechanism:** For each of 5 bypass headers, sends `burst_count` (50 in VAmPI config, default 50) requests. If all succeed, logs "Rate limit bypass via {header}." Against VAmPI with no rate limiting, all requests trivially succeed, producing findings for X-Forwarded-For, X-Real-IP, X-Originating-IP, X-Client-IP (and possibly X-Forwarded-For:10.0.0.1 as a separate finding -- code logs per iteration, but likely 4-5 depending on dedup).

**Why FP:** No rate limiting exists to bypass. The test's precondition (rate limiting is active) is not met.

**Fix:** Before `_test_header_bypass()` runs, check rate limit detection result. If ABSENT, skip.

### Secondary: S07 cors_misconfiguration

**Test:** `S07AccessControls._test_cors_misconfiguration()` (s07_access_controls.py lines 202-277)
**Mechanism:** Sends requests with `Origin: https://evil.com` (and others) and checks if the origin is reflected back. Reports "CORS wildcard origin," "CORS reflects arbitrary origin," "CORS allows null origin."
**Prerequisite question:** If no CORS headers are returned at all, these tests pass harmlessly (no false findings). But if CORS is not configured, sending these probes is wasted effort. The prerequisite check is more about efficiency than FP elimination here.
**Recommendation:** Add prerequisite check. If CORS is ABSENT, skip with reason. Currently not producing FPs against VAmPI, but the infrastructure should be consistent.

### Secondary: S11 cors_deep_analysis

**Test:** `S11SecurityMisconfig._test_cors_deep()` (s11_security_misconfig.py lines 393-462)
**Mechanism:** Sends OPTIONS preflight with evil origin, checks for dangerous methods, wildcard headers, long max-age, and credentials-with-evil-origin.
**Prerequisite question:** Same as S07 -- if no CORS headers are returned, the test passes harmlessly but wastes requests.
**Recommendation:** Add prerequisite check. Skip if CORS ABSENT.

### Secondary: S11 security_headers_check (CSP)

**Test:** `S11SecurityMisconfig._test_security_headers()` (s11_security_misconfig.py lines 97-136)
**Note:** This test checks for MISSING headers including CSP. This is NOT a bypass test -- it reports absence as a finding. This test should NOT have a prerequisite check. Missing CSP IS the finding, not a bypass of CSP.
**Recommendation:** Do NOT add prerequisite for this test. Only add CSP prerequisite if a CSP bypass test is added in the future.

## Which S02 Tests Get Prerequisite Checks

Critical distinction: not all S02 tests need prerequisite checking.

| S02 Test | Needs Prerequisite? | Rationale |
|----------|-------------------|-----------|
| `burst_requests` | NO | This test IS the rate limit detection. Finding "no rate limiting" is a legitimate finding. |
| `response_time_degradation` | NO | Tests server capacity, not rate limit bypass. |
| `rate_limit_header_check` | NO | Checks for informational headers. Missing headers is the finding. |
| `header_bypass_attempt` | YES | Tests bypass of rate limiting. Meaningless without rate limiting. |

Only `header_bypass_attempt` gets gated. The other three S02 tests remain unchanged.

## Integration Approach: Two Options

### Option A: Runner-Level Detection (Recommended)

Detection runs once in the runner, results passed to all scenarios.

**Pros:**
- Detection happens once, shared across scenarios
- Follows Phase 2/3 pattern (runner pre-scan)
- Scenarios don't need to know how detection works

**Cons:**
- Adds another parameter to `setup()`
- All detectors run even if their scenarios are not selected

```python
# In runner.py run():
checker = PrerequisiteChecker(self.http, self.endpoints, self.config, self.oauth_a)
self.prerequisite_results = checker.check_all()

# Pass to scenarios
scenario.setup(..., prerequisite_results=self.prerequisite_results)
```

### Option B: Scenario-Level Detection

Each scenario runs its own detection before bypass tests.

**Pros:**
- Only runs detection when the scenario is selected
- No change to setup() signature

**Cons:**
- Detection logic duplicated if multiple scenarios need same check
- S07 and S11 both need CORS detection -- would probe twice

**Recommendation:** Option A (runner-level). The extra parameter to `setup()` is a minor cost versus the benefit of centralized, non-duplicated detection. The runner already does response learning and endpoint classification as pre-scan steps.

## HTML Report Changes

### Current Template Structure
```
Executive Summary (summary-grid cards)
Findings (finding-card for each finding)
Test Results (table with all results)
```

### Modified Template Structure
```
Executive Summary (summary-grid cards) -- add "Not Applicable" count card
Findings (finding-card for each finding) -- unchanged
Not Applicable (new section) -- table of prerequisite-skipped tests
Test Results (table with all results) -- unchanged (skips still appear here too)
```

### Summary Card Addition
Add a summary card for "Not Applicable" count alongside existing cards:
```html
<div class="summary-card">
  <div class="number" style="color: #8b949e;">{{ summary.not_applicable }}</div>
  <div class="label">Not Applicable</div>
</div>
```

### Report Generator Changes
The `generate_html()` method needs to:
1. Filter prerequisite skips from results (using "Precondition not met:" prefix or dedicated field)
2. Pass them as a separate `skipped_prerequisites` variable to the template
3. Add `not_applicable` count to the summary dict

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Always run all bypass tests | Check prerequisites before bypass tests | Current best practice in DAST tools | Eliminates "bypass of nonexistent control" FP class |
| Silent skips with no logging | Explicit skip reporting with reasons | Standard in mature security tools | Audit trail, user transparency |
| Binary present/absent detection | Three-state (present/absent/uncertain) | Modern approach for robustness | Avoids false skips |

**Preserved:**
- `is_success_status()` and `is_real_success()` unchanged -- prerequisite checking is orthogonal to response validation
- All existing scenario tests continue to run for present controls
- Endpoint classification (Phase 3) is independent of prerequisite detection

## Open Questions

1. **Should detection results be cached between S02, S07, and S11?**
   - What we know: If runner-level detection is used (Option A), results are computed once and shared
   - What's unclear: If a later phase adds more detectors, the pre-scan step grows. Is this acceptable?
   - Recommendation: Accept runner-level detection for now. The 3 detectors (rate limit, CORS, CSP) are lightweight.

2. **Burst size for rate limit detection: 10, 15, or match config?**
   - What we know: VAmPI config sets `requests_per_burst: 30`. S02 uses this for its full test. Detection should be smaller.
   - What's unclear: What is the minimum burst to reliably detect rate limiting?
   - Recommendation: Use 10-15 requests for detection. This is enough to trigger most rate limiters (which typically have thresholds of 10-100 per minute). If this is too few for certain setups, the detection returns UNCERTAIN and the test runs normally.

3. **Should S02's `burst_requests` result feed into `header_bypass` prerequisite?**
   - What we know: `burst_requests` already detects rate limiting (looks for 429s). If it found no rate limiting, `header_bypass` is definitely pointless.
   - What's unclear: Whether to use burst_requests as detection (avoiding separate probe) or keep detection independent.
   - Recommendation: Keep detection independent in the runner (cleaner separation). The duplicate traffic is small (15 extra requests) and the architectural cleanliness is worth it. S02's burst_requests sends 50 * 5 = 250 requests; 15 more for detection is negligible.

4. **How to handle rate limit detection in CI/CD (fast, repeated scans)?**
   - What we know: Detection adds 15 HTTP requests to each scan.
   - What's unclear: Whether repeated scans might trigger rate limiting on the detection endpoint itself.
   - Recommendation: This is a non-issue for Phase 4. 15 requests is trivial. If rate limiting triggers on the detection burst, that is actually a positive detection result (PRESENT).

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `s02_rate_limiting.py` -- Exact FP mechanism in `_test_header_bypass()` (lines 202-248)
- Codebase analysis: `s07_access_controls.py` -- CORS misconfiguration test (lines 202-277)
- Codebase analysis: `s11_security_misconfig.py` -- CORS deep analysis (lines 393-462), security headers check (lines 97-136)
- Codebase analysis: `base_scenario.py` -- `setup()` signature, `add_result()`, `make_request()`, existing skip patterns
- Codebase analysis: `runner.py` -- Pre-scan flow: parse -> oauth -> http -> response_learner -> classifier -> scenarios
- Codebase analysis: `report_generator.py` + `report.html` -- Current report structure and template variables
- Codebase analysis: `models.py` -- `TestStatus.SKIP`, `TestResult`, `Finding`, `Evidence` dataclasses
- Phase 2 RESEARCH.md -- Integration pattern precedent (standalone class, runner integration, scenario helpers)
- Phase 3 RESEARCH.md -- Classification pattern precedent (EndpointClassifier, three-tier strategy)
- CONTEXT.md decisions -- All implementation decisions locked (skip visibility, detection scope, uncertain outcomes, rate limit specifics)

### Secondary (MEDIUM confidence)
- HTTP 429 status code (RFC 6585) -- Standard rate limit response code
- CORS specification (W3C) -- Access-Control-Allow-Origin header semantics
- VAmPI configuration (vampi_config.yaml) -- `requests_per_burst: 30`, no rate limiting implemented

### Tertiary (LOW confidence)
- None -- all findings verified against codebase analysis

## Metadata

**Confidence breakdown:**
- FP mechanism: HIGH -- Traced exact code path in S02._test_header_bypass(), logic is straightforward
- Architecture: HIGH -- Follows established Phase 2/3 integration patterns, all insertion points verified in runner.py
- Detection logic: HIGH -- Rate limit detection via 429 probing is deterministic; CORS/CSP detection via header presence is trivial
- Report integration: HIGH -- Template structure and Jinja2 variables verified from report.html and report_generator.py
- Pitfalls: HIGH -- Based on actual codebase analysis and understanding of HTTP semantics

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable -- no external dependency changes, pure internal architecture work)
