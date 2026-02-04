---
phase: 04-prerequisite-aware-testing
verified: 2026-02-04T18:28:44Z
status: passed
score: 12/12 must-haves verified
---

# Phase 4: Prerequisite-Aware Testing Verification Report

**Phase Goal:** The toolkit checks whether a test's preconditions exist before running it, so it does not flag bypass of nonexistent controls

**Verified:** 2026-02-04T18:28:44Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Rate limit bypass tests (header_bypass_attempt) do not run when no rate limiting exists on target | VERIFIED | S02._test_header_bypass() checks rate_limiting prerequisite, calls add_skip_result() when ABSENT (lines 212-220) |
| 2 | Detection probes the target for rate limiting presence before bypass tests execute | VERIFIED | RateLimitDetector.detect() sends DETECTION_BURST_SIZE=15 burst requests, checks for 429 + rate limit headers (lines 62-116) |
| 3 | Skipped bypass tests are logged at info level with reason in console output | VERIFIED | BaseScenario.add_skip_result() logs at info with reason (lines 237-240), sets details="Precondition not met: {reason}" |
| 4 | Detection returns three-state result: PRESENT, ABSENT, or UNCERTAIN | VERIFIED | DetectionStatus enum has PRESENT/ABSENT/UNCERTAIN (lines 19-24), used by all detectors |
| 5 | When detection is UNCERTAIN, bypass tests still run (conservative) | VERIFIED | Only DetectionStatus.ABSENT triggers skip (S02:213, S07:207, S11:398), UNCERTAIN falls through |
| 6 | CORS bypass tests in S07 and S11 skip when no CORS headers are detected on the target | VERIFIED | S07._test_cors_misconfiguration() (lines 206-213) and S11._test_cors_deep() (lines 397-404) both gate on cors prerequisite |
| 7 | HTML report has a 'Not Applicable' section showing tests skipped due to unmet preconditions | VERIFIED | report.html has "Not Applicable" section (lines 87-103) with table of prerequisite skips |
| 8 | Summary card in report shows count of not-applicable tests | VERIFIED | report.html summary grid includes not_applicable card (line 58), report_generator computes count (lines 179-183) |
| 9 | Prerequisite skips are distinguishable from other skips in the report | VERIFIED | Filtered by "Precondition not met:" prefix convention (report_generator.py:145, 182) |
| 10 | Tests skipped for non-prerequisite reasons (no endpoints, no token) are NOT shown in the Not Applicable section | VERIFIED | Only skips with details.startswith("Precondition not met:") are included (lines 145, 182) |
| 11 | S02 burst_requests, response_time_degradation, rate_limit_header_check are NOT gated | VERIFIED | No get_prerequisite calls in these methods, only in _test_header_bypass() |
| 12 | S11._test_security_headers() is NOT gated (missing headers is the finding) | VERIFIED | S11 has exactly 1 get_prerequisite call (in _test_cors_deep only, line 397), _test_security_headers() has no gate |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api_pentest/core/prerequisite_detector.py` | DetectionStatus enum, PrerequisiteResult dataclass, RateLimitDetector, CORSDetector, CSPDetector, PrerequisiteChecker facade | VERIFIED | 264 lines, all components present and substantive |
| `api_pentest/scenarios/base_scenario.py` | get_prerequisite() and add_skip_result() helpers, prerequisite_results in setup() | VERIFIED | get_prerequisite() returns prerequisite_results.get(control_name) (lines 231-233), add_skip_result() logs and creates SKIP result with "Precondition not met:" prefix (lines 235-246), setup() accepts prerequisite_results parameter (line 51) and stores it (line 62) |
| `api_pentest/scenarios/s02_rate_limiting.py` | Prerequisite gate on _test_header_bypass() with "Precondition not met" | VERIFIED | Lines 212-220: checks rate_limiting prerequisite, calls add_skip_result() with reason when ABSENT |
| `api_pentest/scenarios/s07_access_controls.py` | CORS prerequisite gate on _test_cors_misconfiguration() | VERIFIED | Lines 206-213: checks cors prerequisite, calls add_skip_result() when ABSENT |
| `api_pentest/scenarios/s11_security_misconfig.py` | CORS prerequisite gate on _test_cors_deep(), NOT on _test_security_headers() | VERIFIED | Lines 397-404: cors gate on _test_cors_deep(). _test_security_headers() has no gate (correct - missing headers IS the finding) |
| `api_pentest/runner.py` | PrerequisiteChecker integration after classification, prerequisite_results passed to scenarios | VERIFIED | Lines 169-176: PrerequisiteChecker instantiated after classifier.classify_all(), check_all() called. Line 212: prerequisite_results passed to scenario.setup() |
| `api_pentest/reporting/report_generator.py` | Prerequisite skip filtering, not_applicable count, skipped_prerequisites template variable | VERIFIED | Lines 141-151: extracts prerequisite skips by "Precondition not met:" prefix. Lines 179-183: computes not_applicable count. Line 160: passes skipped_prerequisites to template |
| `api_pentest/reporting/templates/report.html` | Not Applicable summary card and section between Findings and Test Results | VERIFIED | Line 58: not_applicable summary card. Lines 87-103: "Not Applicable" section with table, positioned after Findings (line 86) and before Test Results (line 105) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| runner.py | prerequisite_detector.py | PrerequisiteChecker instantiation + check_all() | WIRED | Lines 170-176: PrerequisiteChecker imported (line 12), instantiated with http_client/endpoints/config/oauth_handler, check_all() called, results stored in self.prerequisite_results |
| runner.py | base_scenario.py | prerequisite_results passed to scenario.setup() | WIRED | Line 212: prerequisite_results=self.prerequisite_results in setup() call. Line 63: self.prerequisite_results declared |
| s02_rate_limiting.py | base_scenario.py | self.get_prerequisite('rate_limiting') in _test_header_bypass() | WIRED | Line 212: rate_limit_prereq = self.get_prerequisite("rate_limiting"). Lines 213-220: checks status, calls add_skip_result() |
| s07_access_controls.py | base_scenario.py | self.get_prerequisite('cors') in _test_cors_misconfiguration() | WIRED | Line 206: cors_prereq = self.get_prerequisite("cors"). Lines 207-213: checks status, calls add_skip_result() |
| s11_security_misconfig.py | base_scenario.py | self.get_prerequisite('cors') in _test_cors_deep() | WIRED | Line 397: cors_prereq = self.get_prerequisite("cors"). Lines 398-404: checks status, calls add_skip_result() |
| report_generator.py | report.html | skipped_prerequisites template variable | WIRED | Lines 141-151: prerequisite_skips list built. Line 160: skipped_prerequisites=prerequisite_skips passed to template.render(). Lines 88-103 in report.html: iterates over skipped_prerequisites |
| report_generator.py | models.py | TestResult.details "Precondition not met:" prefix filtering | WIRED | Lines 145, 182: details.startswith("Precondition not met:") filters prerequisite skips. BaseScenario.add_skip_result() (line 244) creates details with this prefix |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| VALID-04: Skip nonsensical tests (don't test rate limit bypass when no rate limiting exists) | SATISFIED | Rate limiting detection + S02 gating verified |
| FIX-04: Fix false positives from rate limit bypass tests when no rate limiting exists (4 findings) | SATISFIED | S02 header_bypass_attempt gated, only runs when rate_limiting is PRESENT or UNCERTAIN |

### Anti-Patterns Found

None detected. All files are substantive implementations with proper wiring.

### Human Verification Required

None. All verifications can be performed programmatically against the codebase.

### Gaps Summary

No gaps found. All must-haves verified.

---

## Detailed Verification Evidence

### 1. Three-State Detection (PRESENT/ABSENT/UNCERTAIN)

**File:** `api_pentest/core/prerequisite_detector.py`

```python
class DetectionStatus(Enum):
    """Three-state detection result."""
    
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNCERTAIN = "UNCERTAIN"
```

All three detectors (RateLimitDetector, CORSDetector, CSPDetector) return PrerequisiteResult with DetectionStatus:
- UNCERTAIN when no endpoints available for detection
- PRESENT when control detected (429 responses, CORS headers, CSP headers)
- ABSENT when control not found after probing

**Conservative behavior:** Only ABSENT triggers test skips. UNCERTAIN falls through, allowing tests to run.

### 2. Rate Limit Detection Sends Burst Requests

**File:** `api_pentest/core/prerequisite_detector.py` (lines 62-116)

RateLimitDetector:
- DETECTION_BURST_SIZE = 15 (class constant)
- detect() selects probe endpoint (prefers GET)
- Sends 15 identical requests via self.http.request()
- Counts 429 responses
- Checks for rate limit headers (ratelimit, rate-limit, x-rate, retry-after)
- Returns PRESENT if any 429 or rate headers found
- Returns ABSENT if none found

### 3. CORS Detection Checks Access-Control-Allow-Origin

**File:** `api_pentest/core/prerequisite_detector.py` (lines 141-183)

CORSDetector:
- Tests up to 5 endpoints
- Adds Origin: https://detect-cors.example.com header to requests
- Checks response headers for access-control-allow-origin (case-insensitive)
- Returns PRESENT if header found on any endpoint
- Returns ABSENT if no CORS headers found

### 4. CSP Detection Checks Content-Security-Policy

**File:** `api_pentest/core/prerequisite_detector.py` (lines 186-229)

CSPDetector:
- Tests up to 5 endpoints
- Checks response headers for content-security-policy (case-insensitive)
- Returns PRESENT/ABSENT based on header presence

### 5. S02 Gating Pattern

**File:** `api_pentest/scenarios/s02_rate_limiting.py` (lines 212-220)

```python
# Check if rate limiting exists before testing bypass
rate_limit_prereq = self.get_prerequisite("rate_limiting")
if rate_limit_prereq and rate_limit_prereq.status == DetectionStatus.ABSENT:
    self.add_skip_result(
        test_name="header_bypass_attempt",
        reason=rate_limit_prereq.reason,
        control="rate_limiting",
        endpoint_name=ep.full_name,
    )
    return
```

Only _test_header_bypass() is gated. The other three S02 tests (burst_requests, response_time_degradation, rate_limit_header_check) have no prerequisite checks - "no rate limiting detected" is their legitimate finding.

### 6. S07 and S11 CORS Gating

**S07:** `api_pentest/scenarios/s07_access_controls.py` (lines 206-213)
**S11:** `api_pentest/scenarios/s11_security_misconfig.py` (lines 397-404)

Both use identical pattern:
```python
cors_prereq = self.get_prerequisite("cors")
if cors_prereq and cors_prereq.status == DetectionStatus.ABSENT:
    self.add_skip_result(
        test_name="...",
        reason=cors_prereq.reason,
        control="cors",
    )
    return
```

S11._test_security_headers() deliberately NOT gated - that test reports missing headers as findings.

### 7. Skip Result Logging

**File:** `api_pentest/scenarios/base_scenario.py` (lines 235-246)

```python
def add_skip_result(self, test_name: str, reason: str, control: str, endpoint_name: str = ""):
    """Record a SKIP result when a prerequisite control is not present."""
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

Logs at info level with reason and control, creates TestResult with "Precondition not met:" prefix in details.

### 8. Runner Wiring

**File:** `api_pentest/runner.py` (lines 169-176, 212)

```python
# Detect security control prerequisites before running scenarios
prereq_checker = PrerequisiteChecker(
    http_client=self.http,
    endpoints=self.endpoints,
    config=self.config,
    oauth_handler=self.oauth_a,
)
self.prerequisite_results = prereq_checker.check_all()
```

Then in scenario setup:
```python
scenario.setup(
    endpoints=self.endpoints,
    oauth_handler=self.oauth_a,
    http_client=self.http,
    config=self.config,
    oauth_handler_b=self.oauth_b,
    response_learner=self.response_learner,
    prerequisite_results=self.prerequisite_results,
)
```

PrerequisiteChecker runs after endpoint classification (line 167) and before scenario loop (line 189).

### 9. HTML Report "Not Applicable" Section

**File:** `api_pentest/reporting/report_generator.py` (lines 141-151, 179-183)

Prerequisite skip extraction:
```python
prerequisite_skips = []
for r in results:
    if r.status == TestStatus.SKIP and r.details.startswith("Precondition not met:"):
        prerequisite_skips.append({
            "scenario_id": r.scenario_id,
            "test_name": r.test_name,
            "endpoint": r.endpoint_name,
            "reason": r.details.replace("Precondition not met: ", "", 1),
        })
```

Summary count:
```python
"not_applicable": sum(
    1 for r in results
    if r.status == TestStatus.SKIP
    and r.details.startswith("Precondition not met:")
),
```

**File:** `api_pentest/reporting/templates/report.html` (lines 58, 87-103)

Summary card:
```html
<div class="summary-card"><div class="number" style="color: #8b949e;">{{ summary.not_applicable }}</div><div class="label">Not Applicable</div></div>
```

Section:
```html
<h2>Not Applicable</h2>
{% if skipped_prerequisites %}
<p style="color: #8b949e;">The following tests were skipped because their preconditions were not met on the target:</p>
<table>
<tr><th>Scenario</th><th>Test</th><th>Endpoint</th><th>Reason</th></tr>
{% for skip in skipped_prerequisites %}
<tr>
  <td>{{ skip.scenario_id }}</td>
  <td>{{ skip.test_name }}</td>
  <td>{{ skip.endpoint }}</td>
  <td>{{ skip.reason }}</td>
</tr>
{% endfor %}
</table>
{% else %}
<p style="color: #3fb950;">All test preconditions were met.</p>
{% endif %}
```

Positioned between Findings section (ends line 85) and Test Results section (starts line 105).

---

_Verified: 2026-02-04T18:28:44Z_
_Verifier: Claude (gsd-verifier)_
