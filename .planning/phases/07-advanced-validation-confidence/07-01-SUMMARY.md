---
phase: 07-advanced-validation-confidence
plan: 01
subsystem: validation
tags: [confidence, validation, deepdiff, baseline, signals]

# Dependency graph
requires:
  - phase: 02-response-pattern-learning
    provides: ResponsePattern and baseline evidence infrastructure
provides:
  - ConfidenceLevel enum for finding classification
  - BaselineComparator for structural JSON diff with dynamic field exclusion
  - FindingValidator for multi-signal confidence determination
affects: [07-02, reporting, scenarios]

# Tech tracking
tech-stack:
  added: [deepdiff>=8.0.0]
  patterns: [multi-signal validation, categorical confidence thresholds]

key-files:
  created:
    - api_pentest/core/baseline_comparator.py
    - api_pentest/core/finding_validator.py
  modified:
    - api_pentest/core/models.py
    - requirements.txt

key-decisions:
  - "Four validation signals: body_diff, timing_anomaly, error_message, structure_change"
  - "Categorical threshold: 2+ signals CONFIRMED, 1 LIKELY, 0 UNCERTAIN"
  - "Dynamic value patterns: ISO timestamps, UUIDs, Unix timestamps (10-13 digits)"
  - "Timing anomaly threshold: 3x baseline response time"

patterns-established:
  - "Signal collection pattern: validators return enriched models, not new types"
  - "Baseline keying: {method}:{url} format for endpoint lookup"

# Metrics
duration: 2min
completed: 2026-02-05
---

# Phase 7 Plan 1: Validation Infrastructure Summary

**Multi-signal finding validation with ConfidenceLevel enum, BaselineComparator for structural diff, and FindingValidator for confidence classification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-05T07:47:54Z
- **Completed:** 2026-02-05T07:50:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ConfidenceLevel enum with CONFIRMED, LIKELY, UNCERTAIN values
- BaselineComparator using DeepDiff for structural JSON comparison with dynamic field exclusion
- FindingValidator collecting 4 validation signals and classifying confidence
- Backward-compatible Finding model extension with confidence fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ConfidenceLevel enum and extend Finding model** - `a25819a` (feat)
2. **Task 2: Build BaselineComparator and FindingValidator** - `d06b54a` (feat)

## Files Created/Modified
- `api_pentest/core/models.py` - ConfidenceLevel enum and extended Finding dataclass
- `api_pentest/core/baseline_comparator.py` - Structural JSON diff with dynamic field exclusion
- `api_pentest/core/finding_validator.py` - Multi-signal validation and confidence classification
- `requirements.txt` - Added deepdiff>=8.0.0

## Decisions Made
- **Four core validation signals:** body_diff, timing_anomaly, error_message, structure_change (status code, header diff, size delta excluded as too noisy)
- **Categorical confidence threshold:** 2+ signals = CONFIRMED, 1 = LIKELY, 0 = UNCERTAIN (no numeric weights)
- **Dynamic value patterns:** ISO timestamps, UUIDs (case insensitive), Unix timestamps 10-13 digits
- **Timing anomaly threshold:** Test response time > 3x baseline response time
- **Error indicators:** "error", "exception", "traceback", "stack trace", "syntax error", "internal server error", "fatal", "panic"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Validation infrastructure complete for integration into runner
- Next plan (07-02) will integrate validator into scanner runner
- Baseline capture mechanism needs connection to response pattern learning pass

---
*Phase: 07-advanced-validation-confidence*
*Completed: 2026-02-05*
