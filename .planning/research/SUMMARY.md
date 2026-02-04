# Project Research Summary

**Project:** Adaptive API Security Testing
**Domain:** API pentest toolkit - intelligent test selection and false positive reduction
**Researched:** 2026-02-04
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is an enhancement to an existing API pentest toolkit that suffers from a 31% false positive rate. The current toolkit implements 13 OWASP security test scenarios but uses hardcoded assumptions that ignore API-specific behavior. The adaptive layer being built will transform this from a static scanner into an intelligent pentest tool by adding three core capabilities: (1) API discovery and learning, (2) contextual validation of findings, and (3) intelligent test selection based on endpoint classification.

The recommended approach combines deterministic heuristics with OpenAPI spec intelligence. Use deepdiff and jsonschema for response validation (fixes the HTTP 200 + fail body false positives), enhance the existing OpenAPI parser to extract security metadata (identifies public vs protected endpoints), and implement endpoint classification with conditional test execution (avoids testing login endpoints for data exposure or public endpoints for auth bypass). This approach is deliberately non-ML: pattern matching and rule-based logic produce explainable, reproducible results that are essential for pentest reporting.

The critical risks center on overfitting to a single test target (VAmPI) and introducing new false positives while fixing old ones. Mitigation requires testing against diverse API architectures, building regression tests before implementing fixes, and treating OpenAPI specs as hypotheses to be validated rather than ground truth. The existing codebase already has the hooks needed (baseline capture, OpenAPI parsing, finding model), but they are not connected into an adaptive workflow.

## Key Findings

### Recommended Stack

The stack is scoped to adaptive capabilities only. The existing toolkit already has core HTTP and OpenAPI libraries (requests, prance, pyjwt). The adaptive layer adds three functional areas: OpenAPI intelligence, response analysis, and API profiling.

**Core technologies:**
- **openapi-core 0.22.0**: Deep OpenAPI spec parsing with security scheme extraction — only Python library that provides structured security data providers (Bearer/Basic/API key detection) via result.security after unmarshalling. Enables extracting HOW an endpoint is secured, not just THAT it is secured.
- **deepdiff 8.6.1**: Structural diff of API responses — distinguishes "same structure, different values" (legitimate parameterized response) from "completely different structure" (genuine IDOR). Eliminates the false positives from naive string comparison (current approach: `body != baseline_body` flags any timestamp difference).
- **jsonschema 4.26.0**: Response structure validation against OpenAPI schemas — validates whether responses conform to declared schemas and enables learning schemas from observed responses. Note: requires Python >= 3.10.
- **pydantic 2.12.5**: Type-safe API profile models with validation and JSON serialization — needed for persisting learned API profiles between runs with integrity validation.
- **difflib (stdlib)**: Response similarity scoring via SequenceMatcher.ratio() — provides 0-1 similarity scores for body comparison without external dependencies.

**Supporting libraries:**
- **graphql-core 3.2.7** (optional): GraphQL introspection query support for GraphQL API discovery. Defer unless targeting GraphQL.
- **grpcio-reflection 1.76.0+** (optional): gRPC service reflection for gRPC API discovery. Defer unless targeting gRPC.
- **httpx 0.28.1** (optional, deferred): Async HTTP client with HTTP/2 support. Current requests-based client works fine; migration adds risk without immediate benefit. Defer to when HTTP/2 is specifically needed.

**Alternatives considered and rejected:**
- Rule engines (GoRules, pyKnow): Overkill for 13-scenario selection logic. Simple Python scoring function is clearer and more testable.
- ML-based validation (scikit-learn): Requires training data we don't have. The FP problem is caused by bad heuristics, not by data that needs ML.
- Aggressive payload generation: More payloads without better validation amplifies the FP problem. Focus on validating results from existing payloads.

### Expected Features

Research focused exclusively on adaptive features needed to eliminate the 31% false positive rate. Basic security tests (IDOR, injection, rate limiting) are already implemented.

**Must have (table stakes for "adaptive"):**
- **Response Pattern Learning (TS-1)**: APIs return success/failure differently. HTTP 200 + `{"status":"fail"}` is a rejection, not a success. Must learn each API's success/failure indicators from baseline responses. Eliminates 10 false positives from treating HTTP 200 + fail body as success.
- **Endpoint Classification (TS-2)**: Distinguish public vs protected endpoints using OpenAPI security field and path pattern heuristics. Eliminates 4 false positives from testing auth on public endpoints like `/`, `/login`, `/health`.
- **Endpoint Purpose Detection (TS-3)**: Login endpoints return auth tokens, register endpoints create users, health endpoints return status. Pattern-based heuristics on paths (`/login`, `/auth`, `/register`, `/health`) and OpenAPI operationId. Eliminates false positives like flagging auth_token in login response as data exposure.
- **Prerequisite-Aware Test Execution (TS-4)**: Check preconditions before running tests. If no rate limiting detected, skip rate limit bypass tests. Eliminates 4 false positives from running bypass tests without precondition.
- **Confidence-Level Findings (TS-5)**: Classify findings as CONFIRMED (exploit reproduced), LIKELY (strong indicators), or UNCERTAIN (needs manual review). Users cannot distinguish real vulnerabilities from noise without this.
- **Finding Deduplication (TS-6)**: Signature-based dedup using hash of (title, endpoint, scenario_id). Eliminates duplicate findings in reports.
- **Evidence-Required Findings (TS-7)**: Enforce endpoint and evidence fields for all findings. 9 findings missing endpoint, 15 missing evidence in current reports.

**Should have (competitive differentiators):**
- **API Profile Construction (DF-1)**: Structured profile of the API capturing auth scheme, response patterns, endpoint classification, error format. Central data structure that discovery features feed into and test execution features read from.
- **Baseline Comparison Validation (DF-4)**: For every test, compare response against baseline. If identical to normal behavior, the vulnerability is likely a false positive. Differential testing approach.
- **Contextual Finding Suppression (DF-5)**: Suppress expected behavior. Login returning token is not data exposure. Register creating user is not privilege escalation. Health being public is not missing auth.
- **Auth Scheme Auto-Detection (DF-2)**: Probe to detect Bearer token, API key in header/query, session cookie, custom headers. No manual auth configuration needed.
- **Response Format Fingerprinting (DF-3)**: Detect whether API uses structured error responses (RFC 9457 Problem Details, custom JSON envelopes) vs raw HTTP status codes. Calibrate validation per API's error format.
- **Test Relevance Scoring (DF-6)**: Score each test's relevance to each endpoint before execution. SQL injection on path parameter is more relevant than on boolean flag. Skip tests below threshold.
- **Multi-Signal Finding Validation (DF-7)**: Validate findings using multiple independent signals (response diff + error messages + timing + structure change). Require 2+ signals for CONFIRMED status.

**Defer (v2+):**
- **GraphQL Schema Introspection (DF-8)**: Expand to GraphQL APIs with introspection-based endpoint generation.
- gRPC reflection-based discovery
- Cross-endpoint workflow testing
- Finding trend analysis across runs

**Anti-features (deliberately avoid):**
- AI/ML-based vulnerability detection: Unpredictable results without training data. Pentest tools need deterministic, explainable findings.
- Aggressive payload generation: Volume creates noise. Focus on validating existing payloads.
- Real-time learning during scan: Non-deterministic behavior makes debugging impossible and reports non-reproducible.
- Automated exploitation: Crosses line from testing to attacking. Liability concerns.
- Scan everything by default: Current behavior is root cause of 31% FP rate. Default to intelligent selection.

### Architecture Approach

Architecture research was skipped due to technical issues, but component structure emerges from features and stack:

**Major components:**
1. **OpenAPI Intelligence Layer** (openapi-core + openapi-pydantic) — Extracts security metadata, parameter types, response schemas from specs. Enhances existing prance-based parser.
2. **API Discovery Engine** (graphql-core, grpcio-reflection, custom probing) — Protocol detection (REST/GraphQL/gRPC), auth scheme probing, endpoint classification. Builds API profile.
3. **Response Analysis Engine** (deepdiff, jsonschema, difflib, stdlib statistics) — Structural response comparison, baseline calibration, response time anomaly detection, error pattern matching.
4. **API Profile Model** (pydantic) — Central data structure capturing discovered API characteristics. Persisted to JSON between runs.
5. **Adaptive Test Orchestrator** — Filters endpoints by classification, checks prerequisites, selects relevant tests based on profile, scores confidence.
6. **Enhanced Finding Model** — Adds confidence levels, requires evidence, supports deduplication.

**Integration pattern:**
Existing baseline capture (`base_scenario.py:95-110`) and OpenAPI parser (`openapi_parser.py`) already exist but are not connected into an adaptive workflow. The adaptive layer bridges these by feeding discovery results into the profile, then using the profile to drive test selection and validation.

### Critical Pitfalls

1. **Blind Trust in OpenAPI Specifications** — Specs are frequently incomplete, outdated, or wrong. Treat spec as hypothesis, not truth. Validate security classification via runtime probing regardless of what spec says. If endpoint spec marks public actually returns 401, flag discrepancy and treat as protected. Never rely solely on spec's security field.

2. **Overfitting Response Pattern Detection to a Single Target** — Scanner tuned on VAmPI learns `{"status":"fail"}` means failure, then breaks on APIs using `{"error":true}` or XML or HTML errors. Build response pattern detector as ranked hierarchy of checks (HTTP status → Content-Type parsing → structural pattern → semantic value), not single pattern match. Test against 5+ different API response styles before shipping.

3. **Fixing Old False Positives While Introducing New Ones** — Each FP fix is a new decision rule with its own edge cases. Without regression testing, fixes validated only against specific FP they eliminate, not full finding corpus. Establish ground truth test suite of known TPs and FPs before any fixes. Every fix must pass both: eliminate targeted FP AND not suppress known TPs.

4. **OpenAPI Security Inheritance Misinterpretation** — Operation-level security completely replaces (not merges with) global security. Empty `security:[]` at operation level explicitly marks public (overrides global). Missing security field means inherit from global. Implement explicit test cases for every inheritance scenario. Default ambiguous cases to "unknown" and verify with runtime probing.

5. **Discovery Probing That Damages the Target** — Probes can create test records, trigger emails, exhaust rate limits, or reset databases (VAmPI `/createdb`). Implement safe discovery mode limiting initial probing to safe HTTP methods (GET/HEAD/OPTIONS). Flag operations with descriptions containing "create", "delete", "reset" as potentially destructive. Require explicit opt-in for destructive discovery.

6. **Context-Insensitive Test Selection** — Applying all 13 scenarios to all endpoints is root cause of multiple FPs: testing login for data exposure, public endpoints for auth bypass, bypass tests without preconditions. Build endpoint classification system with categories that map to test applicability. Each scenario declares which endpoint categories it applies to.

**Additional moderate pitfalls:**
- Aggregate finding ambiguity: Report per-endpoint findings, not aggregates. Require representative endpoint/evidence.
- BOLA/IDOR detection limited to numeric IDs: VAmPI uses username-based paths. Implement mutation strategies per path parameter type.
- Injection testing ignoring path parameters: VAmPI has SQL injection on `/books/v1/{book_title}`. Test ALL parameter locations.
- Report output as attack vector: HTML report XSS vulnerability from unescaped response bodies. Apply escaping to ALL dynamic content.

## Implications for Roadmap

Based on research, the work divides into three natural phases aligned with feature dependencies:

### Phase 1: Foundation - Response Validation + Endpoint Classification
**Rationale:** These features have the highest FP elimination impact (18/18 documented FPs) with lowest implementation risk. They build on existing baseline capture and OpenAPI parsing without requiring new infrastructure. Must come first because all other validation depends on knowing (a) how the API communicates success/failure and (b) which endpoints are public vs protected.

**Delivers:**
- Response pattern learning with configurable fail indicators
- Public vs protected endpoint classification from OpenAPI security field + runtime validation
- Endpoint purpose detection via path/operationId heuristics
- Prerequisite checking in conditional tests
- Finding deduplication
- Evidence requirements enforcement

**Technologies:** deepdiff, jsonschema, difflib (stdlib), existing OpenAPI parser enhancement

**Addresses features:** TS-1, TS-2, TS-3, TS-4, TS-6, TS-7

**Avoids pitfalls:** #2 (overfitting - by building hierarchical pattern detection), #3 (regression - by requiring tests before fixes), #4 (inheritance bugs - by comprehensive edge case testing)

**Expected impact:** 31% FP rate → near 0% on VAmPI

### Phase 2: Intelligence - API Profile + Confidence Scoring
**Rationale:** Once response validation and classification work, integrate them into a unified API profile that persists between runs. Add confidence scoring so findings carry validation metadata. This phase builds the central data structure that makes subsequent intelligence features possible.

**Delivers:**
- API profile model (Pydantic) with auth scheme, response patterns, endpoint classifications
- Confidence levels (CONFIRMED/LIKELY/UNCERTAIN) on all findings
- Baseline comparison validation for differential testing
- Contextual finding suppression rules
- Profile persistence to JSON for reuse

**Technologies:** pydantic, enhanced profile construction from Phase 1 outputs

**Addresses features:** TS-5, DF-1, DF-4, DF-5

**Avoids pitfalls:** #1 (blind spec trust - by validating spec claims against profile), #6 (context-insensitive testing - by using profile for test filtering)

**Expected impact:** Findings carry validation metadata. Users can filter by confidence. Profile becomes central decision structure.

### Phase 3: Advanced Adaptive - Smart Test Selection
**Rationale:** With profile and confidence systems in place, add advanced intelligence: auto-detect auth schemes, fingerprint response formats, score test relevance, use multi-signal validation. This phase makes the tool competitive with commercial adaptive scanners.

**Delivers:**
- Auth scheme auto-detection (Bearer, API key, session, custom)
- Response format fingerprinting (RFC 9457, custom envelopes, XML/HTML)
- Test relevance scoring based on endpoint characteristics
- Multi-signal finding validation (response diff + error messages + timing + structure)
- Discovery safety controls (safe methods first, destructive endpoint flagging)

**Technologies:** openapi-core for security data providers, structlog for discovery audit trail

**Addresses features:** DF-2, DF-3, DF-6, DF-7

**Avoids pitfalls:** #5 (destructive discovery - by implementing safety controls), #2 (overfitting - by validating against diverse targets)

**Expected impact:** Tool adapts to APIs it has never seen before. Near-zero FPs across diverse architectures.

### Phase 4: Protocol Expansion (Future/v2)
**Rationale:** GraphQL and gRPC support are valuable but independent of REST testing improvements. Defer until core adaptive capabilities are proven.

**Delivers:**
- GraphQL introspection and schema-based testing
- gRPC reflection and service discovery
- httpx migration for HTTP/2 support

**Technologies:** graphql-core, grpcio-reflection, httpx

**Addresses features:** DF-8

**Defer reasoning:** Expanding to new protocols before fixing the core FP problem risks complexity without proven value. REST testing must be solid first.

### Phase Ordering Rationale

- **Dependencies drive order:** Response pattern learning (Phase 1) is foundation for all validation. API profile (Phase 2) integrates Phase 1 outputs and enables Phase 3 intelligence. Each phase builds on prior phases' outputs.

- **Risk-adjusted delivery:** Phase 1 has highest impact (18 FPs eliminated) with lowest risk (enhances existing code). Phase 2 adds infrastructure without changing test behavior. Phase 3 adds advanced features after validation is proven solid.

- **Pitfall avoidance:** Regression testing infrastructure must be built in Phase 1 before any fixes. Runtime validation of OpenAPI specs must happen in Phase 1 to prevent blind trust. Discovery safety controls must be in Phase 3 before any probing begins.

- **Independent work streams:** TS-6 (deduplication) and TS-7 (evidence requirements) are independent and can be done anytime in Phase 1. Moderate pitfall fixes (#8 BOLA, #9 injection, #10 XSS) can be sprinkled across phases as capacity allows.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 3 (Advanced Adaptive):** Response format fingerprinting and multi-signal validation are complex with limited documentation. May need `/gsd:research-phase` for RFC 9457 integration and weighted scoring algorithms.
- **Phase 4 (Protocol Expansion):** GraphQL introspection and gRPC reflection are niche domains. Definitely needs research if pursued.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Endpoint classification via OpenAPI security field is well-documented. Response pattern detection is standard DAST technique. JSON diffing is established pattern.
- **Phase 2 (Intelligence):** API profile modeling is straightforward Pydantic usage. Confidence scoring is classification problem with clear tiers.

**Codebase-specific considerations:**
All phases operate on existing codebase with documented issues (issues.md) and architectural analysis (.planning/codebase/). Research is already grounded in specific false positive patterns and code locations. Focus implementation on fixing documented issues rather than new research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core libraries (openapi-core, deepdiff, jsonschema, pydantic) verified via PyPI and official docs. Versions current as of Jan 2026. Adaptive patterns synthesized from multiple industry sources. |
| Features | HIGH | Codebase-verified FP patterns from issues.md. Table stakes features (TS-1 through TS-7) directly map to documented FPs. Differentiator features (DF-1 through DF-7) based on commercial tool analysis. |
| Architecture | MEDIUM | Architecture research was skipped, but component structure emerges clearly from features and stack. Existing codebase has hooks (baseline capture, OpenAPI parser, finding model) that adaptive layer will connect. |
| Pitfalls | HIGH | Project-specific pitfalls (issues.md #1-9) have file/line references. Industry pitfalls confirmed across multiple sources (PortSwigger, Invicti, Microsoft MSRC, Criteo engineering). |

**Overall confidence:** MEDIUM-HIGH

The stack and features research is solid (verified sources, codebase grounding). Architecture confidence is medium because ARCHITECTURE.md is missing, but the needed components are clear from feature dependencies. Pitfalls research is high confidence because it's grounded in documented project issues.

### Gaps to Address

**Python version compatibility:** jsonschema 4.26.0 requires Python >= 3.10. If project needs Python 3.9 support, must pin jsonschema to 4.23.x. Check project's minimum Python version requirement before Phase 1.

**OpenAPI spec quality assumption:** All phases assume OpenAPI spec exists and is reasonably accurate. If target APIs have no spec or severely broken specs, discovery layer must be more aggressive. May need fallback heuristics for spec-less scenarios.

**Cross-user testing infrastructure:** BOLA/IDOR detection (moderate pitfall #8) requires two user contexts (user A and user B credentials). Current codebase may not have multi-user credential handling. Verify and potentially build during Phase 1 or defer to Phase 3.

**Performance at scale:** Performance traps identified (O(N*M) discovery probing, baseline capture per scenario per endpoint). Not critical for VAmPI (small API), but may become issue on large APIs (100+ endpoints). Consider parallelization and caching optimizations in Phase 3.

**httpx migration timeline:** Deferred to Phase 4, but if HTTP/2 or gRPC becomes priority, migration touches every scenario (high risk). Existing PentestHttpClient abstraction makes migration feasible but still requires careful testing.

**Diverse target validation:** Research emphasizes testing against 5+ different API styles to avoid overfitting, but only VAmPI is currently available as test target. Need to identify additional test APIs (proper REST with status codes, 200-for-everything API, XML API, GraphQL API) during Phase 1 execution.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis**: `/home/abdulr7man/rb/issues.md` (9 documented FP/FN issue categories), `/home/abdulr7man/rb/.planning/codebase/CONCERNS.md` (systematic concern analysis), `/home/abdulr7man/rb/.planning/PROJECT.md` (requirements and constraints)
- **Official package registries**: openapi-core 0.22.0 on PyPI, deepdiff 8.6.1 on PyPI, jsonschema 4.26.0 on PyPI, pydantic 2.12.5 on PyPI, graphql-core 3.2.7 on GitHub, prance 25.4.8.0 on Libraries.io
- **Official documentation**: OpenAPI Security Specification (learn.openapis.org), RFC 7807/9457 Problem Details, Python difflib docs, gRPC reflection guide, GraphQL introspection spec
- **Current source code**: `api_pentest/scenarios/base_scenario.py` (baseline capture, is_success_status, log_finding), `api_pentest/core/openapi_parser.py` (security inheritance handling), `api_pentest/core/models.py` (Finding model)

### Secondary (MEDIUM confidence)
- **Industry research**: Wallarm (ML-based FP reduction techniques), DryRun Security (accuracy over FP reduction), PortSwigger (API testing, GraphQL security, DAST FP management), Cloudflare (ML API discovery), Levo.ai (API security tools landscape 2026), Pynt (context-aware testing), Cequence (adaptive testing), Traceable (BOLA deep dive)
- **Engineering blogs**: Microsoft MSRC (scaling DAST, OpenAPI spec generation challenges), Criteo (OpenAPI spec drift between spec and live APIs), StackHawk (spec-driven scanning), APIsec (shadow API discovery)
- **Commercial tool analysis**: Pynt, Levo.ai, Cequence, Traceable.ai (feature comparison for context-aware testing, behavioral analysis, intelligent test plans)

### Tertiary (LOW confidence, flagged for validation)
- **Academic research**: Active Behavioral Validation (arXiv 2508.12584v1 - 93% FP reduction claim), HTTP Response Fingerprinting (arXiv 2404.00056v1 - ML-based classification), USENIX Security 2022 (ML overfitting in security domain)
- **Stack decisions**: Rule engine assessment (GoRules, pyKnow) based on general knowledge not benchmark data, structlog version not deeply verified, async vs sync performance claims not specific to security scanning workloads

---
*Research completed: 2026-02-04*
*Ready for roadmap: yes*
