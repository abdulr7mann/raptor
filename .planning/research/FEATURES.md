# Feature Research: Adaptive API Security Testing

**Domain:** Adaptive API security testing (pentest toolkit)
**Researched:** 2026-02-04
**Confidence:** HIGH (codebase-verified FP patterns) / MEDIUM (ecosystem techniques from multiple sources)

## Context

This research focuses exclusively on **adaptive/learning features** needed to transform a static API scanner into an intelligent pentest toolkit. Basic security tests (IDOR, injection, rate limiting, etc.) are already implemented across 13 OWASP scenarios. The problem is not missing tests -- it is a 31% false positive rate caused by static assumptions that ignore API-specific behavior.

**The core question:** What features distinguish an adaptive security tool from a static scanner?

**Answer from research:** Three capability layers separate them:
1. **Discovery** -- Learning what the API actually is before testing it
2. **Contextual Validation** -- Verifying findings against observed behavior, not assumptions
3. **Intelligent Selection** -- Running only relevant tests based on discovered characteristics

---

## Feature Landscape

### Table Stakes (Must Have for "Adaptive" -- Without These, It Is Still a Static Scanner)

These features are the minimum bar. Without them, the tool cannot claim to adapt to different APIs. Every feature here directly eliminates documented false positive patterns from `issues.md`.

| # | Feature | Why Required | Eliminates FP Pattern | Complexity | Notes |
|---|---------|--------------|----------------------|------------|-------|
| TS-1 | **Response Pattern Learning** | APIs return success/failure differently. HTTP 200 + `{"status":"fail"}` is a rejection, not a success. Tool must learn each API's success/failure indicators from baseline responses before testing. | **FP-2** (issues.md #3): 10 false positives from treating HTTP 200 + fail body as success (S06, S09, S13 scenarios) | MEDIUM | Analyze baseline responses to build a response pattern dictionary. Check body-level indicators (`"status":"fail"`, `"error":`, `"success":false`) alongside HTTP status. The existing `capture_baseline()` method in `base_scenario.py:95-110` already makes baseline requests but only caches raw evidence without analyzing patterns. |
| TS-2 | **Endpoint Classification (Public vs Protected)** | Tests must know which endpoints require auth. Flagging a public endpoint for "accepting malformed tokens" is nonsensical -- there is no auth to malform. | **FP-3** (issues.md #4): 4 false positives from testing auth on public endpoints (S07 malformed token on `/`, `/books/v1`, `/createdb`; S06 priv-esc on `/login`) | MEDIUM | Two sources: (1) OpenAPI spec `security` field -- already parsed by `openapi_parser.py:145-161` into `tags` with `"public-no-auth"`, `security_schemes` list. (2) Heuristic path pattern matching for login/register/signup/health endpoints. The parser already does both, but scenarios do not use this information -- they iterate `self.endpoints` without filtering. |
| TS-3 | **Endpoint Purpose Detection** | Login endpoints are supposed to return auth tokens. Register endpoints create users. Health endpoints return status. Testing these the same way as business endpoints creates false findings. | **FP-4** (issues.md #5): 1 false positive from flagging `auth_token` in login response as data exposure (S08). Also connects to **FP-3** (login flagged for priv-esc). | LOW | Path-based heuristics: `/login`, `/auth`, `/register`, `/signup`, `/token`, `/health`, `/status`, `/createdb`, `/reset`. Also check OpenAPI `operationId` and `summary` fields for semantic intent. Low complexity because it is pattern matching, not ML. |
| TS-4 | **Prerequisite-Aware Test Execution** | Some tests are prerequisites for others. If no rate limiting exists, bypass tests are meaningless. If an endpoint is public, auth tests are meaningless. Tests must check preconditions before running. | **FP-5** (issues.md #6): 4 false positives from running rate limit bypass tests when no rate limiting was detected (S02 X-Forwarded-For/X-Real-IP bypass findings). | LOW | Conditional execution: check result of detection test before running bypass test. S02 already runs burst test first (`_test_rate_limit_burst`), but unconditionally proceeds to `_test_header_bypass()`. Fix is adding state tracking between test cases within a scenario. |
| TS-5 | **Confidence-Level Findings** | Findings must be classified by validation certainty: CONFIRMED (exploit reproduced), LIKELY (strong indicators), UNCERTAIN (needs manual review). Static tools report everything at the same confidence, which is misleading. | Not a specific FP pattern, but addresses the systemic problem: users cannot distinguish real vulnerabilities from noise without manual triage of all 58 findings. | MEDIUM | Add `confidence` field to Finding model (currently not present in `models.py:145-168`). Confidence determined by: (a) whether response indicates actual success vs failure, (b) whether baseline comparison shows behavioral change, (c) whether multiple indicators agree. |
| TS-6 | **Finding Deduplication** | Same finding on same endpoint must not appear twice in reports. Duplicate findings are noise. | **DQ-1** (issues.md #9): Duplicate "Rate limit bypass via X-Forwarded-For" findings. | LOW | Signature-based dedup: hash of `(title, endpoint, scenario_id)`. Check before appending to findings list. Can be added to `log_finding()` in `base_scenario.py:132-152` or to `ReportGenerator`. |
| TS-7 | **Evidence-Required Findings** | Every finding must include HTTP evidence (request + response). Findings without evidence cannot be validated by the user. | **FP-1** (issues.md #1, #2): 9 findings missing endpoint field, 15 findings missing evidence. Aggregate findings in S01, S02, S05 report vulnerabilities without proof. | LOW | Enforce at `log_finding()` level: warn or require `evidence` and `endpoint` parameters. For aggregate findings, capture representative evidence from first/last affected endpoint. |

### Differentiators (Advanced Features That Make It Truly Intelligent)

These features go beyond eliminating the current FP patterns. They are what commercial adaptive tools (Pynt, Cequence, Traceable) offer that distinguish them from static DAST scanners. Not required for the immediate FP-reduction milestone, but valuable for the product's competitive position.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| DF-1 | **API Profile Construction** | Build a structured profile of the API before testing: auth scheme, response patterns, endpoint classification, error format, API architecture type. All subsequent test decisions reference the profile rather than hardcoded assumptions. | HIGH | This is the central data structure that TS-1 through TS-4 feed into. The profile should be a first-class object passed to all scenarios during `setup()`. It captures: auth type (Bearer/API key/session/none), response success pattern (status code vs body field), error response format (structured JSON vs plain text), endpoint count by classification, detected capabilities (rate limiting, pagination, CORS). Research from Cloudflare and Wallarm confirms this is the standard approach in ML-driven API security. |
| DF-2 | **Auth Scheme Auto-Detection** | Probe the API to automatically detect which authentication mechanism it uses, without requiring manual configuration. Try Bearer token, API key in header, API key in query, session cookie, and custom headers against baseline endpoints. | MEDIUM | Send requests with and without credentials, observe 401/403 patterns. Check response headers for `WWW-Authenticate`. Parse OpenAPI `securitySchemes` for declared auth type. Fall back to probing if no spec available. This is table stakes in commercial tools (Levo, Cequence, Wallarm all do this), but a differentiator for a pentest CLI tool. |
| DF-3 | **Response Format Fingerprinting** | Detect whether the API uses structured error responses (RFC 7807/9457 Problem Details, custom JSON envelopes, XML faults) vs raw HTTP status codes. Use this to calibrate how success/failure is determined for each endpoint. | MEDIUM | Extends TS-1 beyond hardcoded patterns. Instead of checking for `"status":"fail"`, learn the API's specific error envelope structure from baseline error responses (send intentionally bad request, observe error format). APIs using RFC 9457 will have `type`, `title`, `status`, `detail` fields. APIs using custom envelopes will have `success`/`error`/`status` fields. Some APIs use different formats for different endpoints. |
| DF-4 | **Baseline Comparison Validation** | For every test, compare the test response against the baseline response. If the response is identical to normal behavior, the "vulnerability" is likely a false positive -- the API handled the attack the same way it handles normal requests. | MEDIUM | Extends existing `capture_baseline()` in `base_scenario.py:95-110`. Currently baselines are captured but not systematically compared. Add structural comparison: status code delta, body structure similarity, response time deviation. A test that produces identical output to baseline is less likely to be a real finding. Academic research (EvoMaster) confirms this "differential testing" approach is effective. |
| DF-5 | **Contextual Finding Suppression** | Suppress findings that are expected behavior for the endpoint's purpose. Login returning a token is not data exposure. Register creating a user is not privilege escalation. Health endpoint being public is not missing auth. Build suppression rules from endpoint classification. | LOW | Rules engine that cross-references finding type against endpoint purpose. Example rules: (1) "data exposure" findings on auth endpoints: suppress if exposed field is `token`/`session`/`jwt`. (2) "missing auth" findings on public-tagged endpoints: suppress always. (3) "privilege escalation" on login/register: suppress always. This is essentially formalizing the manual triage that issues.md performed. |
| DF-6 | **Test Relevance Scoring** | Score each test's relevance to each endpoint before execution. SQL injection on a path parameter is more relevant than SQL injection in a query param that is a boolean flag. IDOR is more relevant on endpoints with user-specific path params than on list endpoints. | HIGH | Requires understanding parameter semantics from OpenAPI schema (type, format, name patterns). Score matrix: test type x endpoint characteristics = relevance score. Skip tests below threshold. This is what Pynt calls "context-aware testing" and what Invicti calls "intelligent test case generation." |
| DF-7 | **Multi-Signal Finding Validation** | Validate findings using multiple independent signals before reporting. For an injection finding: (1) Did the response differ from baseline? (2) Did the response contain error messages suggesting injection succeeded? (3) Did response time change (timing-based detection)? (4) Did the response body structure change? Require 2+ signals for CONFIRMED status. | HIGH | Combines DF-4 (baseline comparison) with response content analysis and timing analysis. Each signal is a "voter" in a weighted voting system (Wallarm's approach). Reduces false positives from any single indicator being misleading. The 93% FP reduction cited in the behavioral validation research used a similar multi-signal approach. |
| DF-8 | **GraphQL Schema Introspection** | When testing GraphQL APIs, automatically run introspection queries to discover the full schema (types, queries, mutations, subscriptions). Generate test endpoints from the schema. Detect if introspection is enabled (security finding) or disabled (use Clairvoyance-style suggestion probing). | HIGH | Requires new parser module for GraphQL. Introspection query is standardized (`__schema` query). Parse result into Endpoint objects for each query/mutation. GraphQL has unique attack surfaces: batching attacks, deep nesting/DoS, field-level authorization bypass. OWASP Testing Guide and PortSwigger both document the standard introspection approach. |

### Anti-Features (Things to Deliberately Avoid)

These are features that seem valuable but would reduce accuracy, increase complexity disproportionately, or move the tool in the wrong direction. Each is a deliberate design decision.

| # | Anti-Feature | Why It Seems Good | Why It Reduces Accuracy | What to Do Instead |
|---|-------------|-------------------|------------------------|-------------------|
| AF-1 | **AI/ML-Based Vulnerability Detection** | Commercial tools market ML-powered detection. Sounds cutting-edge. | ML models require massive training datasets of vulnerability patterns. Without them, the model produces unpredictable results. Pentest tools need deterministic, explainable findings -- "the model thinks this might be vulnerable" is not actionable evidence. PROJECT.md explicitly excludes "AI-driven test generation" as out of scope. | Use deterministic heuristics that are explainable and debuggable. Pattern matching for response analysis, rule-based endpoint classification, conditional test logic. These are reliable, testable, and produce reproducible results. |
| AF-2 | **Aggressive Payload Generation** | More payloads = more coverage. Generate thousands of injection variants. | Volume creates noise. Each payload that triggers a false positive wastes user time. The current tool already has adequate payloads across 13 scenarios -- the problem is not payload coverage but result validation. More payloads without better validation amplifies the FP problem. | Focus on validating results from existing payloads rather than generating more. Better to have 10 payloads with accurate validation than 1000 payloads with 31% false positive rate. |
| AF-3 | **Real-Time Learning During Scan** | Tool learns and adapts as it scans, updating its model with each request. | Introduces non-deterministic behavior. The same API scanned twice might produce different results depending on request ordering and learning state. Makes debugging impossible and reports non-reproducible. | Learn during a dedicated **discovery phase** that runs before testing. Lock the API profile. Testing phase uses the frozen profile. This produces deterministic, reproducible results. |
| AF-4 | **Automated Exploitation/Weaponization** | Prove vulnerabilities are real by exploiting them. | Crosses the line from testing to attacking. Can cause damage to target systems (data corruption, service disruption). Liability concerns. PROJECT.md explicitly states: "Discovery and reporting only, no active exploit execution beyond proof-of-concept." | Provide sufficient evidence (request/response pairs showing the vulnerability) for manual verification. Let the pentester decide whether to exploit. |
| AF-5 | **Scan Everything by Default** | Run all 13 scenarios against all endpoints for maximum coverage. | This is the current behavior and the root cause of 31% FP rate. SQL injection tests on health endpoints, privilege escalation on login, rate limit bypass without rate limiting -- all noise. | Default to intelligent selection: only run tests relevant to each endpoint's classification and purpose. Allow override flag (`--all-tests`) for exhaustive scanning. |
| AF-6 | **Suppressing All LOW Confidence Findings** | Only show CONFIRMED findings to eliminate all noise. | Hides real vulnerabilities that could not be automatically validated. Some vulnerabilities (business logic, complex auth bypasses) cannot be confirmed automatically but are critical. The DryRun Security research emphasizes: missing real vulnerabilities (false negatives) is far more dangerous than occasional false positives. | Report all findings but with clear confidence levels. Let users filter by confidence. Default report shows CONFIRMED + LIKELY. UNCERTAIN available on request. |
| AF-7 | **Network-Level Discovery** | Port scan, DNS enumeration, TLS analysis to discover more about the target. | Scope creep. The tool tests APIs, not infrastructure. Network scanning is a different domain with different tools (nmap, testssl.sh). Adding it dilutes focus and increases complexity without improving API-level accuracy. PROJECT.md explicitly excludes network-level testing. | Stay focused on API-layer testing. Accept base URL as input. Do not attempt to discover services, ports, or infrastructure. |

---

## Feature Dependencies

```
[TS-1] Response Pattern Learning
    |
    v
[DF-3] Response Format Fingerprinting ----enhances----> [TS-1]
    |
    v
[DF-1] API Profile Construction <---- feeds into ---- [TS-2] Endpoint Classification
    ^                                                       |
    |                                                       v
    +---- feeds into ---- [TS-3] Endpoint Purpose Detection
    |
    v
[DF-4] Baseline Comparison Validation
    |
    v
[DF-7] Multi-Signal Finding Validation <---- uses ---- [TS-5] Confidence Levels
    |
    v
[DF-5] Contextual Finding Suppression <---- uses ---- [TS-3] Endpoint Purpose

[TS-4] Prerequisite-Aware Execution (independent, can be done anytime)

[TS-6] Finding Deduplication (independent, can be done anytime)

[TS-7] Evidence-Required Findings (independent, can be done anytime)

[DF-2] Auth Scheme Detection ---> feeds into ---> [DF-1] API Profile

[DF-6] Test Relevance Scoring <---- uses ---- [DF-1] API Profile

[DF-8] GraphQL Introspection (independent, new parser path)
```

### Dependency Notes

- **TS-1 (Response Pattern Learning) is the foundation.** Without knowing how the API communicates success/failure, all other validation is unreliable. This must come first.
- **TS-2 (Endpoint Classification) enables TS-3 and TS-4.** Must know which endpoints are public before skipping auth tests or detecting endpoint purpose.
- **DF-1 (API Profile) is the integration point.** Individual discovery features (TS-1, TS-2, TS-3, DF-2, DF-3) all write to the profile. All test execution features (TS-4, DF-5, DF-6) read from the profile.
- **TS-5 (Confidence Levels) is cross-cutting.** Affects how all findings are reported. Should be added to the Finding model early so all scenarios can use it.
- **TS-6 and TS-7 are independent.** Can be implemented at any time without affecting other features. Low risk, high immediate value.
- **DF-8 (GraphQL) is a separate track.** Does not depend on or affect REST testing features. Can be developed in parallel or deferred.

---

## Milestone Prioritization

### Phase 1: Foundation -- Response Validation + Endpoint Classification

Eliminate the documented FP patterns with the minimum viable adaptive features.

- [x] **TS-1** Response Pattern Learning -- Eliminates 10 FPs from HTTP 200 + fail body
- [x] **TS-2** Endpoint Classification -- Eliminates 4 FPs from testing auth on public endpoints
- [x] **TS-3** Endpoint Purpose Detection -- Eliminates 1 FP from login token flagged as exposure
- [x] **TS-4** Prerequisite-Aware Execution -- Eliminates 4 FPs from bypass tests without precondition
- [x] **TS-6** Finding Deduplication -- Eliminates duplicate findings in reports
- [x] **TS-7** Evidence-Required Findings -- Ensures all findings have endpoint + evidence

**Expected impact:** Eliminates 18/18 documented false positives (31% -> near 0% on VAmPI).

### Phase 2: Confidence + Profile -- Making Findings Trustworthy

Build the confidence scoring system and integrate discovery features into a unified API profile.

- [ ] **TS-5** Confidence-Level Findings -- CONFIRMED/LIKELY/UNCERTAIN classification
- [ ] **DF-1** API Profile Construction -- Central profile object for all adaptive decisions
- [ ] **DF-4** Baseline Comparison Validation -- Differential testing for finding verification
- [ ] **DF-5** Contextual Finding Suppression -- Rules engine for expected-behavior suppression

**Expected impact:** Findings carry validation metadata. Users can filter by confidence. Profile becomes the central decision structure.

### Phase 3: Intelligence -- Smart Test Selection

Make the tool actively intelligent about what tests to run and how to validate results.

- [ ] **DF-2** Auth Scheme Auto-Detection -- No manual auth configuration needed
- [ ] **DF-3** Response Format Fingerprinting -- Calibrate validation per API's error format
- [ ] **DF-6** Test Relevance Scoring -- Skip irrelevant tests, focus on high-value targets
- [ ] **DF-7** Multi-Signal Finding Validation -- Multiple independent signals for confirmation

**Expected impact:** Tool adapts to APIs it has never seen before. Near-zero false positives across diverse API architectures.

### Future Consideration (v2+)

- [ ] **DF-8** GraphQL Schema Introspection -- Expand to GraphQL APIs
- [ ] gRPC reflection-based discovery -- Expand to gRPC APIs
- [ ] Cross-endpoint workflow testing -- Multi-step business logic validation
- [ ] Finding trend analysis -- Track FP rates across runs for continuous improvement

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | FP Elimination | Priority |
|---------|-----------|-------------------|---------------|----------|
| TS-1 Response Pattern Learning | HIGH | MEDIUM | 10 FPs | P1 |
| TS-2 Endpoint Classification | HIGH | MEDIUM | 4 FPs | P1 |
| TS-3 Endpoint Purpose Detection | HIGH | LOW | 1+ FPs | P1 |
| TS-4 Prerequisite-Aware Execution | HIGH | LOW | 4 FPs | P1 |
| TS-5 Confidence Levels | HIGH | MEDIUM | Systemic | P1 |
| TS-6 Finding Deduplication | MEDIUM | LOW | Duplicates | P1 |
| TS-7 Evidence-Required Findings | MEDIUM | LOW | 15+ findings | P1 |
| DF-1 API Profile Construction | HIGH | HIGH | Systemic | P2 |
| DF-4 Baseline Comparison | HIGH | MEDIUM | Systemic | P2 |
| DF-5 Contextual Suppression | MEDIUM | LOW | Systemic | P2 |
| DF-2 Auth Scheme Detection | MEDIUM | MEDIUM | N/A | P3 |
| DF-3 Response Format Fingerprinting | MEDIUM | MEDIUM | Systemic | P3 |
| DF-6 Test Relevance Scoring | HIGH | HIGH | Systemic | P3 |
| DF-7 Multi-Signal Validation | HIGH | HIGH | Systemic | P3 |
| DF-8 GraphQL Introspection | MEDIUM | HIGH | N/A | P4 |

**Priority key:**
- P1: Must have for adaptive milestone (eliminates documented FPs)
- P2: Should have, makes findings trustworthy
- P3: Makes tool truly intelligent, competitive with commercial tools
- P4: Future expansion to other API types

---

## Competitor Feature Analysis

| Feature | Static Scanners (ZAP, Nikto) | Commercial Adaptive (Pynt, Cequence) | Our Approach |
|---------|------------------------------|--------------------------------------|-------------|
| Response pattern learning | None -- HTTP status only | ML-based behavioral analysis | Deterministic pattern matching from baselines (TS-1) |
| Endpoint classification | None -- test all equally | Auto-discovery + ML classification | OpenAPI `security` field + path heuristics (TS-2, TS-3) |
| Prerequisite checking | None -- run everything | Intelligent test plans | State tracking between test cases (TS-4) |
| Confidence scoring | None or binary pass/fail | CERTAIN/UNCERTAIN with validation | Three-tier: CONFIRMED/LIKELY/UNCERTAIN (TS-5) |
| Finding deduplication | Basic (ZAP has some) | Full cross-scan dedup | Signature-based dedup (TS-6) |
| API profile | None | Full behavioral profile | Structured profile object (DF-1) |
| Auth detection | Manual configuration | Automatic probing | Spec-based + fallback probing (DF-2) |
| Business logic testing | None | Context-aware (Pynt) | Contextual suppression rules (DF-5) |
| Multi-signal validation | None | AI-driven validation agents | Weighted voting from multiple indicators (DF-7) |
| GraphQL support | Limited (ZAP has basic) | Full introspection + testing | Introspection-based endpoint generation (DF-8) |

**Our competitive position:** We occupy a unique niche between static open-source scanners (accurate but dumb) and commercial platforms (smart but expensive/opaque). Our approach is deterministic and explainable (no ML black box), uses spec-based intelligence where available, and falls back to heuristics. This makes results reproducible and debuggable -- critical for pentest reporting where findings must be defensible.

---

## Sources

**Codebase analysis (PRIMARY -- HIGH confidence):**
- `/home/abdulr7man/rb/issues.md` -- Documented false positive patterns with root causes
- `/home/abdulr7man/rb/.planning/codebase/CONCERNS.md` -- Systematic codebase concern analysis
- `/home/abdulr7man/rb/.planning/PROJECT.md` -- Project requirements and constraints
- `/home/abdulr7man/rb/api_pentest/core/openapi_parser.py` -- Existing security field parsing
- `/home/abdulr7man/rb/api_pentest/scenarios/base_scenario.py` -- Existing baseline/validation methods
- `/home/abdulr7man/rb/api_pentest/core/models.py` -- Current data model structure

**OpenAPI specification (HIGH confidence):**
- [OpenAPI Security Documentation](https://learn.openapis.org/specification/security.html) -- Authoritative source for security field semantics, global vs per-operation security, empty array = public
- [RFC 7807/9457](https://datatracker.ietf.org/doc/html/rfc7807) -- Problem Details for HTTP APIs standard error format

**Industry landscape (MEDIUM confidence -- multiple sources agree):**
- [Wallarm: Reducing False Positives with ML](https://lab.wallarm.com/reducing-false-positives-api-security-advanced-techniques-machine-learning/) -- Weighted voting, behavioral baseline, contextual evaluation techniques
- [DryRun Security: Accuracy Over FP Reduction](https://www.dryrun.security/blog/false-positives-reduction-is-a-red-herring--accuracy-is-king-in-application-security) -- False negatives more dangerous than false positives, contextual analysis
- [PortSwigger: API Testing](https://portswigger.net/web-security/api-testing) -- Systematic API interaction, response analysis, hidden parameter discovery
- [Cloudflare: ML API Discovery](https://blog.cloudflare.com/ml-api-discovery-and-schema-learning/) -- ML-powered endpoint classification and schema learning
- [PortSwigger: GraphQL Security](https://portswigger.net/web-security/graphql) -- Introspection testing, InQL scanner approach

**Commercial tool approaches (MEDIUM confidence):**
- [Pynt](https://www.pynt.io/) -- Context-aware-first, business logic vulnerability detection
- [Levo.ai: API Security Tools 2026](https://www.levo.ai/resources/blogs/top-10-api-security-testing-tools-2026) -- Landscape of API security testing tools
- [Pentest-Tools: Finding Validation](https://support.pentest-tools.com/manually-validate-findings) -- CERTAIN/UNCERTAIN classification approach

**Academic/research (LOW-MEDIUM confidence):**
- [Active Behavioral Validation (arXiv)](https://arxiv.org/html/2508.12584v1) -- 93% FP reduction with active behavioral analysis
- [HTTP Response Fingerprinting (arXiv)](https://arxiv.org/html/2404.00056v1) -- ML-based response classification, 0.96 F1 score

---
*Feature research for: Adaptive API Security Testing*
*Researched: 2026-02-04*
