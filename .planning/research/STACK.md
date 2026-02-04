# Stack Research: Adaptive API Security Testing

**Domain:** Adaptive API discovery, intelligent security test selection, false positive reduction
**Researched:** 2026-02-04
**Confidence:** MEDIUM-HIGH (core libraries verified via PyPI/official docs; adaptive patterns synthesized from multiple sources)

## Context

This stack research is scoped to the **adaptive capabilities being added** to an existing API pentest toolkit. The existing toolkit already uses: `requests`, `pyjwt`, `cryptography`, `pyyaml`, `jinja2`, `colorama`, `prance`, `openapi-spec-validator`. Those are not re-evaluated here.

The problem being solved: **31% false positive rate** caused by hardcoded assumptions in the current test scenarios:
- `is_success_status()` uses `200 <= status < 300` universally
- `is_auth_failure()` checks only `401, 403`
- No baseline calibration -- IDOR test flags any 2xx with different body as a finding
- No API behavior learning -- tests assume all non-`public-no-auth` endpoints require auth
- No response structure analysis -- success/failure determined purely by HTTP status code

---

## Recommended Stack

### 1. OpenAPI Intelligence Layer

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| openapi-core | 0.22.0 | Deep OpenAPI spec parsing with security scheme extraction | Only Python library that provides structured security data providers (API keys, Cookie, Basic, Bearer HTTP auth) via `result.security` after unmarshalling. Can validate requests/responses against spec. Extracts what prance cannot: operation-level security requirements, response schemas for validation. | HIGH |
| prance | 25.4.8.0 (already installed) | $ref resolution, spec normalization | Already in use. Keep for $ref resolution. openapi-core complements it -- prance resolves, openapi-core interprets. | HIGH |
| openapi-pydantic | 0.5.1 | Typed OpenAPI spec models in Pydantic | Converts raw OpenAPI dicts into typed Pydantic objects. Enables IDE-assisted access to security schemes, parameters, response schemas. Compatible with both Pydantic 1.x and 2.x. Speeds up development of the spec intelligence extractor. | MEDIUM |

**Why openapi-core over alternatives:**
- `openapi3` (Dorthu): Read-only client, no security extraction, no response validation
- `openapi3-parser` (manchenkoff): Lightweight parser but no security data providers
- Raw dict parsing (current approach): Works but fragile -- misses edge cases in security inheritance, allOf/oneOf compositions

**How this solves the FP problem:** The current `openapi_parser.py` extracts `security_schemes` as a flat list of names. openapi-core can extract the *type* of each security scheme (http/apiKey/oauth2/openIdConnect), the *location* (header/query/cookie), and the *scheme* (bearer/basic). This enables the discovery layer to know *how* an endpoint is secured, not just *that* it is secured.

### 2. API Discovery and Protocol Detection

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| graphql-core | 3.2.7 | GraphQL introspection query support | Standard Python GraphQL library. Provides `get_introspection_query()` and `build_client_schema()` for discovering GraphQL APIs. Detects if an endpoint speaks GraphQL by sending introspection query and validating response structure. | HIGH |
| grpcio-reflection | 1.76.0+ | gRPC service reflection/introspection | Official gRPC Python reflection client. `ProtoReflectionDescriptorDatabase` discovers services and methods via `list_services`. Enables detecting if target speaks gRPC. | HIGH |
| (stdlib) difflib | N/A | Response similarity scoring | SequenceMatcher.ratio() provides 0-1 similarity scores for response body comparison. Used to distinguish "different data returned" from "same template, different values" -- critical for IDOR FP reduction. Zero dependencies, always available. | HIGH |

**Protocol detection strategy (no single library exists for this):**
Auto-detection must be built from primitives. The detection signals are:
1. **Content-Type header**: `application/grpc` = gRPC, `application/graphql` = GraphQL
2. **Endpoint patterns**: single `/graphql` endpoint = GraphQL; resource-path patterns = REST
3. **HTTP version**: HTTP/2 with binary payload = likely gRPC
4. **Introspection probe**: Send GraphQL introspection query, check for `__schema` in response
5. **Response format**: JSON with `data`/`errors` keys = GraphQL; Protobuf binary = gRPC

This is custom logic, not a library. The libraries above provide the protocol-specific clients for probing.

### 3. Response Analysis and Baseline Calibration

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| deepdiff | 8.6.1 | Structural diff of API responses | Compares two JSON response bodies structurally, distinguishing value changes from structural changes. Critical for IDOR validation: "same structure, different values" (legitimate parameterized response) vs "completely different structure" (genuinely different resource). Supports ignore paths, type coercion, custom comparators. | HIGH |
| jsonschema | 4.26.0 | Response structure validation against learned/declared schemas | Validates whether response bodies conform to declared OpenAPI response schemas. Can also learn schemas from observed responses and validate subsequent responses against them. Full Draft 2020-12 support. | HIGH |
| (stdlib) statistics | N/A | Response time baseline statistics | `mean()`, `stdev()` for building response time baselines. Detect anomalous timing that indicates different code paths (e.g., auth bypass hitting different handler). | HIGH |
| (stdlib) re | N/A | Error pattern matching in response bodies | Regex-based detection of error patterns in response bodies: `"error"`, `"message"`, `"unauthorized"`, framework-specific patterns. Already used in codebase. | HIGH |

**Why deepdiff over alternatives:**
- Manual dict comparison (current approach): Only checks `body != baseline_body` -- any whitespace or timestamp difference triggers a false positive
- `jsondiff`: Less mature, fewer features, no structural vs value distinction
- `dictdiffer`: Lighter but cannot handle nested structure comparison with the depth deepdiff provides

**How this solves the FP problem:** The current IDOR test (s03) does `if evidence.response_body != baseline.response_body` -- a naive string comparison. deepdiff enables: "did the response *structure* change (different resource) or just the *values* change (same template, different data)?" Combined with `difflib.SequenceMatcher.ratio()` for body similarity scoring, this separates true IDORs from parameterized responses.

### 4. API Profile Modeling

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| pydantic | 2.12.5 | API profile data models with validation | Type-safe models for API profiles (endpoint behaviors, auth patterns, response fingerprints). Built-in serialization to/from JSON for caching profiles. Validation ensures profile data integrity. Rust-powered core for performance. | HIGH |
| (stdlib) dataclasses | N/A | Lightweight internal data transfer objects | Already used in codebase for Evidence, Endpoint, Finding models. Continue using for simple DTOs that do not need validation. Reserve pydantic for profile models that need serialization and validation. | HIGH |

**Why pydantic over dataclasses for profiles:**
The API profile models need:
- Serialization to JSON (for caching learned profiles between runs)
- Validation (profiles from cached files must be validated before use)
- Default values with complex types
- Union types (endpoint can have multiple possible auth schemes)

Plain dataclasses cannot do this without `dataclasses-json` or manual serialization. Pydantic handles all of it natively with better performance (Rust core).

**Why NOT a rule engine (GoRules, pyKnow, etc.):**
Evaluated ZEN Engine (GoRules), pyKnow, and rule-engine. These are overkill for adaptive test selection. The selection logic is: "given this API profile, which of 13 scenarios are relevant?" This is a scoring/matching problem, not a complex inference problem. A simple Python function with weighted scoring is clearer, more testable, and more maintainable than a rule engine DSL. Rule engines add complexity without proportional benefit at this scale.

### 5. HTTP Client Enhancement (Optional, Deferred)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| httpx | 0.28.1 | Async HTTP client with HTTP/2 support | Needed IF testing gRPC or HTTP/2-only APIs. Current `requests` cannot do HTTP/2. httpx provides both sync and async APIs, HTTP/2 support via `httpx[http2]`, and a requests-compatible API. Benchmark: 7x faster than requests for concurrent operations. | MEDIUM |

**Recommendation: DEFER httpx migration.** The existing toolkit uses `requests` throughout. Migrating to httpx is a cross-cutting change that touches every scenario. The adaptive layer should be built to work with the existing `requests`-based `PentestHttpClient`. Add httpx only when gRPC/HTTP2 detection becomes a priority. The current `PentestHttpClient` abstraction makes future migration straightforward.

**Why defer, not reject:** httpx is the clear successor to requests. The pre-release 1.0 versions exist. But switching HTTP clients is a *risk* for a milestone focused on adaptive capabilities. The abstraction layer (`PentestHttpClient`) already isolates HTTP details. When the time comes, swap `self.session = requests.Session()` for `httpx.Client()` with minimal disruption.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| structlog | 24.5.0+ | Structured logging for discovery audit trail | Use for discovery phase logging. Key-value structured logs enable filtering by endpoint, auth scheme, detection type. Integrates with stdlib logging. | MEDIUM |
| (stdlib) functools.lru_cache | N/A | Cache probe results during discovery | Avoid re-probing same endpoints during a single run. Already available, zero cost. | HIGH |
| (stdlib) hashlib | N/A | Fingerprint response bodies for deduplication | SHA256 hash of normalized response body for quick equality checks before expensive deepdiff. | HIGH |
| (stdlib) json | N/A | JSON parsing of response bodies | Already used throughout codebase. | HIGH |
| (stdlib) enum | N/A | API type classification enums | REST, GraphQL, gRPC, SOAP classification. Already used in codebase (BodyMode, Severity). | HIGH |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Test framework | Already standard for Python projects. Test the adaptive logic with mock API responses. |
| pytest-mock / unittest.mock | Mock HTTP responses | Test discovery probes without live APIs. Mock response bodies, status codes, headers. |
| responses (library) | Mock requests library calls | Intercept `requests.Session` calls in tests. Verify correct probes are sent. |

---

## Installation

```bash
# New adaptive layer dependencies
pip install openapi-core>=0.22.0
pip install openapi-pydantic>=0.5.1
pip install pydantic>=2.12.0
pip install deepdiff>=8.6.0
pip install jsonschema>=4.26.0
pip install graphql-core>=3.2.7

# Optional: gRPC detection (only if targeting gRPC APIs)
pip install grpcio>=1.76.0
pip install grpcio-reflection>=1.76.0

# Optional: structured logging
pip install structlog>=24.5.0

# Dev dependencies
pip install pytest pytest-mock responses
```

**Note:** `prance`, `openapi-spec-validator`, `requests`, `pyjwt`, `cryptography`, `pyyaml`, `jinja2`, `colorama` are already installed and unchanged.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| OpenAPI parsing | openapi-core | openapi3-parser | No security data extraction, no response validation |
| OpenAPI parsing | openapi-core | Raw dict walking (current) | Fragile, misses security inheritance chains, no response schema validation |
| Response diffing | deepdiff | jsondiff | Less mature, no structural vs value distinction, fewer configuration options |
| Response diffing | deepdiff | Manual string comparison (current) | Current approach: `body != baseline_body` causes false positives on timestamps, pagination tokens |
| Response similarity | difflib.SequenceMatcher | fuzzywuzzy/rapidfuzz | Overkill for body similarity; SequenceMatcher is stdlib, zero dependencies |
| Data models | pydantic | dataclasses-json | Less type safety, no Rust-powered validation, weaker serialization |
| Data models | pydantic | attrs | Less ecosystem support, no built-in JSON schema generation |
| Test orchestration | Simple Python scoring | GoRules ZEN Engine | Rule engine DSL is overkill for 13-scenario selection. Adds dependency, learning curve, and debugging opacity for no proportional benefit. |
| HTTP client | requests (keep) | httpx | Migration risk outweighs benefit for this milestone. Defer to when HTTP/2 is needed. |
| Protocol detection | Custom probing logic | No library exists | Searched extensively. API protocol auto-detection is not a solved library problem. Must build from primitives (Content-Type checks, introspection probes, response format analysis). |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| ML-based FP reduction (scikit-learn, etc.) | Requires training data we do not have. Adds massive dependency. Overkill for pattern-matching problem. The FP problem is caused by bad heuristics, not by data that needs ML. | Behavioral baseline calibration with deepdiff + response fingerprinting |
| Selenium/browser automation | Not applicable -- we test APIs, not web UIs | requests/httpx for HTTP calls |
| openapi-schema-pydantic (kuimono) | No longer maintained. Superseded by openapi-pydantic (mike-oakley) | openapi-pydantic 0.5.1 |
| Heavy DAST frameworks (ZAP, Burp extensions) | We are building the toolkit, not wrapping another one. Different architecture. | Direct HTTP probing with requests |
| asyncio throughout | Current codebase is synchronous. Introducing async across 13 scenarios is high-risk refactoring. Discovery probes are I/O bound but not high-volume enough to justify async complexity. | Synchronous requests with connection pooling |

---

## Stack Patterns by Variant

**If targeting REST APIs only (most common case):**
- Use openapi-core + deepdiff + jsonschema
- Skip graphql-core and grpcio-reflection
- Smallest dependency footprint

**If targeting REST + GraphQL:**
- Add graphql-core for introspection
- Discovery layer sends introspection query to detect GraphQL endpoints
- Profile stores GraphQL-specific metadata (types, queries, mutations)

**If targeting REST + GraphQL + gRPC:**
- Add grpcio + grpcio-reflection
- Consider httpx for HTTP/2 support (gRPC uses HTTP/2)
- Most complex variant, defer unless specifically needed

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| openapi-core 0.22.0 | Python 3.9-3.14 | Verified on PyPI (Dec 2025 release) |
| pydantic 2.12.5 | Python 3.9-3.14 | Verified on PyPI (Nov 2025 release). Python 3.14 support added in 2.12. |
| deepdiff 8.6.1 | Python 3.9+ | Verified on PyPI (Sep 2025 release) |
| jsonschema 4.26.0 | Python 3.10+ | Verified on PyPI (Jan 2026 release). NOTE: requires Python 3.10+, not 3.9. |
| graphql-core 3.2.7 | Python 3.7-3.14 | Verified on GitHub |
| openapi-pydantic 0.5.1 | Pydantic 1.8+ and 2.x | Compatibility layer built in |
| prance 25.4.8.0 | Python 3.8+ | Already installed, verified on Libraries.io (Apr 2025 release) |

**Compatibility concern:** jsonschema 4.26.0 requires Python >= 3.10. If the project needs to support Python 3.9, pin jsonschema to an older version (4.23.x supports 3.9). Check the project's minimum Python version requirement before installing.

---

## Sources

### Verified via Official Package Registries (HIGH confidence)
- [openapi-core 0.22.0 on PyPI](https://pypi.org/project/openapi-core/) -- version, features, security providers
- [httpx 0.28.1 on PyPI](https://pypi.org/project/httpx/) -- version, HTTP/2 support, async API
- [jsonschema 4.26.0 on PyPI](https://pypi.org/project/jsonschema/) -- version, draft support, Python requirements
- [deepdiff 8.6.1 on PyPI](https://pypi.org/project/deepdiff/) -- version, features, security patch
- [pydantic 2.12.5 on PyPI](https://pypi.org/project/pydantic/) -- version, Python 3.14 support
- [prance on Libraries.io](https://libraries.io/pypi/prance) -- version 25.4.8.0 confirmed
- [graphql-core on GitHub](https://github.com/graphql-python/graphql-core) -- version 3.2.7, introspection API
- [grpcio-reflection on PyPI](https://pypi.org/project/grpcio-reflection/) -- version 1.76.0, reflection API
- [openapi-pydantic on GitHub](https://github.com/mike-oakley/openapi-pydantic) -- version 0.5.1, Pydantic compat

### Verified via Official Documentation (HIGH confidence)
- [openapi-core security docs](https://openapi-core.readthedocs.io/en/latest/security/) -- security data providers API
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) -- SequenceMatcher algorithm, ratio()
- [gRPC reflection guide](https://grpc.io/docs/guides/reflection/) -- ProtoReflectionDescriptorDatabase
- [GraphQL introspection](https://graphql.org/learn/introspection/) -- introspection query specification

### WebSearch-Informed (MEDIUM confidence, cross-verified)
- [HTTPX vs Requests performance](https://www.speakeasy.com/blog/python-http-clients-requests-vs-httpx-vs-aiohttp) -- async benchmarks, HTTP/2 comparison
- [Levo.ai API discovery approach](https://www.levo.ai/resources/blogs/top-10-api-security-testing-tools-2026) -- adaptive discovery patterns
- [Escape DAST BLST engine](https://escape.tech/blog/top-dast-tools/) -- feedback-driven testing approach
- [Wallarm FP reduction with ML](https://lab.wallarm.com/reducing-false-positives-api-security-advanced-techniques-machine-learning/) -- adaptive detection patterns
- [OWASP fingerprinting guide](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/08-Fingerprint_Web_Application_Framework) -- response fingerprinting techniques
- [Autoswagger discovery tool](https://www.darknet.org.uk/2025/10/autoswagger-automated-discovery-and-testing-of-openapi-swagger-endpoints/) -- OpenAPI-driven testing patterns

### Training Data Only (LOW confidence, flagged for validation)
- Rule engine assessment (GoRules, pyKnow comparative evaluation) -- based on general knowledge, not benchmark data
- structlog version recommendation -- version number from search but not deeply verified
- Async vs sync performance claims for this specific use case -- general benchmarks, not specific to security scanning workloads

---

## Roadmap Implications for Stack

The stack divides cleanly into phases:

1. **Response Analysis First** -- deepdiff, jsonschema, difflib are the foundation. They fix the FP problem immediately without requiring discovery infrastructure.

2. **OpenAPI Intelligence Second** -- openapi-core, openapi-pydantic extract richer context from specs the toolkit already parses. This enables "skip auth tests on endpoints marked public" and "validate responses against declared schemas."

3. **Discovery Probing Third** -- Protocol detection, auth scheme probing, and endpoint classification. This is the most complex layer and depends on response analysis being solid.

4. **Adaptive Selection Last** -- Profile-driven test selection requires all three prior layers. Simple scoring function, not a rule engine.

---
*Stack research for: Adaptive API Security Testing*
*Researched: 2026-02-04*
