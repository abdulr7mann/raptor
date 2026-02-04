# Phase 4: Prerequisite-Aware Testing - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Check whether a test's preconditions exist before running it. Eliminate false positives from testing bypass of nonexistent security controls. Primary target: 4 FPs from S02 rate limit bypass tests against VAmPI (which has no rate limiting). Secondary: CORS and CSP bypass tests when those controls are absent.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all implementation decisions. The following choices were made based on analysis of the codebase, phase goals, and the tool's core value of accuracy.

### Skip visibility
- Skipped tests appear in BOTH console output (real-time during scan) and the HTML report
- Report includes a separate "Not Applicable" / "Skipped" section — distinct from findings
- Each skip entry includes: test name, endpoint, reason (e.g., "no rate limiting detected"), and what control was checked for
- Console output logs skips at info level (visible by default, not hidden behind verbose flag)

### Detection scope
- Primary: Rate limiting detection — active probing (send burst of requests, check for 429/throttling). This addresses the 4 S02 FPs
- Secondary: CORS detection — passive (check for CORS headers in existing responses). CSP detection — passive (check for Content-Security-Policy header)
- Detection is modular: each control has its own detector, new controls can be added in future phases
- Only controls that have corresponding bypass tests in the toolkit need detectors

### Uncertain outcomes
- When a control is **definitively absent** → skip the test, log reason
- When a control is **definitively present** → run the test normally
- When detection is **uncertain/ambiguous** → run the test (conservative — missing a real vulnerability is worse than a false positive)
- No confidence scoring in this phase (that's Phase 7's domain)

### Rate limiting detection specifics
- Send a controlled burst of identical requests to gauge throttling behavior
- Absence of any 429 or throttling response = "definitively absent" = skip bypass tests
- Burst size should be reasonable (not DoS-like) — detect presence, not stress-test

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User deferred all decisions to Claude's judgment.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-prerequisite-aware-testing*
*Context gathered: 2026-02-04*
