# Pitfalls Research: Adaptive API Security Testing

**Domain:** Adaptive API pentest toolkit (discovery + OpenAPI learning + intelligent validation)
**Researched:** 2026-02-04
**Confidence:** HIGH (project-specific issues from issues.md) / MEDIUM (ecosystem patterns from web research)

---

## Critical Pitfalls

Mistakes that cause rewrites, destroy accuracy, or undermine the core value proposition (eliminating the 31% FP rate).

### Pitfall 1: Blind Trust in OpenAPI Specifications

**What goes wrong:**
The scanner treats OpenAPI spec content as ground truth and bases all security decisions on it. But specs are frequently incomplete, outdated, or wrong. Missing `security` fields, undocumented endpoints, wrong parameter types, absent response schemas, and stale server URLs all lead to incorrect test targeting and classification. The scanner either skips real vulnerabilities (false negatives from missing endpoints) or misclassifies endpoint security requirements (false positives from wrong security metadata).

**Why it happens:**
The "spec-first" approach feels rigorous, and OpenAPI is a structured machine-readable format that inspires false confidence. Developers assume "if it's in the spec, it's correct" and "if it's not in the spec, it doesn't exist." In reality, the Criteo engineering team documented systematic drift between specs and live APIs. Microsoft's DAST scaling effort found that even LLM-generated specs from source code were non-deterministic and incomplete. The OpenAPI specification itself allows empty objects and undefined security schemas, which different tools resolve differently.

**How to avoid:**
1. Treat the spec as a hypothesis, not truth. Use it as a starting point, then verify via discovery probes.
2. Implement a "spec trust score" -- compare what the spec claims with what the live API actually does during the discovery phase. Track divergence metrics.
3. For security classification specifically: probe each endpoint both with and without authentication during discovery, regardless of what the spec says. If an endpoint the spec marks as `security: []` (public) actually returns 401 without a token, flag the discrepancy and treat it as protected.
4. Never rely solely on the spec's `security` field for the public vs. protected endpoint distinction. Cross-validate with runtime behavior.

**Warning signs:**
- Scanner skips endpoints not in the spec (shadow API blind spot)
- Security classification changes drastically between different spec versions
- Zero false positives on a target where the spec is known to be incomplete -- suspiciously clean results mean missed coverage
- `security` field missing at both global and operation level (ambiguous, not definitively "public")

**Phase to address:**
Discovery/Learning phase. The API profile builder must validate spec claims against live behavior before any test execution begins.

**Relevance to issues.md:**
Directly relates to Issue #4 (FP: Public endpoints flagged for accepting no auth). The current code does not use the OpenAPI `security` field at all for endpoint classification. The fix must use it, but must not trust it blindly -- runtime validation is essential.

---

### Pitfall 2: Overfitting Response Pattern Detection to a Single Target

**What goes wrong:**
The adaptive response pattern learner (DISC-02 from PROJECT.md) learns success/failure indicators from one API target, then those patterns fail catastrophically on the next target. A scanner tuned on VAmPI learns that `{"status": "fail"}` means failure, but another API uses `{"error": true, "code": "VALIDATION_FAILED"}` or returns HTML error pages or uses non-JSON responses entirely. The learned patterns become hardcoded assumptions wearing an "adaptive" mask.

**Why it happens:**
This is the security-domain equivalent of ML overfitting (documented extensively in the USENIX Security 2022 "Dos and Don'ts of ML in Security" paper). The scanner develops a model from limited training data (one API) and that model doesn't generalize. Response patterns vary enormously across APIs: some use HTTP status codes correctly, some always return 200, some use XML, some use custom error envelopes, some use plain text. There is no universal "application-level failure" signature.

**How to avoid:**
1. Build the response pattern detector as a ranked hierarchy of checks, not a single pattern match:
   - Check 1: HTTP status code (universal, always available)
   - Check 2: Content-Type-appropriate body parsing (JSON vs XML vs HTML vs plain text)
   - Check 3: Structural pattern detection (look for `error`, `status`, `success`, `message` keys in JSON, or error-class elements in XML/HTML)
   - Check 4: Semantic value detection (is the `status` field value negative? is `success` false?)
2. During the discovery phase, send known-good and known-bad requests to establish baseline patterns for THIS specific API. Don't carry over patterns from previous targets.
3. Make the failure indicator list configurable and extensible, not hardcoded.
4. Test the pattern detector against at least 5 different API response styles before shipping (VAmPI, a REST API with proper status codes, a "200-for-everything" API, an XML API, an API that returns HTML errors).

**Warning signs:**
- The `is_true_success()` helper has hardcoded string patterns like `'"status": "fail"'`
- Response pattern detection works perfectly on VAmPI but fails on any other target
- No configuration option exists to customize failure indicators per target
- The scanner cannot detect failures in non-JSON responses

**Phase to address:**
Discovery/Learning phase first (build generalizable pattern detection), then Validation phase (verify patterns work per-target).

**Relevance to issues.md:**
Directly relates to Issue #3 (FP: `is_success_status()` ignores response body). The proposed fix in issues.md -- a hardcoded list of fail indicators -- is itself a pitfall. It solves the VAmPI case but will break on other APIs. The fix must be adaptive, not a new set of hardcoded strings.

---

### Pitfall 3: Fixing Old False Positives While Introducing New Ones

**What goes wrong:**
In the process of eliminating the 31% FP rate (18/58 findings), new validation logic introduces new classes of false positives or, worse, false negatives. For example: adding body-content checking for application-level failures (to fix Issue #3) may cause the scanner to suppress legitimate vulnerability findings when an API happens to include the word "error" in a valid response body. Or: excluding "public" endpoints from auth tests (to fix Issue #4) may miss genuinely unprotected endpoints that should require auth but don't.

**Why it happens:**
Each FP fix is a new decision rule. New decision rules have their own edge cases. Without regression testing against known good/bad findings, fixes are validated only against the specific FP they were designed to eliminate, not against the full finding corpus. The PortSwigger documentation on DAST false positive management specifically warns about this: fixes applied to suppress one class of noise can blind the scanner to real vulnerabilities. The DAST community calls this "whack-a-mole" false positive management.

**How to avoid:**
1. Before fixing any FP, establish a ground truth test suite: a set of known true-positive findings and known false-positive findings for VAmPI (and ideally other targets). Every fix must pass both sides: it must eliminate the targeted FP AND not suppress any known TP.
2. Implement regression tests for every FP fix. Each test should include:
   - The specific finding that was a false positive (must no longer be reported)
   - At least one related finding that IS a true positive (must still be reported)
3. Track a "finding stability metric": after each change, run the full test suite and compare the finding set. Any unexpected finding appearing or disappearing triggers review.
4. Use confidence scoring (RPT-05 from PROJECT.md) to downrank borderline findings rather than suppressing them entirely. This preserves signal while reducing noise.

**Warning signs:**
- A fix eliminates an FP but the total finding count drops by more than the expected number (legitimate findings were suppressed too)
- No unit tests exist for finding validation logic
- The `is_true_success()` method has no tests, or only tests against VAmPI response patterns
- Finding count changes unexpectedly between runs without code changes

**Phase to address:**
Must be addressed from the very first fix phase. Regression test infrastructure should be built BEFORE any FP fixes are applied.

**Relevance to issues.md:**
This is a meta-pitfall about fixing all 9 issue categories. Every fix in issues.md risks this. The proposed `is_true_success()` helper (Issue #3), the public endpoint exclusion (Issue #4), and the login endpoint whitelist (Issue #5) all have potential to suppress true positives if implemented without regression testing.

---

### Pitfall 4: OpenAPI Security Inheritance Misinterpretation

**What goes wrong:**
The scanner misinterprets OpenAPI security inheritance rules, leading to incorrect public vs. protected endpoint classification. The OpenAPI specification has subtle and frequently misunderstood inheritance semantics:
- Operation-level `security` **completely replaces** (not merges with) global security
- An empty `security: []` at operation level explicitly marks the endpoint as public (overrides global auth)
- A missing `security` field at operation level means "inherit from global"
- An empty `security: []` at global level means "no global auth required" (but operations can still define their own)
- Undefined security schemas referenced in `security` requirements may silently allow unauthenticated access in some implementations

**Why it happens:**
The OpenAPI security model has edge cases that even the official documentation doesn't fully clarify (per the official OpenAPI learning docs). Developers commonly confuse "missing field" (inherit from global) with "empty array" (explicitly no auth). The existing `openapi_parser.py` already handles `explicitly_public` detection (line 150-151), but if the parser misinterprets one of these edge cases, every downstream security test inherits the error.

**How to avoid:**
1. Implement explicit test cases for every security inheritance scenario:
   - Global security defined, operation security missing (should inherit global)
   - Global security defined, operation security empty `[]` (should be public)
   - Global security missing, operation security defined (should use operation security)
   - Global security missing, operation security missing (ambiguous -- should default to "unknown, probe needed")
   - Security requirement references undefined scheme (should warn and flag for manual review)
2. When the classification is ambiguous (no security defined anywhere), do NOT default to "public." Default to "unknown" and verify with runtime probing.
3. Add a "security_source" metadata field to each endpoint: "spec-global", "spec-operation", "spec-explicit-public", "spec-ambiguous", "runtime-verified". This makes the reasoning traceable.

**Warning signs:**
- Parser treats "no security field" the same as `security: []`
- No test cases for security inheritance edge cases
- All endpoints classified as either "public" or "protected" with no "unknown" category
- Endpoint security classification changes when a global security field is added to or removed from the spec

**Phase to address:**
Discovery/Learning phase -- specifically the OpenAPI parser enhancement and the API profile builder.

**Relevance to issues.md:**
Directly enables the fix for Issue #4 (FP: Public endpoints flagged for accepting no auth). The current `openapi_parser.py` already detects `explicitly_public` on line 151, but this logic must be verified against all inheritance edge cases before being used as the basis for test filtering.

---

### Pitfall 5: Discovery Probing That Damages the Target

**What goes wrong:**
The adaptive discovery phase (DISC-01 through DISC-05) sends probe requests to understand the API. These probes can cause real damage: creating test records, triggering email notifications, modifying state, exhausting rate limits, or -- as documented in Issue #7c for VAmPI -- resetting the entire database via `/createdb`. The scanner breaks the very system it's trying to test.

**Why it happens:**
Discovery probes need to test authentication, response patterns, and endpoint behavior, which often requires sending actual requests with various payloads. Without awareness of which operations are safe (GET/HEAD/OPTIONS) vs. unsafe (POST/PUT/DELETE), the scanner may blindly probe all endpoints with equal aggression. The VAmPI `/createdb` endpoint that resets the database is a direct example: the scanner probes it and destroys all test data before tests even begin.

**How to avoid:**
1. Implement a "safe discovery" mode that limits initial probing to safe HTTP methods (GET, HEAD, OPTIONS) and read-only endpoints.
2. Before probing any mutable endpoint (POST/PUT/DELETE), check the OpenAPI spec for operation metadata: descriptions containing "create", "delete", "reset", "initialize" should be flagged as potentially destructive.
3. Sort discovery probing by method safety: GET endpoints first, then PUT/PATCH (idempotent), then POST/DELETE (potentially destructive) last.
4. For destructive-looking endpoints, use the spec's parameter schemas to send intentionally invalid payloads that trigger validation errors (revealing response patterns) without actually executing the operation.
5. Implement a `--safe-discovery` flag (default on) and a `--destructive-discovery` flag (default off, requires explicit opt-in).

**Warning signs:**
- Test data disappears during the discovery phase
- Rate limit counters get exhausted before actual security tests run
- Discovery probes trigger side effects (emails, notifications, webhook calls)
- POST/DELETE endpoints are probed with valid-looking payloads during discovery

**Phase to address:**
Discovery phase -- must be the first thing built, with safety controls before any probing begins.

**Relevance to issues.md:**
Directly relates to Issue #7c (FN: /createdb resets database without auth). The discovery phase must detect and handle destructive endpoints rather than blindly probing them.

---

### Pitfall 6: Context-Insensitive Test Selection

**What goes wrong:**
The scanner applies all 13 OWASP test scenarios to all endpoints without regard to endpoint purpose, HTTP method, or security context. This is the root cause of multiple existing false positives: testing login endpoints for data exposure (Issue #5), testing public endpoints for auth bypass (Issue #4), testing rate limit bypass when no rate limiting exists (Issue #6). The "adaptive" scanner is not actually adapting its test selection.

**Why it happens:**
The existing architecture iterates over `self.endpoints` in each scenario without filtering. Adding adaptive test selection requires the API profile (from discovery) to inform which scenarios apply to which endpoints. Without this cross-component data flow, each scenario operates in isolation with no API-wide context. The industry research confirms this: automated tools that test endpoints individually without considering their role in the broader API miss context-dependent issues while creating noise from irrelevant tests.

**How to avoid:**
1. Build an endpoint classification system with categories that directly map to test applicability:
   - `auth-endpoints` (login, register, token, oauth): Skip sensitive data exposure tests, skip IDOR tests
   - `public-endpoints` (no auth required): Skip auth bypass tests, skip privilege escalation tests
   - `read-only-endpoints` (GET with no side effects): Skip business logic mutation tests
   - `admin-endpoints` (admin panel, management): Intensify privilege escalation tests
   - `data-endpoints` (CRUD on resources): Full test suite including IDOR, BOLA, injection
2. In each scenario's `get_test_cases()`, filter endpoints by applicable category before iterating.
3. For conditional tests (like rate limit bypass in S02), implement prerequisite checks: only run bypass tests if the prerequisite condition was met (rate limiting detected).
4. Document the test-to-endpoint-category matrix: which scenarios apply to which endpoint types.

**Warning signs:**
- All 13 scenarios run against all endpoints regardless of type
- Scenarios have no `if` conditions checking endpoint metadata
- Rate limit bypass tests run even when no rate limiting was detected
- Login endpoints flagged for "sensitive data exposure"
- The word "all endpoints" appears in test iteration loops without filters

**Phase to address:**
Spans two phases: Discovery/Learning (classify endpoints), then Adaptive Test Execution (use classification to filter tests). Both must be built before the test suite provides value.

**Relevance to issues.md:**
Directly relates to Issues #4 (public endpoint FPs), #5 (login auth_token FP), #6 (rate limit bypass FP). These are all symptoms of context-insensitive test selection.

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or reduced accuracy without requiring a rewrite.

### Pitfall 7: Aggregate Finding Ambiguity

**What goes wrong:**
When a test runs against multiple endpoints and reports a single aggregate finding (e.g., "Token reuse accepted by 7/10 endpoints"), the finding loses actionability. Which 7 endpoints? Are they all equally affected? The missing endpoint and evidence fields (Issues #1 and #2) are symptoms of an architectural problem: the finding model doesn't support multi-endpoint findings well.

**Why it happens:**
The `log_finding()` API accepts a single `endpoint` string and a single `Evidence` object. When a test discovers a vulnerability across multiple endpoints, the developer faces a choice: report one finding per endpoint (verbose but precise) or one aggregate finding (concise but vague). The current code chose aggregate and left the fields empty because there was no good way to represent "multiple endpoints."

**How to avoid:**
1. Report per-endpoint findings, not aggregates. A finding that affects 7 endpoints should be 7 findings, each with its own endpoint and evidence. Deduplication in the report layer can group them for presentation.
2. If aggregate findings are kept, require a representative endpoint and evidence. Make these fields non-optional in `log_finding()` (or add validation that warns when they're empty).
3. Add a `related_endpoints` list field to the Finding model for aggregate context: the primary endpoint goes in `endpoint`, other affected endpoints go in `related_endpoints`.
4. Never default `endpoint` to an empty string. Use `"Unknown"` as the default and log a warning, so missing endpoints are visible during development.

**Warning signs:**
- Findings with `endpoint: ""` or `evidence: null`
- A single finding claiming to affect "multiple endpoints" with no specifics
- Report consumers cannot determine which endpoint to remediate first

**Phase to address:**
Evidence and Reporting phase (RPT-01 through RPT-05 from PROJECT.md).

**Relevance to issues.md:**
Directly addresses Issues #1 (missing endpoint) and #2 (missing evidence). The fix must be architectural (change the Finding model and log_finding contract) not just a point fix in each scenario.

---

### Pitfall 8: BOLA/IDOR Detection Limited to Numeric IDs

**What goes wrong:**
The IDOR test (S03) assumes resource identifiers are numeric integers and tests by incrementing/decrementing the ID. APIs using string-based identifiers (usernames, slugs, UUIDs) are not tested for IDOR. This is a known false negative for VAmPI, which uses username-based paths (`/users/v1/{username}`).

**Why it happens:**
BOLA/IDOR is the #1 OWASP API Security vulnerability, but detecting it requires understanding how identifiers work for each specific API. Numeric ID manipulation is the simplest case. String-based, UUID-based, and composite identifiers each require different mutation strategies. Automated tools that only handle numeric IDs miss a significant portion of BOLA vulnerabilities -- the security community widely acknowledges that "there is no one proven way to approach BOLA" and tools that only try numeric increments are insufficient.

**How to avoid:**
1. During discovery, identify the type of each path parameter from the OpenAPI schema: string, integer, UUID, enum. Use the type to select appropriate mutation strategies.
2. For string identifiers: if the scanner has two user contexts (user A and user B), try accessing user A's resources with user B's credentials. This is more reliable than guessing other IDs.
3. For UUID identifiers: mutation (incrementing) is useless. The cross-user approach is the only viable strategy.
4. Implement path parameter type detection in the API profile and pass it to S03 for mutation strategy selection.

**Warning signs:**
- S03 only has a single mutation strategy (numeric increment/decrement)
- Path parameters detected as `{username}` are filled with `1` (the fallback in `openapi_parser.py` line 331)
- Cross-user IDOR testing only works when two user accounts are configured

**Phase to address:**
Adaptive Test Execution phase (TEST-01, TEST-02 from PROJECT.md).

**Relevance to issues.md:**
Directly relates to Issue #7a (FN: IDOR on /users/v1/{username}). The current `openapi_parser.py` already fills remaining path params with `1` as a fallback (line 331: `re.sub(r"\{(\w+)\}", r"1", url)`), which is incorrect for string-based identifiers.

---

### Pitfall 9: Injection Testing Ignoring Path Parameters

**What goes wrong:**
SQL injection and other injection tests (S04) only test parameters in request bodies and query strings, skipping path parameters entirely. APIs with path-parameter-based queries (like VAmPI's `/books/v1/{book_title}`) have known SQL injection vulnerabilities that the scanner misses.

**Why it happens:**
Path parameters feel "structural" -- they define which resource to access, not what data to process. Developers building injection tests naturally focus on input fields (body parameters, query parameters) where user data is expected. But many APIs use path parameters directly in database queries, making them just as vulnerable to injection.

**How to avoid:**
1. Enumerate all parameter locations from the OpenAPI spec: body, query, header, path, cookie. Apply injection payloads to ALL locations.
2. For path parameters specifically, the scanner must rebuild the URL with the injection payload replacing the path parameter value. This requires different request construction than body/query injection.
3. Prioritize path parameters that are strings (not integers) -- string path parameters are more likely to be used in SQL LIKE queries or NoSQL lookups.
4. Test each path parameter individually (one at a time) to identify which specific parameter is vulnerable.

**Warning signs:**
- S04 injection test only modifies `endpoint.body` and `endpoint.query_params`, never `endpoint.url`
- Path parameters with string types are not included in the injection target list
- Known path-parameter SQL injection vulnerabilities go undetected in testing

**Phase to address:**
Adaptive Test Execution phase. Requires the injection test to be aware of path parameters from the API profile.

**Relevance to issues.md:**
Directly relates to Issue #7b (FN: SQL injection on /books/v1/{book_title}).

---

### Pitfall 10: Report Output as an Attack Vector

**What goes wrong:**
The HTML report generator inserts API response bodies directly into HTML without escaping, creating a stored XSS vulnerability. When the scanner tests a malicious API (or an API that reflects attacker-controlled content), the report itself becomes a weapon. Anyone who opens the report in a browser can have JavaScript executed in their context.

**Why it happens:**
Security tool authors focus on finding vulnerabilities in targets, not on their own tool being vulnerable. The evidence capture pipeline faithfully records response bodies and passes them through to the report template. The `_escape()` function exists in the codebase but was not applied to evidence output -- a classic "the fix exists but wasn't used" situation.

**How to avoid:**
1. Apply HTML escaping to ALL dynamic content in report templates. No exceptions.
2. Use the existing `_escape()` function for all evidence fields: response body, request URL, request method, request headers.
3. Consider using Content Security Policy headers in the HTML report to prevent script execution even if escaping is missed.
4. Add a test that generates a report containing `<script>alert(1)</script>` in a response body and verifies it appears as escaped text, not executable HTML.

**Warning signs:**
- Response bodies appear unescaped in HTML reports
- The `_escape()` function exists but is not called in the evidence rendering path
- Opening a report from a test against a malicious API triggers browser alerts

**Phase to address:**
Evidence and Reporting phase (RPT-03 from PROJECT.md). This should be fixed immediately as it's a security vulnerability in the tool itself.

**Relevance to issues.md:**
Directly addresses Issue #8 (HTML report XSS vulnerability). This is the only issue where the scanner itself is vulnerable, not just inaccurate.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding fail indicators (`"status": "fail"`) in `is_true_success()` | Quick fix for VAmPI FPs | Breaks on any API that uses different error conventions | Never -- build configurable/adaptive detection from the start |
| Testing against VAmPI only | Fast validation cycle | Overfitting to one API's behavior, false confidence in accuracy | Only for initial development; must add diverse targets before release |
| Skipping regression tests for FP fixes | Faster fix delivery | FP whack-a-mole: fixing one FP introduces new FPs or suppresses TPs | Never -- regression tests are the only way to ensure fix stability |
| Defaulting ambiguous endpoints to "public" | Simpler classification logic | False negatives: protected endpoints treated as public skip critical auth tests | Never -- default to "unknown" and probe |
| Using `endpoint=""` for aggregate findings | Avoids choosing a representative endpoint | Unusable findings that can't be prioritized or remediated | Never -- always include at least a representative endpoint |
| Monolithic scenario files (300-469 lines) | All related tests in one place | Hard to test, modify, and extend individual test cases | Acceptable in early development, must refactor before adding adaptive logic |

## Integration Gotchas

Common mistakes when connecting adaptive components to the existing scenario system.

| Integration Point | Common Mistake | Correct Approach |
|-------------------|----------------|------------------|
| API Profile to Scenarios | Passing profile as a flat dict; scenarios cherry-pick fields and miss updates | Define a typed APIProfile dataclass with clear fields; pass it through `setup()` alongside existing parameters |
| Discovery to Test Execution | Running discovery and tests sequentially; discovery results not persisted | Persist the API profile to disk (JSON/YAML) so tests can be re-run without re-probing; enables profile review before testing |
| Endpoint Classification to Test Filtering | Each scenario implements its own filtering logic; inconsistent classification | Centralize endpoint filtering in `BaseScenario` or a filter utility; scenarios declare which endpoint categories they apply to |
| Response Pattern Detection to Finding Validation | Pattern detection only used in `is_true_success()`; not available in finding post-processing | Make the pattern detector a first-class component available at both test-time and report-time for finding deduplication/validation |
| Confidence Scoring to Report Generation | Confidence scores added to findings but not displayed in reports | Update both JSON and HTML report templates to surface confidence scores; sort findings by confidence |

## Performance Traps

Patterns that work at small scale but fail as the number of endpoints or API complexity grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| O(N*M) discovery probing (N endpoints x M probe types) | Discovery phase takes 10+ minutes on large APIs | Limit probe types to 3-4 essential ones; parallelize with async requests; cache responses | APIs with 100+ endpoints |
| Baseline capture per endpoint per scenario | Redundant identical requests; N scenarios each making baseline requests to same endpoints | Share baseline cache across scenarios via `_baselines` dict (partially exists); persist across runs | APIs with 50+ endpoints and 13 scenarios |
| String matching for response pattern detection | CPU-bound on large response bodies; regex patterns with backtracking | Limit body inspection to first 1KB; use compiled regex; parse JSON once and inspect structure | Endpoints returning large JSON arrays (10KB+ bodies) |
| Full evidence capture for every request | Memory grows linearly with request count; large reports | Truncate response bodies in evidence to configurable max length (currently 500 chars); store evidence on disk, not in memory | Long test runs with 1000+ requests |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces. Specific to adaptive API security testing.

- [ ] **Response pattern detection:** Works on VAmPI -- verify it also works on an API that always returns 200, an API that uses XML errors, and an API that returns HTML error pages
- [ ] **Public endpoint classification:** Correctly identifies VAmPI's public endpoints -- verify it handles specs with no global security field, specs with empty global security, and specs where `security` is omitted entirely (not the same as empty)
- [ ] **IDOR/BOLA testing:** Finds numeric ID IDOR -- verify it also handles string identifiers, UUIDs, and composite keys
- [ ] **Injection testing:** Tests body/query parameters -- verify it also tests path parameters and header parameters
- [ ] **Finding deduplication:** Removes exact duplicates -- verify it also handles near-duplicates (same vulnerability, slightly different evidence)
- [ ] **Evidence capture:** Captures evidence for single-endpoint findings -- verify aggregate findings also have representative evidence
- [ ] **HTML report escaping:** Escapes response bodies -- verify it also escapes request URLs, headers, and method names
- [ ] **Confidence scoring:** Assigns scores -- verify scores actually influence report ordering and actionability
- [ ] **Discovery safety:** Probes GET endpoints safely -- verify POST/DELETE probes don't execute destructive operations
- [ ] **Test prerequisite logic:** Rate limit bypass skipped when no rate limiting exists -- verify ALL conditional tests have prerequisite checks, not just S02

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Blind spec trust (Pitfall 1) | MEDIUM | Add runtime verification layer; re-run discovery with probing enabled; rebuild API profile |
| Overfitted response patterns (Pitfall 2) | HIGH | Redesign pattern detector as hierarchical/configurable; test against diverse API targets; may require significant refactoring of `is_true_success()` callers |
| New FPs from old FP fixes (Pitfall 3) | HIGH | Build regression test suite retroactively; re-audit all findings against ground truth; may need to revert fixes and re-apply with tests |
| Security inheritance bugs (Pitfall 4) | LOW | Fix parser edge cases; add comprehensive test suite for all inheritance scenarios; re-run classification |
| Discovery damaging target (Pitfall 5) | HIGH | Cannot undo database resets or state changes; implement safety controls and re-deploy target; document which endpoints are destructive |
| Context-insensitive testing (Pitfall 6) | MEDIUM | Add endpoint-to-scenario filtering; requires touching all 13 scenario files but each change is small |
| Aggregate finding ambiguity (Pitfall 7) | LOW | Refactor to per-endpoint findings; mechanical change in each scenario's loop |
| BOLA limited to numeric IDs (Pitfall 8) | MEDIUM | Implement additional mutation strategies; requires cross-user testing infrastructure |
| Injection skipping path params (Pitfall 9) | LOW | Add path parameter to injection target list; requires URL reconstruction logic |
| Report XSS (Pitfall 10) | LOW | Apply `_escape()` to all evidence fields; single-file fix in report_generator.py |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1 Blind spec trust | Discovery/Learning | Run scanner against API with intentionally wrong spec; verify scanner detects discrepancies |
| #2 Overfitted response patterns | Discovery/Learning | Run scanner against 5+ different API styles; verify FP rate stays below 5% on each |
| #3 FP fix regression | All phases (regression testing) | Maintain ground truth finding set; automated comparison after every change |
| #4 Security inheritance | Discovery/Learning | Unit test suite covering all 5 inheritance scenarios documented above |
| #5 Destructive discovery | Discovery/Safety | Run discovery against VAmPI; verify /createdb is not called with valid payload |
| #6 Context-insensitive testing | Adaptive Test Execution | Verify login endpoints excluded from data exposure tests; verify public endpoints excluded from auth tests |
| #7 Aggregate findings | Evidence/Reporting | Verify zero findings have empty endpoint or null evidence after changes |
| #8 BOLA numeric only | Adaptive Test Execution | Verify IDOR found on VAmPI /users/v1/{username} (string identifier) |
| #9 Injection path params | Adaptive Test Execution | Verify SQLi found on VAmPI /books/v1/{book_title} (path parameter) |
| #10 Report XSS | Evidence/Reporting | Generate report with `<script>` in response body; verify escaped output |

## Sources

**Project-specific (HIGH confidence):**
- `/home/abdulr7man/rb/issues.md` -- 9 documented issue categories with specific file/line references
- `/home/abdulr7man/rb/.planning/PROJECT.md` -- Requirements and known problems
- `/home/abdulr7man/rb/.planning/codebase/CONCERNS.md` -- Detailed concern analysis
- `/home/abdulr7man/rb/.planning/codebase/ARCHITECTURE.md` -- Current system architecture
- `/home/abdulr7man/rb/api_pentest/scenarios/base_scenario.py` -- Base scenario source code (is_success_status, log_finding)
- `/home/abdulr7man/rb/api_pentest/core/openapi_parser.py` -- OpenAPI parser source code (security inheritance handling)

**Industry research (MEDIUM confidence, multiple sources agree):**
- [PortSwigger - Best practices for managing false positives](https://portswigger.net/burp/documentation/dast/user-guide/working-with-scans/false-positives-best-practice) -- DAST false positive management guidance
- [Invicti - How to Cut Through DAST False Positives](https://www.invicti.com/blog/web-security/reduce-dast-false-positives) -- Proof-based scanning for false positive reduction
- [Microsoft MSRC - Scaling DAST](https://www.microsoft.com/en-us/msrc/blog/2025/01/scaling-dynamic-application-security-testing-dast) -- OpenAPI spec generation challenges for DAST at scale
- [Criteo Tech Blog - Can You Trust Your OpenAPI Spec](https://medium.com/criteo-engineering/can-you-trust-your-openapi-spec-a62677d43fb3) -- Documented discrepancies between specs and live APIs
- [USENIX Security 2022 - Dos and Don'ts of ML in Computer Security](https://www.usenix.org/system/files/sec22summer_arp.pdf) -- Overfitting and sampling bias in security ML systems
- [Traceable - BOLA Deep Dive](https://www.traceable.ai/blog-post/a-deep-dive-on-the-most-critical-api-vulnerability----bola-broken-object-level-authorization) -- BOLA detection complexity, no one-size-fits-all approach
- [OpenAPI Learning - Security Specification](https://learn.openapis.org/specification/security.html) -- Official security inheritance rules

**Ecosystem patterns (MEDIUM confidence):**
- [StackHawk - OpenAPI Security Testing Foundation](https://www.stackhawk.com/blog/openapi-security-testing/) -- Spec-driven scanning best practices
- [Astra - DAST False Positive Triage](https://www.getastra.com/blog/dast/false-positive-triage/) -- ML-based triage and regression prevention
- [Penligent AI - DAST Tools 2026 Guide](https://www.penligent.ai/hackinglabs/dast-tools-in-2026-a-deep-technical-guide-for-security-engineers-and-ai-driven-appsec-teams/) -- Intelligent scanner architecture patterns
- [APIsec - Shadow API Discovery](https://www.apisec.ai/blog/secure-your-shadow-apis-best-practices-for-api-discovery) -- API discovery pitfalls and undocumented endpoints

---
*Pitfalls research for: Adaptive API Security Testing*
*Researched: 2026-02-04*
