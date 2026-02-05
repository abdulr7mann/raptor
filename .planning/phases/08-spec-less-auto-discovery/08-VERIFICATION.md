---
phase: 08-spec-less-auto-discovery
verified: 2026-02-05T10:32:42Z
status: passed
score: 5/5 must-haves verified
---

# Phase 8: Spec-less Auto-Discovery Verification Report

**Phase Goal:** The toolkit can pentest APIs with just a URL and credentials -- it automatically discovers specs or endpoints using Kiterunner

**Verified:** 2026-02-05T10:32:42Z
**Status:** PASSED
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running with `--url` (no `--input`) triggers automatic spec discovery at common paths | ✓ VERIFIED | `run_pentest.py` has `--url` arg with mutual exclusion validation; `runner.py` line 85 checks `discovery_url` and calls `_discover_from_url()`; Stage 1 message confirms spec discovery triggered |
| 2 | If a spec is found, it is downloaded, parsed, and used for testing (same as `--input` flow) | ✓ VERIFIED | `_parse_discovered_spec()` (lines 151-204) saves spec to temp file, uses `InputDetector` for parsing (same as `--input` flow), stores spec content for classification via `_get_raw_spec()` |
| 3 | If no spec is found, Kiterunner endpoint fuzzing discovers API endpoints using API-aware wordlists | ✓ VERIFIED | `_discover_from_url()` line 138 triggers Stage 2 fuzzing; `EndpointFuzzer.fuzz()` uses Kiterunner when available (lines 98-107), falls back to 289-path `API_ENDPOINTS` wordlist |
| 4 | Discovered endpoints flow through existing classification, prerequisite detection, and testing pipeline unchanged | ✓ VERIFIED | `_discover_from_url()` returns `self.endpoints` (line 149); runner uses same `self.endpoints` for classification (line 284), prerequisite detection (line 293), profiling (line 303), and scenario execution (lines 387-392) |
| 5 | Graceful fallback to built-in wordlist when Kiterunner binary is not installed | ✓ VERIFIED | `KiterunnerAdapter.is_available()` checks `shutil.which("kr")` (line 66); `EndpointFuzzer.fuzz()` tests availability and logs warning before falling back to `_fuzz_with_wordlist()` (lines 98-107) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `api_pentest/core/spec_discoverer.py` | ✓ VERIFIED | EXISTS (251 lines > 100 min), SUBSTANTIVE (SpecDiscoverer class with discover(), _detect_spec_type(), _try_graphql_introspection()), WIRED (imported in runner.py line 11, instantiated line 121) |
| `api_pentest/core/kiterunner_adapter.py` | ✓ VERIFIED | EXISTS (189 lines > 80 min), SUBSTANTIVE (KiterunnerAdapter with is_available(), scan() generator), WIRED (imported in endpoint_fuzzer.py line 27, instantiated line 87) |
| `api_pentest/core/endpoint_wordlist.py` | ✓ VERIFIED | EXISTS (386 lines > 150 min), SUBSTANTIVE (289 endpoints > 200 min, organized by category), WIRED (imported in endpoint_fuzzer.py line 28, used in _fuzz_with_wordlist() line 168) |
| `api_pentest/core/endpoint_fuzzer.py` | ✓ VERIFIED | EXISTS (356 lines > 100 min), SUBSTANTIVE (EndpointFuzzer with fuzz(), _fuzz_with_kiterunner(), _fuzz_with_wordlist()), WIRED (imported in runner.py line 10, instantiated line 140) |
| `run_pentest.py` | ✓ VERIFIED | EXISTS (189 lines > 175 min), SUBSTANTIVE (--url argument lines 64-68, mutual exclusion validation lines 118-122), WIRED (passes url to config line 140, config processed by runner) |
| `api_pentest/runner.py` | ✓ VERIFIED | EXISTS (576 lines > 480 min), SUBSTANTIVE (_discover_from_url() lines 105-149, _parse_discovered_spec() lines 151-204), WIRED (parse_input() calls _discover_from_url() line 86, endpoints flow to classification/testing) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_pentest.py` | `runner.py` | config url passed to PentestRunner | ✓ WIRED | Line 140 sets `cli_overrides["url"]`, line 34 maps to `config["discovery_url"]`, runner checks line 80 |
| `runner.py` | `spec_discoverer.py` | SpecDiscoverer import | ✓ WIRED | Line 11: `from api_pentest.core.spec_discoverer import SpecDiscoverer, SpecType`; instantiated line 121 with http_client and budget |
| `runner.py` | `endpoint_fuzzer.py` | EndpointFuzzer import | ✓ WIRED | Line 10: `from api_pentest.core.endpoint_fuzzer import EndpointFuzzer`; instantiated line 140 with http_client and budget |
| `spec_discoverer.py` | `api_discovery.py` | RequestBudget import | ✓ WIRED | Line 17: `from api_pentest.core.api_discovery import RequestBudget`; used in __init__ line 67, can_request() checks lines 91, 198 |
| `spec_discoverer.py` | `http_client.py` | PentestHttpClient usage | ✓ WIRED | `self.http_client.request()` called lines 109, 206; evidence returned and used |
| `endpoint_fuzzer.py` | `kiterunner_adapter.py` | KiterunnerAdapter import | ✓ WIRED | Line 27: `from api_pentest.core.kiterunner_adapter import KiterunnerAdapter`; instantiated line 87, used in fuzz() line 98 |
| `endpoint_fuzzer.py` | `endpoint_wordlist.py` | API_ENDPOINTS fallback | ✓ WIRED | Line 28: `from api_pentest.core.endpoint_wordlist import API_ENDPOINTS`; iterated in _fuzz_with_wordlist() line 168 |
| `endpoint_fuzzer.py` | `models.py` | Endpoint model creation | ✓ WIRED | Line 29: `from api_pentest.core.models import Endpoint`; Endpoint() instantiated lines 190, 253 with classification |

### Requirements Coverage

No requirements explicitly mapped to Phase 8 in REQUIREMENTS.md (grep "| 8 |" returned empty), but ROADMAP.md lists:
- DISC-07: Spec discovery at common paths - SATISFIED (SpecDiscoverer with 17 paths)
- DISC-08: Kiterunner endpoint fuzzing - SATISFIED (KiterunnerAdapter + EndpointFuzzer)
- DISC-09: --url CLI flag - SATISFIED (run_pentest.py --url argument)
- DISC-10: Graceful Kiterunner fallback - SATISFIED (built-in 289-path wordlist)

### Anti-Patterns Found

**None.** No TODOs, FIXMEs, placeholders, or stub patterns found in modified files.

All implementations are complete:
- SpecDiscoverer: Full detection logic for OpenAPI/Swagger/GraphQL
- KiterunnerAdapter: Subprocess handling with error cases
- EndpointFuzzer: Complete orchestration with validation
- CLI: Proper argument parsing with mutual exclusion
- Runner: Two-stage discovery with progress feedback

### Human Verification Required

#### 1. End-to-End Discovery with Real API

**Test:** Run `python run_pentest.py --url https://petstore.swagger.io/v2 --config pentest.yaml` (or similar public API)

**Expected:** 
- Stage 1 should find OpenAPI spec at /swagger.json or similar
- Endpoints should be parsed and displayed
- Testing should proceed as if `--input` was used

**Why human:** Requires live API target; integration test beyond file-level verification

#### 2. Kiterunner Availability Detection

**Test:** 
- Run with Kiterunner installed: Should see "Using Kiterunner for endpoint discovery"
- Run without Kiterunner: Should see "falling back to built-in wordlist" warning

**Expected:** Clean fallback behavior, no crashes

**Why human:** Requires environment with/without Kiterunner binary

#### 3. Stage 2 Fallback When No Spec Found

**Test:** Run `python run_pentest.py --url http://example.com/nonexistent --config pentest.yaml` (API with no spec at common paths)

**Expected:**
- Stage 1 should try paths and find nothing
- Stage 2 should trigger fuzzing
- Some endpoints discovered (if API exists) or graceful handling if none found

**Why human:** Requires API without spec; edge case testing

#### 4. Mutual Exclusion Validation

**Test:** Run `python run_pentest.py --input test.json --url http://example.com`

**Expected:** Error message "Cannot use both --input and --url"

**Why human:** CLI validation test (can be automated but requires test harness)

---

## Verification Details

### Level 1: Existence (All Artifacts)

All 6 required artifacts exist:
- ✓ `api_pentest/core/spec_discoverer.py` (251 lines)
- ✓ `api_pentest/core/kiterunner_adapter.py` (189 lines)
- ✓ `api_pentest/core/endpoint_wordlist.py` (386 lines)
- ✓ `api_pentest/core/endpoint_fuzzer.py` (356 lines)
- ✓ `run_pentest.py` (189 lines)
- ✓ `api_pentest/runner.py` (576 lines)

All exceed minimum line requirements from PLAN must_haves.

### Level 2: Substantive (Implementation Quality)

**SpecDiscoverer:**
- 17 SPEC_PATHS covering OpenAPI/Swagger/GraphQL (> 15 required)
- discover() method with budget checking and logging
- _detect_spec_type() with JSON parsing and format detection
- _try_graphql_introspection() with POST request and introspection query
- No stubs, no TODOs

**KiterunnerAdapter:**
- Binary detection via `shutil.which("kr") or shutil.which("kiterunner")`
- scan() generator with subprocess handling
- NDJSON output parsing (line-by-line JSON)
- Timeout and error handling
- No stubs, no TODOs

**EndpointFuzzer:**
- fuzz() orchestration with is_available() check
- _fuzz_with_kiterunner() with deduplication and validation
- _fuzz_with_wordlist() with budget checking
- _is_valid_discovery() with status + content-type heuristics
- Discovered endpoints converted to Endpoint model with PROTECTED classification
- No stubs, no TODOs

**endpoint_wordlist:**
- 289 endpoints organized by category
- Covers auth, users, admin, health, actuator, graphql, payment, etc.
- HTTP_METHODS constant
- No stubs, no TODOs

**CLI (run_pentest.py):**
- --url argument with help text
- Mutual exclusion validation (lines 118-122)
- Config mapping (line 34: discovery_url)
- Example in epilog
- No stubs, no TODOs

**Runner (api_pentest/runner.py):**
- _discover_from_url() with two-stage pipeline and progress feedback
- _parse_discovered_spec() with temp file and InputDetector reuse
- _get_raw_spec() updated to handle discovery_url mode (lines 546-558)
- Stage messages with color coding
- No stubs, no TODOs

### Level 3: Wired (Integration)

**SpecDiscoverer → Runner:**
- Imported line 11 of runner.py
- Instantiated in _discover_from_url() line 121
- Used with http_client and RequestBudget
- discover() called line 126
- Result processed lines 128-136

**EndpointFuzzer → Runner:**
- Imported line 10 of runner.py
- Instantiated in _discover_from_url() line 140
- Used with http_client and RequestBudget
- fuzz() called line 145
- Result stored in self.endpoints

**Endpoints → Pipeline:**
- Stored in self.endpoints (line 145 for fuzzing, line 181 for spec parsing)
- Used by EndpointClassifier (line 284: `endpoints=self.endpoints`)
- Used by PrerequisiteChecker (line 293: `endpoints=self.endpoints`)
- Used by ApiProfiler (line 303: `endpoints=self.endpoints`)
- Used by scenario execution (lines 387-392: filtered/iterated)

**RequestBudget:**
- Created in _discover_from_url() line 115 with max_requests=100
- Passed to SpecDiscoverer line 124
- Passed to EndpointFuzzer line 143
- SpecDiscoverer calls budget.can_request() lines 91, 198
- SpecDiscoverer calls budget.record() lines 114, 134, 212, 248
- EndpointFuzzer calls budget.can_request() lines 134, 170
- EndpointFuzzer calls budget.record() lines 186, 279

**KiterunnerAdapter:**
- Imported in endpoint_fuzzer.py line 27
- Instantiated line 87: `self.kr = KiterunnerAdapter()`
- is_available() checked line 98
- scan() called line 122 with self.base_url
- Results converted to Endpoint objects line 123

**API_ENDPOINTS Wordlist:**
- Imported in endpoint_fuzzer.py line 28
- Iterated in _fuzz_with_wordlist() line 168
- 289 paths tested with GET requests
- Responses validated with _is_valid_discovery()

### Import Verification

All imports tested successfully:
```
✓ from api_pentest.core.spec_discoverer import SpecDiscoverer, SpecType
✓ from api_pentest.core.kiterunner_adapter import KiterunnerAdapter, KiterunnerNotFoundError
✓ from api_pentest.core.endpoint_wordlist import API_ENDPOINTS, HTTP_METHODS
✓ from api_pentest.core.endpoint_fuzzer import EndpointFuzzer
✓ from api_pentest.core import SpecDiscoverer, SpecType (via __init__.py)
✓ from api_pentest.core import EndpointFuzzer (via __init__.py)
```

All exports present in `api_pentest/core/__init__.py` lines 15-45.

---

## Summary

Phase 8 goal **ACHIEVED**. The toolkit can now pentest APIs with just a URL:

1. **--url argument** triggers spec-less discovery mode
2. **Stage 1** probes 17 common spec paths (OpenAPI/Swagger/GraphQL)
3. **If spec found:** Downloaded, parsed with InputDetector, used for testing (same as --input)
4. **If no spec:** Stage 2 fuzzing with Kiterunner or 289-path wordlist
5. **Discovered endpoints** flow through classification, prerequisite detection, and testing unchanged
6. **Graceful fallback** when Kiterunner not installed

All 5 observable truths verified. All 6 artifacts substantive and wired. No stubs, no blockers.

Human verification recommended for end-to-end integration testing with live APIs.

---

_Verified: 2026-02-05T10:32:42Z_
_Verifier: Claude (gsd-verifier)_
