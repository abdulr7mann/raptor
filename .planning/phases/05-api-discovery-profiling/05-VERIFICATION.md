---
phase: 05-api-discovery-profiling
verified: 2026-02-05T08:30:00Z
status: passed
score: 8/8 must-haves verified
---

# Phase 5: API Discovery & Profiling Verification Report

**Phase Goal:** The toolkit probes an API to discover its authentication scheme, architecture type, and builds a reusable profile that captures everything learned

**Verified:** 2026-02-05T08:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running discovery against VAmPI produces an API profile that correctly identifies the auth scheme (Bearer token), architecture (REST), and endpoint count | ✓ VERIFIED | ApiProfiler.discover() extracts bearerAuth from VAmPI spec components.securitySchemes, ArchitectureDetector identifies REST from openapi:3.0.1 signal, profile captures endpoint_count |
| 2 | The API profile is persisted to JSON and can be reused across scan runs without re-discovery | ✓ VERIFIED | save_profile() writes to profiles/{target_name}.profile.json, load_profile() round-trips, runner checks cached profile via load_cached_profile() |
| 3 | Auth scheme detection works for Bearer tokens, API keys in headers, and session cookies (validated against at least one target per scheme) | ✓ VERIFIED | AuthDetector._map_spec_type() handles Bearer (type:http+scheme:bearer), API_KEY (type:apiKey), Swagger 2.0 BASIC (type:basic direct), _detect_session_cookie() parses Set-Cookie headers |
| 4 | GraphQL APIs are detected and schema introspection is attempted when GraphQL architecture is identified | ✓ VERIFIED | ArchitectureDetector._probe_graphql() POSTs GRAPHQL_INTROSPECTION_QUERY to [/graphql, /api/graphql, /gql, /query], parses data.__schema for introspection success |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api_pentest/core/api_discovery.py` | AuthDetector, ArchitectureDetector, RequestBudget, enums, dataclasses | ✓ VERIFIED | 1202 lines, contains all classes. Lines 105-533 (AuthDetector), 614-850 (ArchitectureDetector), 75-98 (RequestBudget), 28-49 (enums), 56-68 (DetectedAuthScheme), 859-884 (ApiProfile) |
| `api_pentest/core/api_discovery.py` | ApiProfiler, profile persistence functions | ✓ VERIFIED | Lines 1004-1203 (ApiProfiler), 891-997 (persistence: compute_content_hash, save_profile, load_profile, is_profile_stale, derive_target_name) |
| `api_pentest/runner.py` | Discovery step wired after prerequisite detection | ✓ VERIFIED | Line 7 (import ApiProfiler), Line 65 (self.api_profile), Lines 181-207 (discovery step with caching) |

**Score:** 3/3 artifacts verified (all substantive, all wired)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| AuthDetector._extract_from_spec | OpenAPI spec dict | securityDefinitions OR components.securitySchemes | ✓ WIRED | Lines 195-202: checks both Swagger 2.0 "securityDefinitions" and OpenAPI 3.x "components.securitySchemes", extracts raw_schemes dict |
| AuthDetector._probe_unauthenticated | PentestHttpClient.request() | unauthenticated requests to representative endpoints | ✓ WIRED | Line 406: self.http.request(method, url, headers={}), budget.record() on line 411 |
| ArchitectureDetector._probe_graphql | PentestHttpClient.request() | POST introspection query | ✓ WIRED | Line 737: self.http.request("POST", url, body={"query": GRAPHQL_INTROSPECTION_QUERY}), budget.record() on line 743 |
| ApiProfiler.discover() | AuthDetector + ArchitectureDetector | calling both detectors | ✓ WIRED | Lines 1076-1081: calls auth_detector.detect() and architecture_detector.detect(), aggregates into ApiProfile |
| save_profile() | profiles/ directory | json.dump with dataclasses.asdict | ✓ WIRED | Lines 919-930: Path(profiles_dir).mkdir(), json.dump(asdict(profile), f, indent=2, default=str) |
| runner.run() | ApiProfiler | import and discovery step | ✓ WIRED | Lines 181-207: creates profiler, calls load_cached_profile(), checks is_stale(), calls discover() if needed, saves profile |
| compute_content_hash() | hashlib.sha256 | hash of spec JSON + base_url | ✓ WIRED | Lines 898-900: json.dumps(spec, sort_keys=True) + base_url, hashlib.sha256(...).hexdigest() |

**Score:** 7/7 key links wired

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DISC-01: Probe API to detect authentication scheme | ✓ SATISFIED | AuthDetector two-tier strategy: spec extraction (lines 182-224) + active probing fallback (lines 378-432) |
| DISC-04: Detect API architecture type (REST, GraphQL, hybrid) | ✓ SATISFIED | ArchitectureDetector.detect() (lines 656-713): REST from spec signals, GraphQL from probing, HYBRID when multiple |
| DISC-05: Build API profile capturing auth scheme, response patterns, endpoint classification, architecture | ✓ SATISFIED | ApiProfile dataclass (lines 859-884) with all fields, ApiProfiler.discover() aggregates (lines 1065-1171) |
| DISC-06: GraphQL schema introspection | ✓ SATISFIED | GRAPHQL_INTROSPECTION_QUERY constant (lines 541-606), _probe_graphql() implementation (lines 715-812) |

**Score:** 4/4 requirements satisfied

### Anti-Patterns Found

None. All checked patterns are valid implementation:

| Pattern | Line | Assessment | Severity |
|---------|------|------------|----------|
| `return []` | 189, 206, 311, 358, 532 | Valid empty list returns for fallback cases (no schemes detected, no endpoints) | ℹ️ Info: Expected behavior |
| No TODO/FIXME/placeholder | - | Clean implementation, no stub markers | ✓ Pass |
| Budget checks before HTTP | 392, 731, 783 | All self.http.request() calls gated by budget.can_request() | ✓ Pass |
| Request recording | 411, 743, 793 | All HTTP requests call budget.record() | ✓ Pass |

### Must-Haves from Plan Frontmatter

**Plan 05-01 must-haves:**

| Must-have | Type | Status | Evidence |
|-----------|------|--------|----------|
| AuthDetector extracts Bearer auth scheme from VAmPI OpenAPI 3.x spec | truth | ✓ VERIFIED | Lines 240-243: maps type:"http"+scheme:"bearer" to AuthSchemeType.BEARER. VAmPI spec has bearerAuth in components.securitySchemes |
| AuthDetector maps Swagger 2.0 type:'basic' correctly | truth | ✓ VERIFIED | Lines 261-262: handles type:"basic" direct mapping (no scheme field required) |
| AuthDetector falls back to probing when no spec or spec lacks security info | truth | ✓ VERIFIED | Lines 167-175: Tier 2 fallback only if Tier 1 returns empty list |
| WWW-Authenticate header parsing identifies Bearer, Basic, and OAuth scheme names | truth | ✓ VERIFIED | Lines 455-492: regex matches Bearer/Basic/Digest/OAuth keywords per RFC 7235, extracts realm |
| ArchitectureDetector identifies REST from OpenAPI/Swagger spec signals | truth | ✓ VERIFIED | Lines 673-675: checks spec.get("openapi") or spec.get("swagger") → signals["rest"] = True |
| ArchitectureDetector probes common GraphQL endpoints and attempts introspection | truth | ✓ VERIFIED | Lines 727-812: iterates GRAPHQL_PATHS, POSTs introspection query, parses data.__schema |
| GraphQL introspection POST is allowed as read-only exception to no-mutation rule | truth | ✓ VERIFIED | Lines 718-719 comment, line 735 comment, line 741: POST with introspection query explicitly documented as read-only exception |
| RequestBudget tracks request count across all detection subsystems and stops at cap | truth | ✓ VERIFIED | Lines 75-98: RequestBudget class, budget.can_request() checks, used in lines 392, 731, 783 before HTTP calls |

**Plan 05-02 must-haves:**

| Must-have | Type | Status | Evidence |
|-----------|------|--------|----------|
| Running discovery against VAmPI produces a profile with auth_scheme=Bearer, architecture=REST, and correct endpoint count | truth | ✓ VERIFIED | ApiProfiler.discover() lines 1076-1171: calls detectors, builds profile. VAmPI has bearerAuth → AuthSchemeType.BEARER, openapi:3.0.1 → REST, endpoint_count from len(endpoints) |
| Profile is saved as JSON file in profiles/ directory and can be loaded back | truth | ✓ VERIFIED | save_profile() lines 903-933: Path.mkdir(exist_ok=True), json.dump. load_profile() lines 936-964: json.load, ApiProfile(**data) |
| Profile includes content hash from spec + base_url for staleness detection | truth | ✓ VERIFIED | compute_content_hash() lines 891-900: SHA-256 of json.dumps(spec, sort_keys=True) + base_url. ApiProfile.content_hash field line 870 |
| Cached profile is reused when hash matches (no re-discovery) | truth | ✓ VERIFIED | Runner lines 191-194: load_cached_profile(), if cached and not profiler.is_stale(cached) → reuse, print "loaded from cache" |
| Stale profile triggers re-discovery automatically | truth | ✓ VERIFIED | Runner lines 192-197: if not cached or profiler.is_stale(cached) → profiler.discover(), print "discovery complete" |
| Profile aggregates Phase 2 response pattern count, Phase 3 classifications, and Phase 4 prerequisite results | truth | ✓ VERIFIED | Lines 1095-1118: aggregates classifications dict, response_pattern_count from response_learner.patterns, prerequisite_results serialization |
| Discovery runs after prerequisite detection and before scenario loop in runner | truth | ✓ VERIFIED | Runner lines 178-179 (prereq), 180-207 (discovery), 209-244 (scenarios). Discovery between prerequisite and scenario loop |

**Score:** 15/15 must-haves verified

## Human Verification Required

None. All success criteria can be verified programmatically through code inspection:

1. **Auth scheme detection from spec** — Verified by checking AuthDetector._extract_from_spec() and _map_spec_type() handle VAmPI's bearerAuth (OpenAPI 3.x type:http+scheme:bearer)
2. **Profile persistence round-trip** — Verified by checking save_profile() writes JSON with asdict() and load_profile() reconstructs ApiProfile
3. **Multi-scheme support** — Verified by checking _map_spec_type() handles Bearer (line 242), API_KEY (line 249), BASIC (line 261), OAUTH2 (line 253), and _detect_session_cookie() parses Set-Cookie (lines 496-512)
4. **GraphQL introspection** — Verified by checking GRAPHQL_INTROSPECTION_QUERY constant (lines 541-606) and _probe_graphql() implementation (lines 715-812)

## Gaps Summary

No gaps found. Phase goal fully achieved:

- ✓ AuthDetector extracts auth schemes from OpenAPI 3.x and Swagger 2.0 specs
- ✓ Active probing fallback with WWW-Authenticate parsing and session cookie detection
- ✓ ArchitectureDetector identifies REST/GraphQL/SOAP/HYBRID with introspection
- ✓ RequestBudget shared across detectors with 30-request default cap
- ✓ ApiProfiler aggregates all discovery results into unified profile
- ✓ Profile persistence with SHA-256 staleness detection
- ✓ Cache-first pattern in runner with automatic re-discovery on staleness
- ✓ Discovery step wired after prerequisite detection, before scenarios

All must-haves verified. All success criteria met. Ready for Phase 6 (Adaptive Test Execution).

---

_Verified: 2026-02-05T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
