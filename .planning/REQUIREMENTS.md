# Requirements: API Pentest Toolkit - Adaptive Security Testing

**Defined:** 2026-02-04
**Core Value:** Accuracy - findings must be real vulnerabilities, not false positives

## v1 Requirements

Requirements for adaptive enhancement release. Each maps to roadmap phases.

### Discovery & Learning

- [x] **DISC-01**: Probe API to detect authentication scheme (Bearer, API key, OAuth2, session cookies, custom headers)
- [x] **DISC-02**: Analyze response patterns to identify success/failure indicators (status codes, body structure, error formats)
- [x] **DISC-03**: Classify endpoints as public vs protected using OpenAPI security definitions
- [x] **DISC-04**: Detect API architecture type (REST, GraphQL, gRPC, hybrid)
- [x] **DISC-05**: Build API profile capturing auth scheme, response patterns, endpoint classification, architecture
- [x] **DISC-06**: GraphQL schema introspection - discover full schema via `__schema` query or Clairvoyance-style probing

### Intelligent Validation

- [x] **VALID-01**: Validate test results against API profile (don't flag public endpoints for missing auth)
- [x] **VALID-02**: Check both HTTP status AND response body for application-level failures (fix "HTTP 200 with fail message" false positives)
- [x] **VALID-03**: Context-aware finding validation (login endpoints returning tokens is expected, not data exposure)
- [x] **VALID-04**: Skip nonsensical tests (don't test rate limit bypass when no rate limiting exists)
- [ ] **VALID-05**: Baseline comparison validation - compare test response against baseline for differential testing
- [ ] **VALID-06**: Multi-signal finding validation - require 2+ independent indicators for CONFIRMED confidence

### Adaptive Test Execution

- [ ] **TEST-01**: Select relevant tests based on API profile (skip GraphQL injection on REST APIs)
- [ ] **TEST-02**: Adjust test parameters based on discovered patterns (use correct auth headers, success criteria)
- [ ] **TEST-03**: Handle diverse response formats (JSON, XML, plain text, binary)
- [ ] **TEST-04**: Test relevance scoring - score test-to-endpoint relevance, skip below threshold

### Evidence & Reporting

- [x] **RPT-01**: Include endpoint information in all findings (fix missing endpoint issue)
- [x] **RPT-02**: Capture evidence for aggregate findings (multi-endpoint tests)
- [x] **RPT-03**: Escape HTML output to prevent XSS in reports
- [x] **RPT-04**: Deduplicate findings (same title + endpoint)
- [ ] **RPT-05**: Classify findings with confidence levels (CONFIRMED/LIKELY/UNCERTAIN based on validation certainty)

### Known Issue Fixes

- [x] **FIX-01**: Fix false positives from HTTP 200 + fail body (10 findings in VAmPI test - S06, S09, S13 scenarios)
- [x] **FIX-02**: Fix false positives from public endpoints flagged for no auth (4 findings - S07 on /, /books/v1, /createdb; S06 on /login)
- [x] **FIX-03**: Fix false positive from login endpoint returning auth_token (1 finding - S08 data exposure)
- [x] **FIX-04**: Fix false positives from rate limit bypass tests when no rate limiting exists (4 findings - S02 X-Forwarded-For/X-Real-IP/X-Originating-IP/X-Client-IP)
- [x] **FIX-05**: Add missing endpoint field to aggregate findings (9 findings - S01, S02, S05, S11)
- [x] **FIX-06**: Add missing evidence to aggregate findings (15 findings - S01, S02, S05, S11)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

(None - all features scoped to v1)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| AI/ML-based vulnerability detection | ML requires massive training datasets, produces unpredictable results. Pentest tools need deterministic, explainable findings. Use deterministic heuristics instead. |
| Aggressive payload generation | More payloads without better validation amplifies FP problem. Focus on validating results from existing 13 scenarios' payloads. |
| Real-time learning during scan | Introduces non-deterministic behavior, makes results non-reproducible. Use dedicated discovery phase with frozen profile for testing. |
| Automated exploitation/weaponization | Discovery and reporting only per PROJECT.md. No active exploit execution beyond proof-of-concept. |
| Scan everything by default | Root cause of 31% FP rate. Default to intelligent selection, allow --all-tests flag for exhaustive scanning. |
| Suppressing all LOW confidence findings | Hiding UNCERTAIN findings risks missing real vulnerabilities (false negatives worse than false positives). Report all with clear confidence levels. |
| Network-level discovery/testing | API layer only per PROJECT.md. Port scanning, SSL/TLS auditing, DNS enumeration out of scope. |
| SOAP/XML-RPC protocols | Modern APIs only (REST, GraphQL, gRPC). Legacy SOAP out of scope for v1. |
| Authentication credential cracking | Use provided credentials, don't brute force or dictionary attack login endpoints. |
| Performance/load testing | Security-focused, not capacity planning. Rate limit detection is about bypass, not performance benchmarking. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 5: API Discovery & Profiling | Complete |
| DISC-02 | Phase 2: Response Pattern Learning | Complete |
| DISC-03 | Phase 3: Endpoint Classification | Complete |
| DISC-04 | Phase 5: API Discovery & Profiling | Complete |
| DISC-05 | Phase 5: API Discovery & Profiling | Complete |
| DISC-06 | Phase 5: API Discovery & Profiling | Complete |
| VALID-01 | Phase 3: Endpoint Classification | Complete |
| VALID-02 | Phase 2: Response Pattern Learning | Complete |
| VALID-03 | Phase 3: Endpoint Classification | Complete |
| VALID-04 | Phase 4: Prerequisite-Aware Testing | Complete |
| VALID-05 | Phase 7: Advanced Validation & Confidence | Pending |
| VALID-06 | Phase 7: Advanced Validation & Confidence | Pending |
| TEST-01 | Phase 6: Adaptive Test Execution | Pending |
| TEST-02 | Phase 6: Adaptive Test Execution | Pending |
| TEST-03 | Phase 6: Adaptive Test Execution | Pending |
| TEST-04 | Phase 6: Adaptive Test Execution | Pending |
| RPT-01 | Phase 1: Evidence & Report Quality | Complete |
| RPT-02 | Phase 1: Evidence & Report Quality | Complete |
| RPT-03 | Phase 1: Evidence & Report Quality | Complete |
| RPT-04 | Phase 1: Evidence & Report Quality | Complete |
| RPT-05 | Phase 7: Advanced Validation & Confidence | Pending |
| FIX-01 | Phase 2: Response Pattern Learning | Complete |
| FIX-02 | Phase 3: Endpoint Classification | Complete |
| FIX-03 | Phase 3: Endpoint Classification | Complete |
| FIX-04 | Phase 4: Prerequisite-Aware Testing | Complete |
| FIX-05 | Phase 1: Evidence & Report Quality | Complete |
| FIX-06 | Phase 1: Evidence & Report Quality | Complete |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-05 after Phase 5 completion*
