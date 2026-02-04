# Phase 3: Endpoint Classification - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Classify API endpoints as public vs protected and detect endpoint purpose, so the toolkit does not flag expected behavior as vulnerabilities. Specifically: eliminate 4 FPs from S07/S06 on public endpoints (/, /books/v1, /createdb) and 1 FP from S08 on login endpoint returning auth_token. Uses OpenAPI security definitions when available, falls back to path pattern heuristics.

</domain>

<decisions>
## Implementation Decisions

### Classification granularity
- Three categories: `public` (no auth required), `protected` (auth required), `auth-endpoint` (returns credentials by design, e.g. login)
- Not a full taxonomy — just enough to eliminate the targeted FPs
- `public` → skip auth-missing tests (S07, S06 auth checks)
- `auth-endpoint` → skip data-exposure tests for expected credential fields (S08)
- `protected` → run all applicable tests (default)

### Uncertainty handling
- Default to `protected` when classification confidence is low — run the test rather than skip it
- Only suppress tests when classification is confident (OpenAPI security definitions present, or strong path-pattern match)
- Rationale: better to have a false positive than miss a real vulnerability; only eliminate FPs where classification is clear

### Report visibility
- Skipped tests logged with classification reason: "endpoint classified as public — auth test skipped"
- Classification decisions visible in verbose/debug output, not cluttering the main report
- Enough transparency that a security professional can audit why something was skipped

### Manual overrides
- Config file supports marking specific endpoints as public/protected, overriding auto-detection
- Simple format in the existing YAML config (e.g., `endpoint_overrides:` section)
- Overrides take precedence over both OpenAPI definitions and heuristics

### Claude's Discretion
- OpenAPI security definition parsing implementation
- Path pattern heuristic rules and thresholds
- How classification data is stored/passed between components
- Integration points with existing scenario code

</decisions>

<specifics>
## Specific Ideas

No specific requirements — user deferred all implementation decisions to Claude. Standard approaches appropriate for each area.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-endpoint-classification*
*Context gathered: 2026-02-04*
