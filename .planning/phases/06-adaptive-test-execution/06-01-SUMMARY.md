---
phase: 06-adaptive-test-execution
plan: 01
subsystem: testing
tags: [dataclass, scoring, response-parsing, xml, json, defusedxml]

# Dependency graph
requires:
  - phase: 05-api-discovery-profiling
    provides: ApiProfile with architecture_type, prerequisite_results
provides:
  - ScenarioApplicability dataclass for declaring test requirements
  - ApplicabilityMode enum for matching criteria (ANY, ALL, EXCLUDE)
  - ResponseFormatHandler for safe JSON/XML/text parsing
  - RelevanceCalculator with weighted scoring (0.4/0.3/0.3)
  - RelevanceScore dataclass with score breakdown and skip_reason
affects: [06-02 scenario-annotations, 06-03 runner-integration]

# Tech tracking
tech-stack:
  added: [defusedxml (already present)]
  patterns: [weighted-scoring, applicability-declaration, safe-parsing]

key-files:
  created:
    - api_pentest/core/response_formats.py
    - api_pentest/core/relevance.py
  modified:
    - api_pentest/core/models.py

key-decisions:
  - "ApplicabilityMode enum with ANY/ALL/EXCLUDE for flexible matching"
  - "Weighted scoring: architecture 0.4, classification 0.3, prerequisite 0.3"
  - "Default threshold 0.3 allows tests with at least one dimension match"
  - "defusedxml for XXE-protected XML parsing"
  - "TYPE_CHECKING import to avoid circular imports with ArchitectureType"

patterns-established:
  - "ScenarioApplicability pattern: empty list means 'applies to all'"
  - "RelevanceScore pattern: skip_reason populated when below threshold"
  - "ResponseFormatHandler pattern: returns (data, format_type) tuple"

# Metrics
duration: 7min
completed: 2026-02-05
---

# Phase 6 Plan 1: Core Infrastructure Summary

**ScenarioApplicability declarations, ResponseFormatHandler with XXE-safe XML parsing, and RelevanceCalculator with 0.4/0.3/0.3 weighted scoring**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-05T05:18:13Z
- **Completed:** 2026-02-05T05:25:10Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- ScenarioApplicability dataclass for scenarios to declare architecture/classification/prerequisite requirements
- ResponseFormatHandler with safe JSON, XML (defusedxml), and text parsing with graceful fallback
- RelevanceCalculator producing weighted scores with architecture (0.4), classification (0.3), and prerequisite (0.3) factors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ScenarioApplicability and ApplicabilityMode** - `f17929f` (feat)
2. **Task 2: Create ResponseFormatHandler** - `4ac8907` (feat)
3. **Task 3: Create RelevanceCalculator** - `35b794b` (feat)

## Files Created/Modified
- `api_pentest/core/models.py` - Added ApplicabilityMode enum and ScenarioApplicability dataclass
- `api_pentest/core/response_formats.py` - New module with ResponseFormatHandler for JSON/XML/text parsing
- `api_pentest/core/relevance.py` - New module with RelevanceCalculator and RelevanceScore

## Decisions Made
- Used TYPE_CHECKING import for ArchitectureType to avoid circular imports at runtime
- ApplicabilityMode enum supports three modes: ANY (default), ALL, and EXCLUDE
- Weighted scoring formula: architecture (0.4) + classification (0.3) + prerequisite (0.3) = 1.0 max
- Default threshold of 0.3 means tests run if at least one dimension fully matches
- ResponseFormatHandler returns (parsed_data, format_type) tuple with format_type in {"json", "xml", "text", "empty"}

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Core infrastructure complete for adaptive test execution
- Ready for 06-02: Scenario annotations (scenarios will use ScenarioApplicability)
- Ready for 06-03: Runner integration (runner will use RelevanceCalculator)

---
*Phase: 06-adaptive-test-execution*
*Completed: 2026-02-05*
