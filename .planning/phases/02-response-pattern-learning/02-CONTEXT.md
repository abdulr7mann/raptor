# Phase 2: Response Pattern Learning - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Teach the toolkit to learn how each API communicates success vs failure, so HTTP 200 + fail body is correctly identified as a failed test -- not a successful attack. This eliminates the 10 false positives from S06, S09, and S13 that currently result from checking HTTP status code alone.

Learning happens before security tests run. Test validation uses both status code and body structure.

</domain>

<decisions>
## Implementation Decisions

### Scan workflow integration
- Learning is an automatic pre-pass integrated into the normal scan flow
- No separate command or explicit step required from the user
- The toolkit probes endpoints and learns patterns before running security tests
- Designed as a modular pre-step so Phase 5 (API Discovery & Profiling) can absorb it into the broader profiling pipeline later

### Finding disposition
- Findings identified as false positives via learned patterns are suppressed entirely -- they do not appear in the report
- The goal is elimination, not annotation
- Auditability comes through learning visibility, not through cluttering the report with annotated non-findings

### Learning visibility
- Normal output: brief summary line (e.g., "Analyzed N endpoints, identified success/failure patterns")
- Verbose mode (-v/--verbose): shows the actual patterns discovered per endpoint
- No persistence to file in Phase 2 -- Phase 5 will add API profile persistence to JSON

### User control
- Fully automatic with no user-configurable knobs for Phase 2
- If pattern learning produces incorrect results, that is an algorithm bug to fix
- Phase 5 (API profile persistence) is the right place for user-editable patterns

### Claude's Discretion
- Pattern detection algorithm (what signals to analyze in response bodies)
- How many baseline requests per endpoint
- Internal data structures for storing learned patterns
- How patterns are passed to test validation logic

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. The user's core value is accuracy (findings must be real vulnerabilities, not false positives), which directly aligns with this phase's goal of eliminating HTTP 200 + fail body false positives.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-response-pattern-learning*
*Context gathered: 2026-02-04*
