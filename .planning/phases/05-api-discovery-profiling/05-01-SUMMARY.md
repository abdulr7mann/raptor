---
phase: 05-api-discovery-profiling
plan: 01
subsystem: api
tags: [openapi, swagger, graphql, auth-detection, introspection, http]

# Dependency graph
requires:
  - phase: 04-prerequisite-aware-testing
    provides: PrerequisiteDetector pattern and runner integration flow
provides:
  - AuthDetector for spec-based and probe-based auth scheme detection
  - ArchitectureDetector for REST/GraphQL/SOAP detection
  - RequestBudget for discovery request limiting
  - AuthSchemeType and ArchitectureType enums
  - DetectedAuthScheme dataclass
  - GRAPHQL_INTROSPECTION_QUERY constant
affects: [05-02, 06-adaptive-test-execution, 07-advanced-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-tier detection (spec-first, probe-fallback)
    - Shared request budget across detection subsystems
    - GraphQL POST as read-only exception to no-mutation rule

key-files:
  created:
    - api_pentest/core/api_discovery.py
  modified: []

key-decisions:
  - "Swagger 2.0 type:'basic' mapped directly without scheme field check"
  - "GraphQL introspection POST allowed as read-only exception to no-mutation rule"
  - "WWW-Authenticate parser uses simple regex matching for known schemes (Bearer, Basic, OAuth)"
  - "RequestBudget shared across all detection subsystems with 30-request default cap"

patterns-established:
  - "Spec-first extraction for auth schemes (securityDefinitions or components.securitySchemes)"
  - "Active probing fallback with safe methods only (GET, HEAD, OPTIONS)"
  - "GraphQL introspection with modern locations field (not legacy onOperation/onFragment/onField)"

# Metrics
duration: 4min
completed: 2026-02-05
---

# Phase 5 Plan 01: Detection Engine Summary

**AuthDetector + ArchitectureDetector with spec extraction, active probing, GraphQL introspection, and shared request budget**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-05T04:03:39Z
- **Completed:** 2026-02-05T04:07:16Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments
- AuthDetector extracts auth schemes from both OpenAPI 3.x and Swagger 2.0 specs
- WWW-Authenticate header parsing identifies Bearer, Basic, and OAuth scheme names per RFC 7235
- ArchitectureDetector identifies REST from spec signals and probes GraphQL endpoints with introspection
- RequestBudget tracks request count across all detection subsystems and enforces cap
- GRAPHQL_INTROSPECTION_QUERY uses modern `locations` field (not legacy directive fields)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create enums, dataclasses, AuthDetector with spec extraction and active probing** - `6f7432d` (feat)
2. **Task 2: Build ArchitectureDetector with GraphQL introspection and request budget integration** - `a2184b4` (feat)

## Files Created/Modified
- `api_pentest/core/api_discovery.py` - Core detection module with AuthDetector, ArchitectureDetector, RequestBudget, enums, dataclasses

## Decisions Made
- Swagger 2.0 uses `type:"basic"` directly without `scheme` field -- mapped correctly to AuthSchemeType.BASIC
- GraphQL introspection POST is explicitly allowed as read-only exception to no-mutation rule (query reads schema metadata, never mutates)
- WWW-Authenticate parser kept simple -- regex matches known scheme keywords (Bearer, Basic, Digest, OAuth), extracts realm if present
- RequestBudget with 30-request default cap shared across AuthDetector and ArchitectureDetector

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- AuthDetector and ArchitectureDetector ready for Plan 02 (ApiProfiler aggregation)
- All classes follow codebase conventions: snake_case methods, PascalCase classes, dataclass pattern, logging via getLogger(__name__)
- Request budget pattern established for downstream use

---
*Phase: 05-api-discovery-profiling*
*Completed: 2026-02-05*
