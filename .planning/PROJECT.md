# API Pentest Toolkit - Adaptive Security Testing

## What This Is

An API security testing toolkit that automatically adapts to different API architectures, authentication schemes, and response patterns. It uses discovery and OpenAPI specifications to learn API behavior, then executes OWASP-based security tests with high accuracy and minimal false positives. Built for pentesting REST, GraphQL, and gRPC APIs across any domain without manual configuration.

## Core Value

**Accuracy** — Security findings must be real vulnerabilities, not false positives. A pentest tool that produces noise erodes trust and wastes time investigating non-issues. Every finding reported must be actionable.

## Requirements

### Validated

<!-- Existing capabilities from current codebase -->

- ✓ Parse API specifications (Postman collections, OpenAPI 2.0/3.0/3.1, Swagger) — existing
- ✓ Extract endpoints with methods, paths, parameters, bodies, headers — existing
- ✓ Handle OAuth2 authentication (client_credentials, password grant flows) — existing
- ✓ Execute HTTP requests with evidence capture (full request/response cycle) — existing
- ✓ Generate JSON and HTML reports with findings and evidence — existing
- ✓ Support 13 OWASP API security test categories (token reuse, rate limiting, IDOR, injection, privilege escalation, access controls, data exposure, business logic, mass assignment, security misconfig, unsafe consumption, resource exhaustion) — existing
- ✓ Configure via YAML with CLI overrides — existing
- ✓ Handle retries, timeouts, SSL verification settings — existing

### Completed (v1)

<!-- All v1 adaptive enhancement requirements completed -->

**Discovery & Learning:**
- [x] **DISC-01**: Probe API to detect authentication scheme (Bearer, API key, OAuth2, session cookies, custom headers)
- [x] **DISC-02**: Analyze response patterns to identify success/failure indicators (status codes, body structure, error formats)
- [x] **DISC-03**: Classify endpoints as public vs protected using OpenAPI security definitions
- [x] **DISC-04**: Detect API architecture type (REST, GraphQL, gRPC, hybrid)
- [x] **DISC-05**: Build API profile capturing auth scheme, response patterns, endpoint classification, architecture
- [x] **DISC-06**: GraphQL schema introspection

**Intelligent Validation:**
- [x] **VALID-01**: Validate test results against API profile (don't flag public endpoints for missing auth)
- [x] **VALID-02**: Check both HTTP status AND response body for application-level failures
- [x] **VALID-03**: Context-aware finding validation (login endpoints returning tokens is expected)
- [x] **VALID-04**: Skip nonsensical tests (don't test rate limit bypass when no rate limiting exists)
- [x] **VALID-05**: Baseline comparison validation
- [x] **VALID-06**: Multi-signal finding validation (2+ signals = CONFIRMED)

**Adaptive Test Execution:**
- [x] **TEST-01**: Select relevant tests based on API profile (skip GraphQL injection on REST APIs)
- [x] **TEST-02**: Adjust test parameters based on discovered patterns
- [x] **TEST-03**: Handle diverse response formats (JSON, XML, plain text, binary)
- [x] **TEST-04**: Test relevance scoring and threshold filtering

**Evidence & Reporting:**
- [x] **RPT-01**: Include endpoint information in all findings
- [x] **RPT-02**: Capture evidence for aggregate findings
- [x] **RPT-03**: Escape HTML output to prevent XSS in reports
- [x] **RPT-04**: Deduplicate findings (same title + endpoint)
- [x] **RPT-05**: Classify findings with confidence levels (CONFIRMED/LIKELY/UNCERTAIN)

### Active (v2 - Phase 8)

<!-- Spec-less auto-discovery with Kiterunner -->

**Spec-less Auto-Discovery:**
- [ ] **DISC-07**: Auto-discover API specs at common paths (/openapi.json, /swagger.json, /api-docs, /graphql)
- [ ] **DISC-08**: Integrate Kiterunner for spec discovery and endpoint fuzzing
- [ ] **DISC-09**: Support --url mode (auto-discover) as alternative to --input mode (spec provided)
- [ ] **DISC-10**: Graceful fallback to built-in wordlist when Kiterunner not installed

### Out of Scope

- **AI-driven test generation** — Focus on proven OWASP test patterns, not experimental LLM-based testing (too unpredictable for pentest reliability)
- **Automated exploitation** — Discovery and reporting only, no active exploit execution or payload delivery beyond proof-of-concept
- **Network-level testing** — API layer only, not infrastructure scanning (port scanning, SSL/TLS auditing, DNS enumeration)
- **Performance testing** — Security-focused, not load/stress testing (rate limit detection is about bypass, not capacity planning)
- **SOAP/XML-RPC protocols** — Modern APIs only (REST, GraphQL, gRPC), legacy SOAP out of scope for v1
- **Authentication credential cracking** — Use provided credentials, don't brute force or dictionary attack login endpoints

## Context

**Current System (v1 Complete):**
The toolkit now has adaptive security testing:
- Response pattern learning (HTTP 200 + fail body detection)
- Endpoint classification (public/protected/auth-endpoint)
- Prerequisite-aware testing (skip bypass tests when control absent)
- API discovery & profiling (auth scheme, architecture detection)
- Adaptive test execution (relevance scoring, architecture filtering)
- Confidence-level findings (CONFIRMED/LIKELY/UNCERTAIN)
- Clean reports with evidence, deduplication, XSS protection

**Current Limitation (v2 Target):**
- Requires OpenAPI/Postman spec to know endpoints
- Real-world pentests often have just URL + credentials
- Shadow/undocumented endpoints missed if not in spec

**Target Use Cases:**
- REST APIs with various auth schemes (Bearer, API keys, OAuth2, custom)
- GraphQL APIs with schema introspection
- gRPC APIs with reflection
- APIs across domains: e-commerce, SaaS, fintech, social platforms
- APIs with and without OpenAPI specifications

**Known Test Target:**
VAmPI (Vulnerable API at localhost:5000) serves as validation target - must achieve near-zero false positives while detecting all intentional vulnerabilities.

## Constraints

- **Accuracy over speed** — Prioritize low false positive rate over test execution speed (better to run slower and be accurate than fast and noisy)
- **Evidence required** — Every finding must include captured HTTP evidence (no theoretical findings)
- **Existing test categories** — Keep 13 OWASP API security test scenarios as foundation (refactor implementation, not remove tests)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Architectural redesign over refactor | Systemic issues (31% FP rate) require fundamental rethink, not patches | ✓ Complete (v1) |
| Discovery + OpenAPI dual approach | Discovery validates spec, fills gaps for APIs without specs, handles real-world deviations | ✓ Complete (v1) |
| Python ecosystem | Existing stack (requests, PyJWT, prance) is solid, no need to rewrite | ✓ Complete |
| Kiterunner integration for spec-less mode | Best-in-class API discovery tool, API-aware wordlists, high performance | — Phase 8 |
| Spec-first then fuzz | Try to find existing spec before fuzzing (more efficient) | — Phase 8 |

---
*Last updated: 2026-02-05 after adding Phase 8 (Spec-less Auto-Discovery)*
