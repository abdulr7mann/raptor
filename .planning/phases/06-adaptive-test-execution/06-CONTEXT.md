# Phase 6: Adaptive Test Execution - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Use the API profile from Phase 5 to select only relevant tests for each endpoint and adjust test parameters to match the discovered API characteristics. Tests below relevance threshold are skipped with logged reasons.

</domain>

<decisions>
## Implementation Decisions

### Test Selection Criteria
- Architecture matching is strict — GraphQL tests only run on GraphQL APIs, REST tests only on REST. No crossover.
- Endpoint classification gates auth tests — S07 (missing auth) skips PUBLIC endpoints. BOLA/BFLA tests skip AUTH_ENDPOINT endpoints.
- Prerequisite detection gates bypass tests (already implemented in Phase 4) — rate limit bypass only if rate limiting detected, CORS bypass only if CORS headers present.
- Scenario applicability is explicit — each scenario declares what architectures/classifications it applies to. Runner filters before executing.

### Parameter Adaptation
- Auth from profile — tests use the auth scheme discovered in Phase 5 (Bearer, API key, cookie). No hardcoded `Authorization: Bearer` assumptions.
- Content-Type from profile — tests send payloads matching what the API expects. JSON API gets JSON payloads.
- Success validation from ResponsePatternLearner — Phase 2's `is_real_success()` is already wired. Tests use profile's learned patterns, not just status codes.
- Fallback to conservative defaults — if profile is incomplete, use common patterns (JSON, Bearer) but log the assumption.

### Format Handling
- Content-Type driven parsing — detect from response header, parse accordingly. JSON → json.loads, XML → xml parser, else treat as text.
- Graceful degradation — if parsing fails, treat as plain text. Log the mismatch but don't crash. The finding still captures the raw response.
- Evidence capture always works — even malformed responses get captured in findings. The evidence shows what the server returned.
- No schema validation during testing — we're probing for vulnerabilities, not validating API conformance. Accept whatever comes back.

### Relevance Scoring
- Score factors: architecture match (+0.4, mandatory for GraphQL-specific tests), classification match (+0.3), prerequisite present (+0.3).
- Default threshold: 0.3 — conservative for security testing. Better to run extra tests than miss a vulnerability.
- Below threshold behavior: skip and log reason (e.g., "Skipped: GraphQL test on REST API").
- User-configurable threshold — CLI flag `--relevance-threshold` for stricter (0.5) or exhaustive (0.0) scanning.

### Claude's Discretion
- Exact relevance score calculation formula
- Logging format for skipped tests
- How to structure scenario applicability declarations
- Which existing scenarios need architecture/classification annotations

</decisions>

<specifics>
## Specific Ideas

- Tests should feel intelligent — if a test doesn't make sense for an endpoint, skip it visibly rather than running and producing a nonsensical finding.
- The relevance threshold default (0.3) prioritizes security coverage over speed. A `--fast` mode could raise the threshold for quicker scans.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-adaptive-test-execution*
*Context gathered: 2026-02-05*
