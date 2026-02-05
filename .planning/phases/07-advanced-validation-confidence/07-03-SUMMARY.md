---
phase: 07-advanced-validation-confidence
plan: 03
subsystem: reporting
tags: [confidence, html-report, filtering, badges, ui]

# Dependency graph
requires:
  - phase: 07-01
    provides: ConfidenceLevel enum and confidence fields on Finding model
provides:
  - Confidence badge rendering in HTML reports (CONFIRMED/LIKELY/UNCERTAIN)
  - Confidence-based filtering dropdown
  - Secondary sort by confidence after severity
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [confidence visualization, user-facing filtering]

key-files:
  created: []
  modified:
    - api_pentest/reporting/report_generator.py
    - api_pentest/reporting/templates/report.html

key-decisions:
  - "Badge colors: green CONFIRMED, yellow LIKELY, gray UNCERTAIN"
  - "Filter options: All, CONFIRMED only, CONFIRMED + LIKELY"
  - "Sort order: severity first, confidence second"

patterns-established:
  - "Data attributes on DOM elements for JS filtering"
  - "Confidence explanation displayed as italic text below description"

# Metrics
duration: 2min
completed: 2026-02-05
---

# Phase 7 Plan 3: Report Confidence Display Summary

**HTML report confidence badges with color-coded levels, explanation text, filter dropdown, and severity-then-confidence sorting**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-05T07:53:13Z
- **Completed:** 2026-02-05T07:55:08Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Confidence badges styled with appropriate colors (green CONFIRMED, yellow LIKELY, gray UNCERTAIN)
- Filter dropdown to show All, CONFIRMED only, or CONFIRMED + LIKELY findings
- Confidence explanation text displayed below description when present
- Findings sorted by severity first, confidence second
- Summary grid includes confidence counts

## Task Commits

Each task was committed atomically:

1. **Task 1: Update report_generator.py for confidence sorting and data** - `c6886da` (feat)
2. **Task 2: Add confidence badges, explanations, and filter to HTML template** - `2dd60a3` (feat)

## Files Created/Modified
- `api_pentest/reporting/report_generator.py` - ConfidenceLevel import, _CONFIDENCE_ORDER constant, dual-key sorting, confidence counts in summary
- `api_pentest/reporting/templates/report.html` - CSS for confidence badges, filter dropdown, confidence badges on finding cards, explanation text, JS filterFindings()

## Decisions Made
- **Badge colors:** CONFIRMED = green (#3fb950), LIKELY = yellow (#d29922), UNCERTAIN = gray (#8b949e) - matches GitHub dark theme
- **Filter options:** "All findings", "CONFIRMED only", "CONFIRMED + LIKELY" - allows focus on high-certainty findings
- **Sort order:** Severity first (Critical to Info), confidence second (CONFIRMED to UNCERTAIN) - maintains severity priority while grouping by confidence

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Report confidence display complete
- Phase 07 complete - all validation and confidence features implemented
- Ready for UAT testing with VAmPI target

---
*Phase: 07-advanced-validation-confidence*
*Completed: 2026-02-05*
