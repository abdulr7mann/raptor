# Roadmap: API Pentest Toolkit - Adaptive Security Testing

## Overview

Transform the existing API pentest toolkit from a static scanner with a 31% false positive rate into an adaptive security testing tool that learns API behavior before testing. The roadmap progresses through three arcs: first fix reporting quality and eliminate false positives through response analysis and endpoint classification (Phases 1-4), then build the unified discovery and profiling layer (Phases 5-6), and finally add advanced validation and intelligent test selection (Phase 7). Each phase delivers a verifiable reduction in false positives or improvement in finding accuracy, validated against VAmPI.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Evidence & Report Quality** - Fix missing endpoints, evidence, deduplication, and HTML escaping in findings
- [x] **Phase 2: Response Pattern Learning** - Learn API success/failure indicators to eliminate HTTP 200 + fail body false positives
- [x] **Phase 3: Endpoint Classification** - Classify public vs protected endpoints and detect endpoint purpose to eliminate auth-related false positives
- [x] **Phase 4: Prerequisite-Aware Testing** - Check preconditions before running tests to eliminate nonsensical test false positives
- [ ] **Phase 5: API Discovery & Profiling** - Probe APIs to detect auth scheme, architecture, and build unified API profile
- [ ] **Phase 6: Adaptive Test Execution** - Select and adjust tests based on API profile for intelligent, targeted scanning
- [ ] **Phase 7: Advanced Validation & Confidence** - Baseline comparison, multi-signal validation, and confidence-level classification of findings

## Phase Details

### Phase 1: Evidence & Report Quality
**Goal**: Every finding in a report includes its endpoint, HTTP evidence, and is unique -- reports are clean, complete, and safe to view
**Depends on**: Nothing (first phase)
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, FIX-05, FIX-06
**Success Criteria** (what must be TRUE):
  1. Every finding in VAmPI scan output includes the endpoint field (no "missing endpoint" entries)
  2. Every finding includes captured HTTP request/response evidence (no empty evidence fields)
  3. No duplicate findings appear in the report (same title + endpoint produces one finding)
  4. HTML report can be opened in a browser without triggering XSS from response body content
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Decompose aggregate findings in S01, S02, S05, S11 into per-endpoint findings with evidence
- [x] 01-02-PLAN.md -- Rewrite report generator with Jinja2 autoescape, Pygments highlighting, deduplication

### Phase 2: Response Pattern Learning
**Goal**: The toolkit learns how each API communicates success vs failure, so HTTP 200 + fail body is correctly identified as a failed test
**Depends on**: Phase 1 (clean findings needed to validate FP elimination)
**Requirements**: DISC-02, VALID-02, FIX-01
**Success Criteria** (what must be TRUE):
  1. Running a scan against VAmPI produces zero false positives from HTTP 200 + fail body pattern (currently 10 findings from S06, S09, S13)
  2. The toolkit analyzes baseline responses and identifies per-API success/failure indicators before running security tests
  3. Test validation checks both HTTP status code AND response body structure, not status code alone
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- Build ResponsePatternLearner with pre-scan learning pass and is_real_success() on BaseScenario
- [x] 02-02-PLAN.md -- Replace is_success_status with is_real_success in S06, S09, S13 and verify FP elimination

### Phase 3: Endpoint Classification
**Goal**: The toolkit distinguishes public from protected endpoints and understands endpoint purpose, so it does not flag expected behavior as vulnerabilities
**Depends on**: Phase 2 (response pattern learning informs classification accuracy)
**Requirements**: DISC-03, VALID-01, VALID-03, FIX-02, FIX-03
**Success Criteria** (what must be TRUE):
  1. Public endpoints (/, /books/v1, /createdb) are not flagged for missing authentication (currently 4 FPs from S07 and S06)
  2. Login endpoint returning auth_token is not flagged as data exposure (currently 1 FP from S08)
  3. Test results are validated against endpoint classification -- auth tests skip public endpoints, data exposure tests account for endpoint purpose
  4. Endpoint classification uses OpenAPI security definitions when available and falls back to path pattern heuristics
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md -- Build EndpointClassifier with three-tier classification, add classification fields to Endpoint, wire into runner
- [x] 03-02-PLAN.md -- Integrate classification into S07 and S08 to skip irrelevant tests and eliminate 5 FPs

### Phase 4: Prerequisite-Aware Testing
**Goal**: The toolkit checks whether a test's preconditions exist before running it, so it does not flag bypass of nonexistent controls
**Depends on**: Phase 3 (endpoint classification feeds prerequisite detection)
**Requirements**: VALID-04, FIX-04
**Success Criteria** (what must be TRUE):
  1. Rate limit bypass tests do not produce findings when no rate limiting exists on the target (currently 4 FPs from S02 with X-Forwarded-For/X-Real-IP/X-Originating-IP/X-Client-IP)
  2. The toolkit detects whether a security control (rate limiting, CORS, CSP) is present before testing bypass of that control
  3. Skipped tests are logged with reason (precondition not met) rather than silently omitted
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- Build PrerequisiteDetector with rate limit/CORS/CSP detection, gate S02 header bypass, wire into runner
- [x] 04-02-PLAN.md -- Gate S07/S11 CORS bypass tests, add "Not Applicable" section to HTML report

### Phase 5: API Discovery & Profiling
**Goal**: The toolkit probes an API to discover its authentication scheme, architecture type, and builds a reusable profile that captures everything learned
**Depends on**: Phase 3 (endpoint classification is input to profile construction)
**Requirements**: DISC-01, DISC-04, DISC-05, DISC-06
**Success Criteria** (what must be TRUE):
  1. Running discovery against VAmPI produces an API profile that correctly identifies the auth scheme (Bearer token), architecture (REST), and endpoint count
  2. The API profile is persisted to JSON and can be reused across scan runs without re-discovery
  3. Auth scheme detection works for Bearer tokens, API keys in headers, and session cookies (validated against at least one target per scheme)
  4. GraphQL APIs are detected and schema introspection is attempted when GraphQL architecture is identified
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md -- Build AuthDetector, ArchitectureDetector, and RequestBudget for auth scheme and architecture detection
- [ ] 05-02-PLAN.md -- Build ApiProfiler with profile persistence and wire discovery into runner

### Phase 6: Adaptive Test Execution
**Goal**: The toolkit uses the API profile to select only relevant tests for each endpoint and adjusts test parameters to match the target API
**Depends on**: Phase 5 (API profile drives test selection)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. GraphQL-specific tests are not executed against REST APIs and vice versa (test selection uses architecture from profile)
  2. Tests use the correct authentication headers, content types, and success criteria discovered from the API profile
  3. The toolkit handles JSON, XML, and plain text response formats without crashing or producing malformed findings
  4. Each test-endpoint pair has a relevance score and tests below the configured threshold are skipped with logged reason
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

### Phase 7: Advanced Validation & Confidence
**Goal**: Findings carry confidence levels backed by multiple validation signals, so users can distinguish confirmed vulnerabilities from uncertain indicators
**Depends on**: Phase 5 (profile provides baseline for comparison), Phase 6 (adaptive execution provides cleaner test results)
**Requirements**: VALID-05, VALID-06, RPT-05
**Success Criteria** (what must be TRUE):
  1. Every finding in the report includes a confidence level (CONFIRMED, LIKELY, or UNCERTAIN) with explanation of why that level was assigned
  2. Findings validated by 2+ independent signals (response diff, error message, timing, structure change) are classified as CONFIRMED
  3. Test responses are compared against baseline responses and findings identical to normal behavior are downgraded or suppressed
  4. Users can filter the report by confidence level to focus on high-certainty findings first
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 1. Evidence & Report Quality | 2/2 | Complete | 2026-02-04 |
| 2. Response Pattern Learning | 2/2 | Complete | 2026-02-04 |
| 3. Endpoint Classification | 2/2 | Complete | 2026-02-04 |
| 4. Prerequisite-Aware Testing | 2/2 | Complete | 2026-02-04 |
| 5. API Discovery & Profiling | 0/2 | Planned | - |
| 6. Adaptive Test Execution | 0/TBD | Not started | - |
| 7. Advanced Validation & Confidence | 0/TBD | Not started | - |
