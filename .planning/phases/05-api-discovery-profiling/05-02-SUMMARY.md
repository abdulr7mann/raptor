---
phase: 05-api-discovery-profiling
plan: 02
subsystem: api
tags: [api-profile, json-cache, sha256-hash, staleness-detection, discovery-orchestration]

# Dependency graph
requires:
  - phase: 05-api-discovery-profiling plan 01
    provides: AuthDetector, ArchitectureDetector, RequestBudget, enums, dataclasses
provides:
  - ApiProfile dataclass capturing all discovery fields
  - ApiProfiler orchestrator aggregating detection results
  - compute_content_hash() for staleness detection
  - save_profile/load_profile for JSON persistence
  - derive_target_name() for profile file naming
  - Runner integration with caching logic
affects: [06-adaptive-test-execution, 07-advanced-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Profile dataclass with JSON serialization via dataclasses.asdict
    - Content hash staleness detection (SHA-256 of spec + base_url)
    - Profile versioning for schema compatibility checks
    - Cache-first discovery pattern in runner

key-files:
  created: []
  modified:
    - api_pentest/core/api_discovery.py
    - api_pentest/runner.py

key-decisions:
  - "Profile version check rejects incompatible cached profiles (forces re-discovery)"
  - "default=str in json.dump handles Enum values and non-serializable types"
  - "Profile stored in profiles/{target_name}.profile.json with sanitized name"
  - "Discovery runs after prerequisite detection and before scenario loop"

patterns-established:
  - "ApiProfile aggregates all discovery results into single dataclass"
  - "Cache-first pattern: load_cached_profile() -> is_stale() -> discover() if needed"
  - "Target name derived from input_file stem or base_url hostname"

# Metrics
duration: 5min
completed: 2026-02-05
---

# Phase 5 Plan 02: ApiProfiler Summary

**ApiProfiler orchestrates AuthDetector + ArchitectureDetector, aggregates results into ApiProfile dataclass, persists as cached JSON with SHA-256 staleness detection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-05T04:10:00Z
- **Completed:** 2026-02-05T04:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ApiProfile dataclass captures all discovery fields (auth, architecture, classifications, response patterns, prerequisites, server metadata, gaps)
- compute_content_hash() produces deterministic SHA-256 for staleness detection (spec JSON + base_url)
- save_profile/load_profile round-trip JSON with profile_version compatibility check
- ApiProfiler.discover() calls AuthDetector + ArchitectureDetector and aggregates all results
- Runner.run() integrates discovery step after prerequisite detection with cache-first pattern
- Discovery summary printed to console (auth schemes, architecture, endpoint count)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build ApiProfile dataclass, ApiProfiler orchestrator, and profile persistence** - `ae4cac4` (feat)
2. **Task 2: Wire discovery into runner.py after prerequisite detection** - `2d30641` (feat)

## Files Created/Modified
- `api_pentest/core/api_discovery.py` - Added ApiProfile dataclass, ApiProfiler class, profile persistence functions (compute_content_hash, save_profile, load_profile, is_profile_stale, derive_target_name)
- `api_pentest/runner.py` - Added ApiProfiler import, self.api_profile attribute, discovery step in run() with caching logic

## Decisions Made
- PROFILE_VERSION=1 at top of file; incompatible versions trigger re-discovery rather than partial loading
- Auth schemes serialized as dicts (scheme_type.value for enums) for JSON compatibility
- Gaps list tracks discovery limitations (e.g., "budget exhausted", "no auth schemes detected")
- Profile saved to profiles/ directory (configurable via config["profiles_dir"])
- Target name sanitization: non-alphanumeric chars (except hyphen/dot) replaced with hyphen

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ApiProfile available on runner.api_profile for Phase 6 (adaptive test selection)
- Profile caching reduces redundant discovery on repeat scans
- All must-haves verified: content hash staleness, JSON round-trip, runner integration
- Phase 5 complete (both plans executed)

---
*Phase: 05-api-discovery-profiling*
*Completed: 2026-02-05*
