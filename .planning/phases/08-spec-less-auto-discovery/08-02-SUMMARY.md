---
phase: 08-spec-less-auto-discovery
plan: 02
subsystem: api
tags: [kiterunner, fuzzing, endpoint-discovery, wordlist]

# Dependency graph
requires:
  - phase: 05-api-discovery-profiling
    provides: RequestBudget for shared request counting
  - phase: 08-01
    provides: SpecDiscoverer for spec-based discovery (this is fallback when spec fails)
provides:
  - KiterunnerAdapter subprocess wrapper for external Kiterunner CLI
  - Built-in 289-path API endpoint wordlist for fallback discovery
  - EndpointFuzzer orchestrator with Kiterunner/wordlist auto-fallback
affects: [08-03, 08-04, discovery-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess wrapper pattern for external CLI tools"
    - "Generator-based scan output for memory-efficient processing"
    - "Graceful fallback when external tools unavailable"

key-files:
  created:
    - api_pentest/core/kiterunner_adapter.py
    - api_pentest/core/endpoint_wordlist.py
    - api_pentest/core/endpoint_fuzzer.py
  modified:
    - api_pentest/core/__init__.py

key-decisions:
  - "shutil.which() for binary detection - checks both 'kr' and 'kiterunner' names"
  - "NDJSON parsing for Kiterunner output (line-by-line JSON)"
  - "Conservative PROTECTED classification for all fuzzed endpoints"
  - "289 endpoints in wordlist - exceeds 200 minimum for broad coverage"
  - "API response detection uses content-type + body heuristics"

patterns-established:
  - "External tool adapter: shutil.which + subprocess.run + timeout"
  - "Discovery fallback: primary tool -> built-in alternative"
  - "Budget-aware iteration: check can_request() before each HTTP call"

# Metrics
duration: 4min
completed: 2026-02-05
---

# Phase 08 Plan 02: Endpoint Fuzzer with Kiterunner Integration Summary

**Kiterunner subprocess adapter with built-in 289-path wordlist fallback for spec-less endpoint discovery**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-05T10:19:53Z
- **Completed:** 2026-02-05T10:23:36Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- KiterunnerAdapter wraps external CLI tool with JSON output parsing and graceful error handling
- Built-in 289-path wordlist covers auth, users, admin, health, actuator, graphql, and more
- EndpointFuzzer auto-detects Kiterunner availability and falls back to wordlist when needed
- All discovered endpoints converted to Endpoint model with PROTECTED classification

## Task Commits

Each task was committed atomically:

1. **Task 1: Create KiterunnerAdapter subprocess wrapper** - `e15dac7` (feat)
2. **Task 2: Create built-in endpoint wordlist** - `ca2dfc5` (feat)
3. **Task 3: Create EndpointFuzzer orchestrator with fallback** - `05c59e4` (feat)

## Files Created/Modified

- `api_pentest/core/kiterunner_adapter.py` - Subprocess wrapper for Kiterunner CLI with binary detection via shutil.which
- `api_pentest/core/endpoint_wordlist.py` - 289 curated API paths organized by category
- `api_pentest/core/endpoint_fuzzer.py` - Orchestrator that uses Kiterunner or wordlist based on availability
- `api_pentest/core/__init__.py` - Updated exports to include all new modules

## Decisions Made

1. **Binary detection**: shutil.which("kr") or shutil.which("kiterunner") - covers common installation names
2. **Kiterunner output format**: NDJSON (newline-delimited JSON) parsed line by line
3. **Default classification**: PROTECTED for all fuzzed endpoints (conservative - assume auth needed)
4. **Wordlist size**: 289 paths exceeds 200 minimum for comprehensive coverage
5. **API response detection**: Combines Content-Type header check with body heuristics (JSON/XML detection)
6. **Valid discovery statuses**: 200, 201, 204, 400, 401, 403, 405 all indicate endpoint exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

For enhanced discovery coverage, users can optionally install Kiterunner:
```bash
# Optional: Install Kiterunner for better endpoint discovery
go install github.com/assetnote/kiterunner/cmd/kr@latest
```

## Next Phase Readiness

- EndpointFuzzer ready for integration with discovery pipeline
- Exports available via `from api_pentest.core import EndpointFuzzer, KiterunnerAdapter`
- Next plan (08-03) should integrate SpecDiscoverer + EndpointFuzzer into unified flow
- RequestBudget sharing tested - budget.can_request()/record() pattern works

---
*Phase: 08-spec-less-auto-discovery*
*Completed: 2026-02-05*
