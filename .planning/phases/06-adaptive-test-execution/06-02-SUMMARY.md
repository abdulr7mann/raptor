---
phase: 06-adaptive-test-execution
plan: 02
subsystem: testing
tags: [applicability, scenario-filtering, architecture-detection, profile-adaptation]

# Dependency graph
requires:
  - phase: 06-01
    provides: ScenarioApplicability model, ResponseFormatHandler, ApplicabilityMode enum
provides:
  - Default APPLICABILITY on BaseScenario
  - Explicit APPLICABILITY declarations on all 13 scenarios
  - Profile adaptation helpers (get_auth_header_from_profile, get_content_type_from_profile)
  - Response format helpers on BaseScenario
affects: [07-cli-integration, test-runner-filtering]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Class-level APPLICABILITY declarations for test filtering"
    - "Profile-based auth header and content-type adaptation"

key-files:
  created: []
  modified:
    - api_pentest/scenarios/base_scenario.py
    - api_pentest/scenarios/s01_token_reuse.py
    - api_pentest/scenarios/s02_rate_limiting.py
    - api_pentest/scenarios/s03_idor.py
    - api_pentest/scenarios/s04_injection.py
    - api_pentest/scenarios/s05_auth_hijacking.py
    - api_pentest/scenarios/s06_privileged_access.py
    - api_pentest/scenarios/s07_access_controls.py
    - api_pentest/scenarios/s08_api_responses.py
    - api_pentest/scenarios/s09_business_flow.py
    - api_pentest/scenarios/s10_ssrf.py
    - api_pentest/scenarios/s11_security_misconfig.py
    - api_pentest/scenarios/s12_inventory_management.py
    - api_pentest/scenarios/s13_unsafe_consumption.py

key-decisions:
  - "S03 IDOR excludes GraphQL (different pattern for object references)"
  - "S08 API Responses excludes auth-endpoint (returns credentials by design)"
  - "S02 Rate Limiting uses requires_prerequisites for filtering"
  - "api_profile.content_types_observed used for content-type adaptation (not content_types)"

patterns-established:
  - "APPLICABILITY = ScenarioApplicability() as class attribute on scenarios"
  - "api_profile parameter in setup() for profile-based adaptation"

# Metrics
duration: 4min
completed: 2026-02-05
---

# Phase 6 Plan 2: Scenario Applicability Declarations Summary

**APPLICABILITY declarations on BaseScenario and all 13 scenarios enabling architecture/classification-based test filtering**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-05
- **Completed:** 2026-02-05
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Added default `APPLICABILITY = ScenarioApplicability()` to BaseScenario
- Added explicit APPLICABILITY declarations to all 13 scenarios with architecture/classification constraints
- Added profile adaptation helpers: `get_auth_header_from_profile()` and `get_content_type_from_profile()`
- Added response format helpers: `parse_response_body()` and `parse_json_safe()`
- S03 IDOR correctly excludes GraphQL (different object reference pattern)
- S07 Access Controls correctly targets protected endpoints only

## Task Commits

Each task was committed atomically:

1. **Task 1: Add default APPLICABILITY and format handling to BaseScenario** - `9b0ecf0` (feat)
2. **Task 2: Add APPLICABILITY declarations to all 13 scenarios** - `31140b7` (feat)

## Files Created/Modified

- `api_pentest/scenarios/base_scenario.py` - Default APPLICABILITY, api_profile support, format helpers
- `api_pentest/scenarios/s01_token_reuse.py` - REST/GraphQL/Hybrid, protected
- `api_pentest/scenarios/s02_rate_limiting.py` - requires rate_limiting prerequisite
- `api_pentest/scenarios/s03_idor.py` - REST/Hybrid/Unknown (excludes GraphQL), protected
- `api_pentest/scenarios/s04_injection.py` - All architectures, any classification
- `api_pentest/scenarios/s05_auth_hijacking.py` - REST/GraphQL/Hybrid, protected/auth-endpoint
- `api_pentest/scenarios/s06_privileged_access.py` - All architectures, protected
- `api_pentest/scenarios/s07_access_controls.py` - Protected only
- `api_pentest/scenarios/s08_api_responses.py` - Public/protected (excludes auth-endpoint)
- `api_pentest/scenarios/s09_business_flow.py` - No restrictions
- `api_pentest/scenarios/s10_ssrf.py` - No restrictions
- `api_pentest/scenarios/s11_security_misconfig.py` - No restrictions
- `api_pentest/scenarios/s12_inventory_management.py` - No restrictions
- `api_pentest/scenarios/s13_unsafe_consumption.py` - No restrictions

## Decisions Made

- **S03 GraphQL exclusion**: IDOR tests use URL-based ID enumeration which doesn't apply to GraphQL's query-based pattern
- **S08 auth-endpoint exclusion**: Auth endpoints return tokens/credentials by design, so sensitive field detection would false-positive
- **api_profile.content_types_observed**: Used actual ApiProfile field name (not `content_types`) for content-type adaptation
- **Profile dict handling**: `get_auth_header_from_profile()` handles both dict (from JSON cache) and DetectedAuthScheme objects

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All scenarios now declare APPLICABILITY for architecture and classification filtering
- Runner can use RelevanceCalculator (from 06-01) with scenario APPLICABILITY to filter tests
- Ready for Phase 7 CLI integration to expose adaptive test execution to users

---
*Phase: 06-adaptive-test-execution*
*Completed: 2026-02-05*
