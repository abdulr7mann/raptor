# Phase 7: Advanced Validation & Confidence - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Findings carry confidence levels (CONFIRMED, LIKELY, UNCERTAIN) backed by multiple validation signals. Users can distinguish confirmed vulnerabilities from uncertain indicators. Includes baseline comparison to suppress findings identical to normal behavior.

</domain>

<decisions>
## Implementation Decisions

### Confidence Level Criteria
- CONFIRMED: 2+ independent validation signals detected
- LIKELY: 1 validation signal detected
- UNCERTAIN: 0 validation signals (heuristic-only finding)
- UNCERTAIN findings visible by default, clearly marked — user filters if wanted

### Validation Signals
- Core 4 signals count toward confidence:
  1. Response body diff (primary signal)
  2. Timing anomaly (significant deviation from baseline)
  3. Error message (unexpected error in response)
  4. Structure change (different JSON schema, missing/added fields)
- Status code, header diff, size delta NOT included — too noisy

### Baseline Comparison
- Structural match for suppression — same JSON keys, ignore dynamic values
- Dynamic fields detected by pattern: ISO timestamps, UUIDs, incrementing integers
- Baseline captured during existing response pattern learning pass (Phase 2 infrastructure)
- Findings identical to normal behavior: downgrade confidence, do not auto-suppress

### Signal Weighting
- No numeric weights — categorical threshold (2+ signals) is clearer
- Response body diff is primary; timing/error/structure are supporting signals
- Finding with only timing anomaly stays LIKELY, not auto-upgraded to CONFIRMED

### Report Presentation
- Confidence badge on each finding (green CONFIRMED, yellow LIKELY, gray UNCERTAIN)
- Explanation text below badge listing which signals were detected
- Filter dropdown to show/hide by confidence level
- Findings ordered by severity first, confidence second (security priority > certainty)

### Claude's Discretion
- Exact timing threshold for "anomaly" detection
- Dynamic field detection heuristics
- Baseline storage format and caching strategy
- Explanation text templates

</decisions>

<specifics>
## Specific Ideas

- User trusts Claude's expertise on implementation details — prioritize practical, well-tested approaches
- Keep confidence system simple enough to explain in the report

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-advanced-validation-confidence*
*Context gathered: 2026-02-05*
