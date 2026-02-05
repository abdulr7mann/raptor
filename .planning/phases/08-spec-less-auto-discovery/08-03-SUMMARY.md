---
phase: 08-spec-less-auto-discovery
plan: 03
subsystem: cli
tags: [cli, discovery, argparse, url-mode, endpoint-fuzzing]

# Dependency graph
requires:
  - phase: 08-01
    provides: SpecDiscoverer class for finding API specs at common paths
  - phase: 08-02
    provides: EndpointFuzzer class for discovering endpoints via fuzzing
provides:
  - --url CLI argument as alternative to --input
  - URL-only mode in PentestRunner with two-stage discovery pipeline
  - Progress feedback during discovery stages
affects: [end-to-end-testing, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-stage discovery (spec first, fuzzing fallback)
    - Temp file for spec parsing via existing InputDetector

key-files:
  created: []
  modified:
    - run_pentest.py
    - api_pentest/runner.py

key-decisions:
  - "Mutual exclusion for --input and --url (cannot use both)"
  - "URL stored as discovery_url in config to distinguish from base_url"
  - "Temp file approach for discovered spec parsing reuses InputDetector flow"
  - "Discovered spec content cached for _get_raw_spec() endpoint classification"

patterns-established:
  - "Two-stage discovery: spec discovery (Stage 1) then fuzzing fallback (Stage 2)"
  - "Stage progress feedback with [Stage 1] and [Stage 2] prefixes"

# Metrics
duration: 3min
completed: 2026-02-05
---

# Phase 8 Plan 3: CLI URL Mode and Discovery Wiring Summary

**--url CLI argument enables spec-less discovery with two-stage pipeline (spec discovery then endpoint fuzzing fallback)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-05T10:26:29Z
- **Completed:** 2026-02-05T10:29:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added --url/-u CLI argument as alternative to --input for URL-only mode
- Implemented mutual exclusion validation (cannot use both --input and --url)
- Wired two-stage discovery pipeline into PentestRunner._discover_from_url()
- Progress feedback shows [Stage 1] and [Stage 2] during discovery
- Discovered specs flow through existing InputDetector for consistent parsing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --url CLI argument to run_pentest.py** - `304cf20` (feat)
2. **Task 2: Wire discovery into PentestRunner** - `b5bcef1` (feat)

## Files Created/Modified
- `run_pentest.py` - Added --url argument, mutual exclusion validation, discovery_url config mapping
- `api_pentest/runner.py` - Added _discover_from_url(), _parse_discovered_spec(), updated parse_input() and _get_raw_spec()

## Decisions Made
- **Mutual exclusion:** --input and --url cannot be used together (parser.error validation)
- **Config key:** URL stored as discovery_url to distinguish from base_url override
- **Temp file parsing:** Discovered specs saved to temp file and parsed via InputDetector for consistency with --input flow
- **Spec caching:** Discovered spec content stored in _discovered_spec_content for _get_raw_spec() to enable endpoint classification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation straightforward with well-defined 08-01 and 08-02 interfaces.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 8 (Spec-less Auto Discovery) complete
- All DISC requirements satisfied:
  - DISC-07: SpecDiscoverer probes common paths
  - DISC-08: EndpointFuzzer discovers endpoints via fuzzing
  - DISC-09: --url CLI flag enables URL-only mode
  - DISC-10: Graceful Kiterunner fallback to built-in wordlist
- End-to-end testing recommended with real API targets

---
*Phase: 08-spec-less-auto-discovery*
*Completed: 2026-02-05*
