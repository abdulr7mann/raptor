---
phase: 01-evidence-report-quality
plan: 01
subsystem: reporting
tags: [log_finding, evidence, endpoint, per-endpoint-findings, scenarios]

# Dependency graph
requires: []
provides:
  - "Per-endpoint findings with endpoint= and evidence= in S01, S02, S05, S11"
  - "No aggregate findings remain across these 4 scenarios"
  - "Pattern: collect (ep, evidence) pairs, emit after threshold check"
affects:
  - "01-02 (dedup plan needs per-endpoint findings as input)"
  - "Phase 2+ (all future scenario work follows per-endpoint pattern)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Collect-then-emit: gather (endpoint, evidence) pairs during test loop, emit per-endpoint findings after threshold/condition check"
    - "All log_finding() calls include endpoint=f\"{ep.method} {ep.url}\" and evidence=evidence"

key-files:
  created: []
  modified:
    - "api_pentest/scenarios/s01_token_reuse.py"
    - "api_pentest/scenarios/s02_rate_limiting.py"
    - "api_pentest/scenarios/s05_auth_hijacking.py"
    - "api_pentest/scenarios/s11_security_misconfig.py"

key-decisions:
  - "Collect-then-emit pattern for threshold-gated findings (S01 cross_endpoint_replay keeps ratio > 0.8 guard)"
  - "S11 security_headers restructured from header-first to endpoint-first loop to naturally produce per-endpoint findings"

patterns-established:
  - "Per-endpoint finding pattern: every log_finding() call must include endpoint=f\"{ep.method} {ep.url}\" and evidence=evidence"
  - "Collect-then-emit: accumulate (ep, evidence) pairs in first loop, emit findings after condition check"

# Metrics
duration: 5min
completed: 2026-02-04
---

# Phase 01 Plan 01: Decompose Aggregate Findings Summary

**Refactored 11 aggregate findings across S01, S02, S05, S11 into per-endpoint findings with endpoint= and evidence= on every log_finding() call**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-04T13:16:12Z
- **Completed:** 2026-02-04T13:21:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- All 19 log_finding() calls across 4 scenario files now include both endpoint= and evidence= parameters
- Eliminated all aggregate findings ("accepted by N/M endpoints" as single finding, "Multiple endpoints" string)
- Established collect-then-emit pattern for threshold-gated test methods (e.g., S01 ratio > 0.8 check preserved)
- Addressed requirements FIX-05, FIX-06, RPT-01, RPT-02

## Task Commits

Each task was committed atomically:

1. **Task 1: Decompose S01 and S02 aggregate findings** - `1830fa3` (feat)
2. **Task 2: Decompose S05 and S11 aggregate findings** - `73754cb` (feat)

## Files Created/Modified

- `api_pentest/scenarios/s01_token_reuse.py` - Per-endpoint findings for cross_endpoint_replay, old_token_after_refresh, cross_user_token_swap
- `api_pentest/scenarios/s02_rate_limiting.py` - Per-endpoint findings for burst_requests, response_time_degradation, rate_limit_headers; evidence= added to header_bypass
- `api_pentest/scenarios/s05_auth_hijacking.py` - Per-endpoint findings for expired_jwt, tampered_signature, alg_none, stripped_signature
- `api_pentest/scenarios/s11_security_misconfig.py` - Per-endpoint findings for security_headers_check; evidence= added to cookie_flags and cors_deep

## Decisions Made

- **Collect-then-emit pattern:** For methods with threshold checks (S01 cross_endpoint_replay ratio > 0.8, S01 old_token_after_refresh accepted > 0), collect (endpoint, evidence) pairs during the test loop and emit findings only after the threshold is met. This preserves the original threshold logic while producing per-endpoint output.
- **S11 restructure:** Changed _test_security_headers from a two-pass approach (loop endpoints then loop headers) to a single endpoint-first loop that checks all headers per endpoint. This naturally produces per-endpoint per-header findings.
- **S02 burst_requests:** Moved log_finding inside the per-endpoint loop (into the else branch where rate_limited == 0), eliminating the aggregate any_rate_limited check entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing evidence= in S02 _test_header_bypass**
- **Found during:** Task 1 (S02 refactoring)
- **Issue:** The _test_header_bypass method had endpoint= but was missing evidence= in its log_finding() call
- **Fix:** Added evidence=evidence parameter to the log_finding call
- **Files modified:** api_pentest/scenarios/s02_rate_limiting.py
- **Verification:** Multi-line grep confirms evidence= present
- **Committed in:** 1830fa3 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed missing evidence= in S11 _test_cookie_flags**
- **Found during:** Task 2 (S11 refactoring)
- **Issue:** The _test_cookie_flags method stored (url, issues, cookie) tuples but lost the evidence object and endpoint object, using bare url string for endpoint= and no evidence=
- **Fix:** Changed tuple to (ep, issues, cookie, evidence), updated log_finding to use endpoint=f"{ep.method} {ep.url}" and evidence=evidence
- **Files modified:** api_pentest/scenarios/s11_security_misconfig.py
- **Verification:** Multi-line grep confirms both parameters present
- **Committed in:** 73754cb (Task 2 commit)

**3. [Rule 1 - Bug] Fixed missing evidence= in S11 _test_cors_deep**
- **Found during:** Task 2 (S11 refactoring)
- **Issue:** The _test_cors_deep method stored (issue_type, url, detail) tuples but lost both ep and evidence objects, using bare url string for endpoint= and no evidence=
- **Fix:** Changed tuple to (issue_type, ep, evidence, detail), updated log_finding to use endpoint=f"{ep.method} {ep.url}" and evidence=evidence
- **Files modified:** api_pentest/scenarios/s11_security_misconfig.py
- **Verification:** Multi-line grep confirms both parameters present
- **Committed in:** 73754cb (Task 2 commit)

**4. [Rule 1 - Bug] Removed unused time import from S01 and S05**
- **Found during:** Tasks 1 and 2
- **Issue:** After removing the duration calculation variable in S01 and the time module was never used in S05, the `import time` statements were dead code
- **Fix:** Removed unused imports
- **Files modified:** api_pentest/scenarios/s01_token_reuse.py, api_pentest/scenarios/s05_auth_hijacking.py
- **Committed in:** 1830fa3, 73754cb

---

**Total deviations:** 4 auto-fixed (4 bugs)
**Impact on plan:** All auto-fixes necessary for correctness. Bugs 1-3 were pre-existing missing evidence= parameters in methods the plan said needed no changes. Bug 4 was dead code cleanup. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 19 log_finding() calls across S01, S02, S05, S11 now produce per-endpoint findings with evidence
- Ready for Plan 01-02 (dedup) which will collapse identical (title, endpoint) pairs from the increased finding count
- No blockers

---
*Phase: 01-evidence-report-quality*
*Completed: 2026-02-04*
