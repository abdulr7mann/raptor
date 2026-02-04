# Phase 1: Evidence & Report Quality - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix report output so every finding includes its endpoint, HTTP evidence, and is unique. Reports are clean, complete, and safe to view in a browser. No new scanning capabilities -- this phase fixes the output of existing tests.

Requirements: RPT-01, RPT-02, RPT-03, RPT-04, FIX-05, FIX-06

</domain>

<decisions>
## Implementation Decisions

### Evidence detail
- Full HTTP exchange per finding: complete request (method, URL, headers, body) + complete response (status line, headers, body)
- Never truncate response bodies -- always show full content regardless of size
- Only capture the triggering request/response (the one that confirmed the vulnerability), not all attempted payloads
- Include response timing (elapsed time) with each captured exchange

### Aggregate findings
- Split aggregate tests into one finding per endpoint -- no grouped/multi-endpoint findings
- Split findings share the same vulnerability title; the endpoint field distinguishes them
- Only generate findings for endpoints that actually showed the vulnerability -- do not list tested-but-clean endpoints

### Deduplication
- Keep the first occurrence, silently drop all duplicates (no count, no trace)
- Uniqueness key: title + endpoint + HTTP method (GET /users and POST /users are separate)
- Different parameters on the same endpoint are different findings (e.g., "SQLi via id" and "SQLi via name" on the same endpoint are NOT duplicates)
- Deduplication runs as a post-processing step on final results, not during scan execution

### Report output formats
- Three formats: JSON (machine-readable), HTML (human review), and colored terminal output
- HTML evidence displayed in syntax-highlighted blocks (headers, body, status line visually distinct)
- Findings ordered by severity: Critical > High > Medium > Low > Info
- Terminal output: show progress during scan (endpoints tested, findings count), full summary at end

### Claude's Discretion
- Whether to add a scenario/group ID linking per-endpoint findings that came from the same test run
- Syntax highlighting library/approach for HTML evidence blocks
- HTML report overall layout and styling
- Terminal progress format (progress bar, counters, spinner, etc.)
- XSS escaping strategy for HTML report (how to sanitize response body content)

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 01-evidence-report-quality*
*Context gathered: 2026-02-04*
