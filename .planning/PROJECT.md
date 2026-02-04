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

### Active

<!-- Redesign goals to fix false positives and make adaptive -->

**Discovery & Learning:**
- [ ] **DISC-01**: Probe API to detect authentication scheme (Bearer, API key, OAuth2, session cookies, custom headers)
- [ ] **DISC-02**: Analyze response patterns to identify success/failure indicators (status codes, body structure, error formats)
- [ ] **DISC-03**: Classify endpoints as public vs protected using OpenAPI security definitions
- [ ] **DISC-04**: Detect API architecture type (REST, GraphQL, gRPC, hybrid)
- [ ] **DISC-05**: Build API profile capturing auth scheme, response patterns, endpoint classification, architecture

**Intelligent Validation:**
- [ ] **VALID-01**: Validate test results against API profile (don't flag public endpoints for missing auth)
- [ ] **VALID-02**: Check both HTTP status AND response body for application-level failures (fix "HTTP 200 with fail message" false positives)
- [ ] **VALID-03**: Context-aware finding validation (login endpoints returning tokens is expected, not data exposure)
- [ ] **VALID-04**: Skip nonsensical tests (don't test rate limit bypass when no rate limiting exists)

**Adaptive Test Execution:**
- [ ] **TEST-01**: Select relevant tests based on API profile (skip GraphQL injection on REST APIs)
- [ ] **TEST-02**: Adjust test parameters based on discovered patterns (use correct auth headers, success criteria)
- [ ] **TEST-03**: Handle diverse response formats (JSON, XML, plain text, binary)

**Evidence & Reporting:**
- [ ] **RPT-01**: Include endpoint information in all findings (fix missing endpoint issue)
- [ ] **RPT-02**: Capture evidence for aggregate findings (multi-endpoint tests)
- [ ] **RPT-03**: Escape HTML output to prevent XSS in reports
- [ ] **RPT-04**: Deduplicate findings (same title + endpoint)
- [ ] **RPT-05**: Classify findings with confidence levels (HIGH/MEDIUM/LOW based on validation certainty)

**Known Issue Fixes:**
- [ ] **FIX-01**: Fix false positives from HTTP 200 + fail body (10 findings in VAmPI test)
- [ ] **FIX-02**: Fix false positives from public endpoints flagged for no auth (4 findings)
- [ ] **FIX-03**: Fix false positive from login endpoint returning auth_token (1 finding)
- [ ] **FIX-04**: Fix false positives from rate limit bypass tests when no rate limiting exists (4 findings)
- [ ] **FIX-05**: Add missing endpoint field to aggregate findings (9 findings)
- [ ] **FIX-06**: Add missing evidence to aggregate findings (15 findings)

### Out of Scope

- **AI-driven test generation** — Focus on proven OWASP test patterns, not experimental LLM-based testing (too unpredictable for pentest reliability)
- **Automated exploitation** — Discovery and reporting only, no active exploit execution or payload delivery beyond proof-of-concept
- **Network-level testing** — API layer only, not infrastructure scanning (port scanning, SSL/TLS auditing, DNS enumeration)
- **Performance testing** — Security-focused, not load/stress testing (rate limit detection is about bypass, not capacity planning)
- **SOAP/XML-RPC protocols** — Modern APIs only (REST, GraphQL, gRPC), legacy SOAP out of scope for v1
- **Authentication credential cracking** — Use provided credentials, don't brute force or dictionary attack login endpoints

## Context

**Existing System:**
The current toolkit has a solid foundation:
- Layered architecture with plugin-based scenario system
- 13 OWASP API security test scenarios implemented
- Evidence-based reporting with full request/response capture
- OpenAPI and Postman collection parsing
- OAuth2 token handling with JWT manipulation

**Current Problems (from issues.md audit):**
- ~31% false positive rate (18 of 58 findings on VAmPI test)
- Hardcoded assumptions (HTTP 200 = success, all endpoints need auth)
- No distinction between public vs protected endpoints
- Aggregate findings missing endpoint and evidence fields
- Doesn't adapt to different API patterns (works on VAmPI, breaks elsewhere)

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
| Architectural redesign over refactor | Systemic issues (31% FP rate) require fundamental rethink, not patches | — Pending |
| Discovery + OpenAPI dual approach | Discovery validates spec, fills gaps for APIs without specs, handles real-world deviations | — Pending |
| Python ecosystem | Existing stack (requests, PyJWT, prance) is solid, no need to rewrite | — Pending |

---
*Last updated: 2026-02-04 after initialization*
