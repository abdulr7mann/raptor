# Architecture: Adaptive API Security Testing

**Research Date:** 2026-02-04
**Focus:** Adding adaptive intelligence layer to existing pentest toolkit

## Executive Summary

The adaptive layer adds three new architectural components to the existing toolkit: **Discovery Engine** (learns API characteristics), **API Profiler** (builds unified API profile), and **Validation Engine** (contextual finding verification). These integrate as a pre-processing phase before scenario execution, with the API Profile flowing through to scenarios for intelligent test selection and validation.

**Integration Strategy:** Minimal disruption - new components plug in before existing scenario execution, with BaseScenario enhanced to consume API Profile without breaking existing 13 scenarios.

## Industry Context

Modern API security tools in 2026 follow a three-phase pattern:

1. **Discovery Phase**: Automated endpoint discovery, auth scheme detection, response pattern learning ([Akamai](https://www.akamai.com/resources/reference-architecture/api-discovery-security), [Gravitee](https://www.gravitee.io/blog/api-discovery-distributed-architectures))
2. **Profiling Phase**: Build unified API behavioral profile with security context ([AccuKnox eBPF telemetry](https://accuknox.com/blog/best-api-security-tools-2026))
3. **Adaptive Testing Phase**: Select relevant tests, validate findings against profile ([Imperva adaptive positive security](https://securityboulevard.com/2025/11/why-api-security-will-drive-appsec-in-2026-and-beyond/))

**Key Pattern**: Server-side discovery with centralized intelligence, not client-side per-scenario logic ([Microservices.io patterns](https://microservices.io/patterns/client-side-discovery.html)).

## Proposed Architecture

### Current Architecture (Existing)

```
┌─────────────────┐
│   CLI Entry     │
│ run_pentest.py  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Orchestration Layer           │
│   PentestRunner                 │
│   - parse_input()               │
│   - init_oauth()                │
│   - init_http()                 │
│   - run_scenarios()             │
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌─────────────┐
│ Input  │ │   Scenario  │
│ Parser │ │  Execution  │
│        │ │  (S01-S13)  │
└────────┘ └──────┬──────┘
                  │
                  ▼
           ┌──────────────┐
           │   Reporting  │
           └──────────────┘
```

**Data Flow:**
1. Parse spec → List[Endpoint]
2. For each scenario: run(endpoints) → List[Finding]
3. Generate report(findings)

**Problem:** Scenarios operate on raw Endpoint objects with no contextual intelligence. Every scenario reimplements auth checks, success detection, endpoint filtering.

### Adaptive Architecture (Proposed)

```
┌─────────────────┐
│   CLI Entry     │
│ run_pentest.py  │
└────────┬────────┘
         │
         ▼
┌───────────────────────────────────────────────┐
│   Orchestration Layer (ENHANCED)              │
│   PentestRunner                               │
│   - parse_input()                             │
│   - build_profile()        ← NEW              │
│   - init_oauth()                              │
│   - init_http()                               │
│   - run_scenarios(profile) ← ENHANCED         │
└────────┬──────────────────────────────────────┘
         │
    ┌────┴─────┬─────────────────┐
    │          │                 │
    ▼          ▼                 ▼
┌────────┐ ┌──────────────┐ ┌──────────────┐
│ Input  │ │  Discovery   │ │     API      │
│ Parser │ │    Engine    │ │   Profiler   │
│        │ │     NEW      │ │     NEW      │
└────────┘ └──────┬───────┘ └──────┬───────┘
                  │                │
                  └────────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ API Profile  │  ← Shared State
                    │   (Model)    │
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌─────────────┐       ┌──────────────┐
         │  Scenario   │       │  Validation  │
         │ Execution   │◄──────┤    Engine    │
         │  (S01-S13)  │       │     NEW      │
         │  ENHANCED   │       │              │
         └──────┬──────┘       └──────────────┘
                │
                ▼
         ┌──────────────┐
         │   Reporting  │
         │   ENHANCED   │
         └──────────────┘
```

**Enhanced Data Flow:**
1. Parse spec → List[Endpoint]
2. **Discovery → API Profile** (auth scheme, response patterns, endpoint classification)
3. For each scenario: run(endpoints, **profile**) → List[Finding]
4. **Validation Engine filters findings** → List[ValidatedFinding]
5. Generate report(validated_findings)

**Key Change:** API Profile is built once, shared across all scenarios. Validation happens centrally, not per-scenario.

## Component Specifications

### 1. Discovery Engine

**Purpose:** Probe API to learn characteristics without causing harm

**Location:** `api_pentest/adaptive/discovery_engine.py`

**Responsibilities:**
- Detect authentication scheme (Bearer, API key, OAuth2, cookie, custom header)
- Classify endpoints (public vs protected) using OpenAPI security + runtime probing
- Analyze response patterns (success indicators, failure formats)
- Detect API type (REST, GraphQL, gRPC) via Content-Type and introspection
- Safe probing (read-only, avoid destructive endpoints like /reset, /delete)

**Interface:**
```python
class DiscoveryEngine:
    def discover(self, endpoints: List[Endpoint], spec: Dict) -> DiscoveryResult:
        """Run safe discovery probes, return learned characteristics"""

    def detect_auth_scheme(self) -> AuthScheme:
        """Probe auth headers, analyze 401/403 responses"""

    def classify_endpoints(self) -> Dict[str, EndpointClass]:
        """Map endpoint -> PUBLIC | PROTECTED | DESTRUCTIVE"""

    def learn_response_patterns(self) -> ResponsePatternSet:
        """Analyze successful/failed responses, extract patterns"""
```

**Integration Point:** Called by `PentestRunner.build_profile()` before scenario execution

**Dependencies:**
- PentestHttpClient (for safe probes)
- OpenAPI parser (for security scheme hints)
- Pattern matching libraries (re, difflib for response analysis)

**Safety Controls:**
- Whitelist safe HTTP methods (GET, HEAD, OPTIONS) for initial probes
- Blacklist destructive path patterns (/delete, /reset, /createdb, /drop)
- Rate limiting (max 3 probes per endpoint)
- Fail-safe defaults (if discovery fails, assume most restrictive: PROTECTED)

**Output:** `DiscoveryResult` with detected auth, endpoint classifications, response patterns

### 2. API Profiler

**Purpose:** Build unified API profile from discovery + OpenAPI spec

**Location:** `api_pentest/adaptive/api_profiler.py`

**Responsibilities:**
- Merge OpenAPI security definitions with runtime discovery results
- Resolve conflicts (spec says public, discovery says protected → trust runtime)
- Build canonical API Profile model
- Persist profile for reuse across runs (optional caching)

**Interface:**
```python
class APIProfiler:
    def build_profile(self,
                     spec: Dict,
                     discovery: DiscoveryResult,
                     endpoints: List[Endpoint]) -> APIProfile:
        """Merge spec + discovery into unified profile"""

    def resolve_conflicts(self, spec_auth, runtime_auth) -> AuthScheme:
        """Trust runtime over spec when conflict detected"""

    def enrich_endpoints(self) -> List[EnrichedEndpoint]:
        """Attach classification, auth requirements to each endpoint"""
```

**Data Model (APIProfile):**
```python
@dataclass
class APIProfile:
    api_type: APIType  # REST, GraphQL, gRPC
    auth_scheme: AuthScheme  # Bearer, APIKey, OAuth2, etc.
    endpoint_map: Dict[str, EndpointMetadata]  # URL → metadata
    response_patterns: ResponsePatternSet  # Success/fail indicators
    discovered_at: datetime
    confidence: ProfileConfidence  # HIGH/MEDIUM/LOW
```

**Integration Point:** Consumed by scenarios via `BaseScenario.get_profile()`

**Dependencies:**
- Discovery Engine (discovery results)
- OpenAPI parser (spec security definitions)
- Pydantic (profile model validation)

**Conflict Resolution Rules:**
1. **Auth Scheme**: Runtime > Spec (APIs lie in docs)
2. **Endpoint Classification**: Runtime > Spec (specs often incomplete)
3. **Response Patterns**: Spec + Runtime merged (both sources valuable)

**Output:** `APIProfile` object passed to all scenarios

### 3. Validation Engine

**Purpose:** Filter findings using contextual intelligence to eliminate false positives

**Location:** `api_pentest/adaptive/validation_engine.py`

**Responsibilities:**
- Validate finding against API profile context
- Apply suppression rules (e.g., login endpoints returning tokens is not data exposure)
- Check prerequisite conditions (don't flag bypass when no protection exists)
- Assign confidence levels (CONFIRMED, LIKELY, UNCERTAIN)
- Deduplicate findings

**Interface:**
```python
class ValidationEngine:
    def validate_finding(self, finding: Finding, profile: APIProfile) -> ValidationResult:
        """Check if finding is valid given API context"""

    def apply_suppression_rules(self, finding: Finding) -> bool:
        """Returns True if finding should be suppressed"""

    def assign_confidence(self, finding: Finding) -> ConfidenceLevel:
        """Rate confidence based on evidence quality"""

    def deduplicate(self, findings: List[Finding]) -> List[Finding]:
        """Remove duplicate findings (same title + endpoint)"""
```

**Validation Rules (from issues.md):**
1. **Public Endpoint Rule**: Suppress auth-related findings on endpoints classified as PUBLIC
2. **Login Endpoint Rule**: Suppress "token exposed" on /login, /auth, /token endpoints
3. **Response Body Rule**: Check both HTTP status AND body for application-level failures
4. **Prerequisite Rule**: Suppress bypass findings when no protection exists to bypass
5. **Aggregate Rule**: Require endpoint + evidence for all findings

**Integration Point:** Called by `PentestRunner` after scenario execution, before reporting

**Dependencies:**
- API Profile (context for validation)
- Finding objects (from scenarios)
- Response pattern matching (from profile)

**Output:** List[ValidatedFinding] with confidence levels and suppression flags

### 4. Enhanced BaseScenario

**Purpose:** Provide API profile access to scenarios without breaking existing code

**Location:** `api_pentest/scenarios/base_scenario.py` (ENHANCED)

**New Methods:**
```python
class BaseScenario:
    # EXISTING methods unchanged (make_request, log_finding, etc.)

    # NEW methods for adaptive behavior
    def get_profile(self) -> APIProfile:
        """Access shared API profile"""

    def is_endpoint_protected(self, endpoint: Endpoint) -> bool:
        """Check if endpoint requires auth (uses profile)"""

    def should_skip_test(self, test_name: str, endpoint: Endpoint) -> bool:
        """Adaptive test selection based on profile"""

    def is_true_success(self, evidence: Evidence) -> bool:
        """Smart success detection (status + body check)"""
```

**Backward Compatibility:**
- Existing scenarios work unchanged (new methods optional)
- Profile defaults to None if not available (graceful degradation)
- `is_success_status()` remains but deprecated in favor of `is_true_success()`

**Integration Pattern:**
Scenarios can **opt-in** to adaptive behavior:

```python
# OLD WAY (still works)
if self.is_success_status(evidence.response_status):
    self.log_finding(...)

# NEW WAY (adaptive)
if self.is_true_success(evidence) and self.is_endpoint_protected(endpoint):
    self.log_finding(...)
```

## Data Flow Detail

### Phase 1: Initialization (Existing + Enhanced)

```
1. CLI parses args
2. PentestRunner.parse_input()
   → InputDetector detects format
   → OpenAPI parser extracts endpoints + security definitions
   → List[Endpoint] + Dict[security_schemes]
```

### Phase 2: Profile Building (NEW)

```
3. PentestRunner.build_profile()
   ├─→ DiscoveryEngine.discover(endpoints, spec)
   │   ├─→ Probe public endpoint (GET /, OPTIONS *)
   │   ├─→ Detect auth scheme (401/403 response analysis)
   │   ├─→ Classify endpoints (security definitions + probes)
   │   └─→ Learn response patterns (sample requests)
   │
   └─→ APIProfiler.build_profile(spec, discovery, endpoints)
       ├─→ Merge spec + discovery (resolve conflicts)
       ├─→ Enrich endpoints with metadata
       └─→ Return APIProfile
```

### Phase 3: Scenario Execution (Enhanced)

```
4. For each scenario:
   ├─→ scenario.setup(endpoints, oauth, http, config, profile)  ← profile added
   ├─→ scenario.get_test_cases()
   │   └─→ Uses profile.should_skip_test() for filtering
   │
   ├─→ scenario.execute_test(test_case)
   │   ├─→ make_request() with evidence capture
   │   └─→ is_true_success(evidence) ← uses profile patterns
   │
   └─→ scenario.log_finding() → Finding with endpoint + evidence
```

### Phase 4: Validation (NEW)

```
5. ValidationEngine.validate_findings(all_findings, profile)
   ├─→ For each finding:
   │   ├─→ Check suppression rules (public endpoint, login, etc.)
   │   ├─→ Validate evidence completeness
   │   ├─→ Assign confidence level
   │   └─→ Keep or suppress
   │
   └─→ Return List[ValidatedFinding]
```

### Phase 5: Reporting (Enhanced)

```
6. ReportGenerator.generate(validated_findings)
   ├─→ Group by severity + confidence
   ├─→ Include profile summary in report header
   ├─→ Escape HTML for XSS prevention (issues.md #8)
   └─→ Write JSON + HTML reports
```

## Build Order / Dependency Graph

```
Phase 1: Foundation
├─→ Response Analysis (deepdiff, jsonschema)
├─→ API Profile Model (pydantic)
└─→ Enhanced BaseScenario (is_true_success method)

Phase 2: Discovery
├─→ Discovery Engine (depends on: http_client, openapi parser)
└─→ API Profiler (depends on: Discovery Engine, Profile Model)

Phase 3: Validation
└─→ Validation Engine (depends on: API Profile, suppression rules)

Phase 4: Integration
├─→ PentestRunner.build_profile() (orchestration)
└─→ Scenario opt-in refactoring (use new BaseScenario methods)
```

**Critical Path:** Profile Model → Discovery Engine → API Profiler → Validation Engine

## Integration with Existing Architecture

### Minimal Impact Points

**✓ No changes needed:**
- Input parsing layer (openapi_parser, postman_parser)
- OAuth2Handler (token acquisition)
- PentestHttpClient (HTTP requests)
- ReportGenerator structure (just enhanced content)
- Existing 13 scenarios (work unchanged until opted-in)

**✓ Additive changes:**
- `PentestRunner.build_profile()` method added
- `PentestRunner.run()` passes profile to scenarios
- `BaseScenario.setup()` accepts optional profile parameter
- New adaptive/ directory with 3 new modules

**✓ Breaking changes:**
- None (backward compatible)

### Rollout Strategy

1. **Phase 1**: Build adaptive components alongside existing code
2. **Phase 2**: Add profile building to PentestRunner (disabled by default via config flag)
3. **Phase 3**: Refactor one scenario at a time to use adaptive methods
4. **Phase 4**: Enable adaptive mode by default, deprecate old methods

**Config Flag:**
```yaml
adaptive:
  enabled: true  # Enable adaptive layer
  discovery: true  # Run discovery phase
  validation: true  # Apply validation engine
```

## Open Questions & Decisions Needed

1. **Profile Persistence**: Should API profiles be cached between runs?
   - **Pro**: Faster subsequent runs, avoid redundant discovery
   - **Con**: Staleness risk (API changes, profile outdated)
   - **Recommendation**: Optional caching with TTL (e.g., 24h)

2. **Discovery Scope**: How many probe requests are acceptable?
   - **Constraint**: Don't overwhelm target API
   - **Recommendation**: Max 3 probes per endpoint, configurable rate limit

3. **Validation Strictness**: Should validation engine warn or suppress?
   - **Option A**: Suppress FPs entirely (cleaner report)
   - **Option B**: Mark as "LOW CONFIDENCE" but include (user decides)
   - **Recommendation**: Suppress by default, add --show-suppressed flag

4. **Python Version**: jsonschema 4.26.0 requires Python 3.10+
   - **Check project requirement**, downgrade jsonschema if needed

5. **Profile Model Storage**: Where to persist profiles?
   - **Options**: `./profiles/`, `.planning/profiles/`, temp directory
   - **Recommendation**: `.planning/profiles/` (tracked in git if commit_docs=true)

## Research Sources

- [API Discovery and Security - Akamai](https://www.akamai.com/resources/reference-architecture/api-discovery-security)
- [API Security Tools 2026 - AccuKnox](https://accuknox.com/blog/best-api-security-tools-2026)
- [API Discovery in Distributed Architectures - Gravitee](https://www.gravitee.io/blog/api-discovery-distributed-architectures)
- [Service Discovery Design Patterns - Microservices.io](https://microservices.io/patterns/client-side-discovery.html)
- [API Security Trends 2026 - Security Boulevard](https://securityboulevard.com/2025/11/why-api-security-will-drive-appsec-in-2026-and-beyond/)

---

*Architecture research: 2026-02-04*
