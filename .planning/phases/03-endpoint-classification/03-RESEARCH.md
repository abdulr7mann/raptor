# Phase 3: Endpoint Classification - Research

**Researched:** 2026-02-04
**Domain:** API endpoint classification for false positive elimination in security testing
**Confidence:** HIGH

## Summary

Phase 3 must classify API endpoints into three categories -- `public`, `protected`, and `auth-endpoint` -- so the toolkit can skip irrelevant security tests and eliminate 5 targeted false positives. The FPs come from two sources: (1) S07 `no_auth_access` and `malformed_token_access` tests flagging public endpoints (`/`, `/books/v1`, `/createdb`) for missing authentication, and (2) S08 `sensitive_field_exposure` flagging the login endpoint (`/users/v1/login`) for returning `auth_token` in its response body.

The codebase already has partial infrastructure for this. The `OpenAPIParser` detects `security: []` (explicit no-auth) and tags endpoints with `public-no-auth`. The S07 `_test_no_auth_access` method already checks for this tag. However, this is incomplete: (a) endpoints without a `security` key that also have no global security are not tagged, (b) no path-pattern heuristics exist for Postman collections or specs without security definitions, (c) the `auth-endpoint` concept does not exist yet, and (d) S08 has no classification-awareness at all.

The solution is a standalone `EndpointClassifier` class that consumes parsed endpoints and the raw OpenAPI spec (when available), applies a three-tier classification strategy (manual overrides > OpenAPI security definitions > path-pattern heuristics), and stores classification results on each endpoint. Scenarios then check classification before logging findings. No new external libraries are needed -- this is pure Python logic using existing data structures.

**Primary recommendation:** Build an `EndpointClassifier` in `api_pentest/core/endpoint_classifier.py` that classifies endpoints using a three-tier strategy and stores the result as a new `classification` field on the `Endpoint` dataclass. Integrate into the runner between parsing and scenario execution, and update S07 and S08 to consult classification before logging findings.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `re` | N/A | Path-pattern matching for heuristic classification | Already used throughout codebase |
| Python stdlib `logging` | N/A | Classification decision logging for audit trail | Consistent with codebase logging |
| Python stdlib `dataclasses` | N/A | Classification data structures | Consistent with existing models.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `enum` | N/A | EndpointClassification enum | For type-safe classification values |
| PyYAML (existing) | N/A | Reading endpoint_overrides from config | Already a project dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Simple enum classification | Full probability-based scoring | Overkill -- three categories with boolean confidence is sufficient for 5 FPs |
| Standalone classifier class | Inline logic in each scenario | Violates DRY, makes audit trail impossible, harder to test |
| Path regex heuristics | NLP-based endpoint naming analysis | Way too complex for deterministic patterns like /login, /register |

**Installation:**
```bash
# No new dependencies needed -- pure Python stdlib + existing PyYAML
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  core/
    endpoint_classifier.py  # NEW: EndpointClassifier + EndpointClassification enum
    models.py               # MODIFIED: Add classification field to Endpoint
    openapi_parser.py       # UNCHANGED (already extracts security info)
    response_patterns.py    # UNCHANGED
  scenarios/
    base_scenario.py        # MODIFIED: Add classification helper methods
    s07_access_controls.py  # MODIFIED: Consult classification before flagging
    s08_api_responses.py    # MODIFIED: Consult classification for auth-endpoint
  runner.py                 # MODIFIED: Run classifier after parsing, before scenarios
```

### Pattern 1: Three-Tier Classification Strategy
**What:** Classification priority: manual overrides > OpenAPI security definitions > path-pattern heuristics
**When to use:** Every endpoint classification decision
**Why:** Deterministic, auditable, allows user control while having sensible defaults

```python
# Classification priority chain
class EndpointClassifier:
    def classify(self, endpoint: Endpoint) -> EndpointClassification:
        # 1. Check manual overrides from config
        override = self._check_overrides(endpoint)
        if override is not None:
            return override

        # 2. Check OpenAPI security definitions (when spec available)
        if self.openapi_spec is not None:
            classification = self._classify_from_openapi(endpoint)
            if classification is not None:
                return classification

        # 3. Fall back to path-pattern heuristics
        return self._classify_from_path_patterns(endpoint)
```

### Pattern 2: Classification Stored on Endpoint
**What:** Add `classification` field to `Endpoint` dataclass, set during classification pass
**When to use:** After parsing, before scenario execution
**Why:** Each scenario gets classification for free without re-computing; consistent with how `tags` already works

```python
# In models.py
class EndpointClassification(Enum):
    PUBLIC = "public"           # No auth required
    PROTECTED = "protected"     # Auth required (default)
    AUTH_ENDPOINT = "auth-endpoint"  # Returns credentials by design

@dataclass
class Endpoint:
    # ... existing fields ...
    classification: EndpointClassification = EndpointClassification.PROTECTED
    classification_reason: str = ""  # Audit trail: why this classification
```

### Pattern 3: Scenario Integration via BaseScenario Helpers
**What:** Add `is_public_endpoint()` and `is_auth_endpoint()` helper methods to BaseScenario
**When to use:** Scenarios check before logging auth-missing or data-exposure findings
**Why:** Clean API, scenarios don't need to understand classification internals

```python
# In base_scenario.py
def is_public_endpoint(self, endpoint: Endpoint) -> bool:
    return endpoint.classification == EndpointClassification.PUBLIC

def is_auth_endpoint(self, endpoint: Endpoint) -> bool:
    return endpoint.classification == EndpointClassification.AUTH_ENDPOINT
```

### Anti-Patterns to Avoid
- **Classification inside scenarios:** Each scenario re-implementing classification logic leads to inconsistency. Classification must be centralized.
- **Global public/protected lists:** Hardcoding endpoint paths defeats the purpose. Use the spec and heuristics.
- **Overriding classification based on test results:** Classification is a pre-test decision. Don't change classification because a test succeeded -- that conflates classification with findings.
- **Suppressing findings silently:** Always log why a test was skipped with the classification reason. Security professionals need audit trails.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI security parsing | Custom JSON traversal for security field | Existing `openapi_parser.py` logic + `public-no-auth` tag | Parser already handles `security: []`, `security: [{...}]`, and global security inheritance |
| YAML config parsing | Custom config loader | Existing `load_config()` in `run_pentest.py` + PyYAML | Config loading already works, just add new keys |
| Endpoint path extraction | Custom URL parsing | `urllib.parse.urlparse` | Already used in S07 and S08 |

**Key insight:** The OpenAPI parser already extracts security information and tags endpoints. The classifier does not need to re-parse the spec for most cases -- it can read the existing `security_schemes` and `tags` fields on the `Endpoint` dataclass. Direct spec access is only needed for the no-security-key-inherits-global case.

## Common Pitfalls

### Pitfall 1: Confusing "No Security Key" with "Public"
**What goes wrong:** In OpenAPI 3.0, an operation without a `security` key *inherits* global security. Only `security: []` explicitly means "no auth required." Treating missing security key as public would mis-classify protected endpoints.
**Why it happens:** Intuition says "no security definition = no security required," but the OpenAPI spec says "inherit from global."
**How to avoid:** Implement the exact OpenAPI spec rules:
  - `security: []` at operation level = public (overrides global)
  - `security: [{}]` at operation level = optionally public
  - No `security` key at operation level = inherit global security
  - No global `security` key = no global requirement (operation is public unless it defines its own)
**Warning signs:** Endpoints that have `security_schemes == []` but should be protected.

### Pitfall 2: VAmPI Has No Global Security (Special Case)
**What goes wrong:** The VAmPI OpenAPI spec has no top-level `security` key. This means endpoints without a per-operation `security` key are genuinely public. But many real-world specs DO have global security, so the same pattern (no per-operation key) would mean "protected by global auth."
**Why it happens:** The parser currently only detects `security: []` as explicitly public. Endpoints like `/`, `/books/v1 GET`, `/createdb` have NO security key at all, but VAmPI has no global security either -- so they are public.
**How to avoid:** The classifier must check BOTH the per-operation security AND the global security to determine classification:
  - If global security exists AND operation has no security key: classify as `protected`
  - If no global security AND operation has no security key: classify as `public`
  - If operation has `security: []`: classify as `public` (overrides global)
  - If operation has `security: [{scheme}]`: classify as `protected`
**Warning signs:** The existing `public-no-auth` tag misses endpoints in VAmPI that are actually public.

### Pitfall 3: Login Detection Is Not Just Path Matching
**What goes wrong:** Classifying `/login` by path alone might miss `/auth/token`, `/oauth/token`, `/api/authenticate`, or custom auth endpoints.
**Why it happens:** Auth endpoints have diverse naming conventions.
**How to avoid:** Combine path patterns with response analysis: (a) path matches login/auth/token/register patterns, AND/OR (b) the OpenAPI response schema mentions auth_token/access_token/token fields. For Phase 3, path patterns are sufficient for the targeted FPs, but the classifier should be extensible.
**Warning signs:** Real-world APIs with non-standard auth endpoint names.

### Pitfall 4: Overly Aggressive Classification Suppresses Real Findings
**What goes wrong:** Making too many endpoints "public" suppresses legitimate auth-missing findings.
**Why it happens:** Confidence threshold too low, or path heuristics too broad.
**How to avoid:** Per CONTEXT.md decision: default to `protected` when confidence is low. Only suppress when classification is confident (OpenAPI security definitions present, or strong path-pattern match). Heuristic-only classification should require multiple signals.
**Warning signs:** True positive count drops after classification is deployed.

### Pitfall 5: Postman Collections Have No Security Metadata
**What goes wrong:** Postman collections lack OpenAPI-style security definitions, so the OpenAPI classification tier is unavailable.
**Why it happens:** Postman auth is per-request, not declaratively structured.
**How to avoid:** For Postman inputs, the classifier falls through to path-pattern heuristics only. Manual overrides in config become more important for Postman users. This is acceptable -- the FPs we are targeting are from OpenAPI specs.
**Warning signs:** Postman users getting different classification behavior than OpenAPI users.

## Code Examples

### OpenAPI Security Classification Logic
```python
# Source: OpenAPI 3.0 spec rules verified against official documentation
def _classify_from_openapi(self, endpoint: Endpoint) -> EndpointClassification | None:
    """Classify using OpenAPI security definitions."""

    # Existing parser already tags security: [] as "public-no-auth"
    if "public-no-auth" in endpoint.tags:
        return EndpointClassification.PUBLIC

    # Endpoint has explicit security schemes = protected
    if endpoint.security_schemes:
        return EndpointClassification.PROTECTED

    # No per-operation security and no security_schemes populated:
    # Check if global security exists in the raw spec
    if self._has_global_security():
        # Inherits global security = protected
        return EndpointClassification.PROTECTED
    else:
        # No global security, no per-operation security = public
        return EndpointClassification.PUBLIC
```

### Path-Pattern Heuristic Rules
```python
# Source: Common API path conventions + VAmPI analysis
import re

# Auth-endpoint patterns (returns credentials by design)
AUTH_ENDPOINT_PATTERNS = re.compile(
    r"/(login|signin|sign-in|authenticate|auth/token|oauth/token|"
    r"token$|session$)",
    re.IGNORECASE,
)

# Public endpoint patterns (no auth expected)
PUBLIC_PATH_PATTERNS = re.compile(
    r"/(register|signup|sign-up|"
    r"health|healthz|readyz|status|ping|version|"
    r"createdb|resetdb|initdb|"
    r"docs|swagger|openapi|api-docs|redoc)$",
    re.IGNORECASE,
)

# Root path is typically public
def _is_root_path(self, path: str) -> bool:
    return path.rstrip("/") == "" or path == "/"

def _classify_from_path_patterns(self, endpoint: Endpoint) -> EndpointClassification:
    """Classify using URL path heuristics."""
    from urllib.parse import urlparse
    path = urlparse(endpoint.url).path

    # Check auth-endpoint patterns first (more specific)
    if self.AUTH_ENDPOINT_PATTERNS.search(path):
        return EndpointClassification.AUTH_ENDPOINT

    # Check public patterns
    if self.PUBLIC_PATH_PATTERNS.search(path) or self._is_root_path(path):
        return EndpointClassification.PUBLIC

    # Default: protected
    return EndpointClassification.PROTECTED
```

### S07 Integration Example
```python
# In S07._test_no_auth_access() -- replace existing is_public check
def _test_no_auth_access(self):
    for ep in self.endpoints:
        # Skip public endpoints -- no auth expected
        if self.is_public_endpoint(ep):
            logger.debug(
                "Skipping no-auth test for %s %s: %s",
                ep.method, ep.url, ep.classification_reason,
            )
            continue

        evidence = self.make_request(ep, token=None)
        if self.is_success_status(evidence.response_status):
            # ... log finding as before ...
```

### S08 Integration Example
```python
# In S08._test_sensitive_field_exposure() -- skip auth-token fields for auth-endpoints
EXPECTED_AUTH_FIELDS = {"auth_token", "access_token", "refresh_token", "token", "session_token"}

for ep in self.endpoints:
    evidence = self.make_request(ep, token=token)
    if not self.is_success_status(evidence.response_status):
        continue

    field_matches = self.SENSITIVE_FIELD_PATTERNS.findall(body)
    if field_matches:
        # Filter out expected fields for auth-endpoints
        if self.is_auth_endpoint(ep):
            field_matches = [f for f in field_matches if f.lower() not in EXPECTED_AUTH_FIELDS]

        if field_matches:
            # ... log finding with remaining unexpected fields ...
```

### Config Override Format
```yaml
# In pentest.yaml / vampi_config.yaml
endpoint_overrides:
  - path: "/custom-public-endpoint"
    classification: "public"
  - path: "/internal/login"
    classification: "auth-endpoint"
  - path: "/api/health"
    classification: "public"
```

### Runner Integration Point
```python
# In runner.py, after parse_input() and before run() scenarios
from api_pentest.core.endpoint_classifier import EndpointClassifier

# In run() method, after self.parse_input()
classifier = EndpointClassifier(
    endpoints=self.endpoints,
    openapi_spec=self._get_raw_spec(),  # Raw spec for global security check
    config=self.config,
)
classifier.classify_all()
# Classification results stored on each endpoint.classification
```

## Exact FP Mapping

The 5 FPs this phase must eliminate, with their exact locations in code:

### FP Group 1: S07 no_auth_access on public endpoints (3 FPs)
**Endpoints:** `GET /`, `GET /books/v1`, `GET /createdb`
**Why they are FPs:** These endpoints have no `security` key in the OpenAPI spec, and VAmPI has no global security -- they are genuinely public.
**Current code:** `s07_access_controls.py:_test_no_auth_access()` lines 62-89. Checks `is_public = "public-no-auth" in ep.tags` but these endpoints don't have that tag because they lack `security: []` -- they simply have no security key at all.
**Fix:** The classifier will mark these as `public` (via OpenAPI tier: no global security + no per-operation security). S07 will check `is_public_endpoint(ep)` and skip.

### FP Group 2: S07 malformed_token_access on public endpoint (1 FP)
**Endpoint:** `GET /` (first endpoint tested)
**Why it is an FP:** Empty token accepted because the endpoint doesn't require auth at all.
**Current code:** `s07_access_controls.py:_test_malformed_token_access()` lines 110-143. Tests `self.endpoints[:5]` which includes `/` as the first endpoint. No classification check.
**Fix:** Skip public endpoints in malformed_token_access test.

### FP Group 3: S08 sensitive_field_exposure on login endpoint (1 FP)
**Endpoint:** `POST /users/v1/login`
**Why it is an FP:** Login endpoint returning `auth_token` is expected behavior, not data exposure.
**Current code:** `s08_api_responses.py:_test_sensitive_field_exposure()` lines 78-116. `SENSITIVE_FIELD_PATTERNS` includes `auth_token`. No check for auth-endpoint purpose.
**Fix:** The classifier will mark `/users/v1/login` as `auth-endpoint` (via path-pattern heuristic matching `/login`). S08 will filter out expected auth fields for auth-endpoints.

### Note on "S06 on /login" from FIX-02
The requirements mention "S06 on /login" but the S06 scenario (`_test_admin_endpoint_access`) skips when no admin endpoints are detected. In the VAmPI test results, S06 produced 0 findings -- only SKIPs and PASSes. This FP may have been from an earlier run before Phase 2 fixes. The S07 malformed_token_access FP on `/` accounts for the 4th auth-related FP. If S06 does produce a /login FP in some configurations, the classifier handles it the same way: skip auth tests on public/auth-endpoints.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `"public-no-auth" in ep.tags` check only in S07 | Centralized EndpointClassifier with three-tier strategy | Phase 3 (this phase) | Covers all cases: explicit security:[], missing security key with no global, and path heuristics |
| No auth-endpoint concept | `auth-endpoint` classification category | Phase 3 (this phase) | Eliminates login token exposure FP |
| No manual override capability | `endpoint_overrides` in YAML config | Phase 3 (this phase) | User control for edge cases |

**Preserved:**
- `public-no-auth` tag from OpenAPI parser continues to work as one signal fed into the classifier
- `is_success_status()` and `is_real_success()` unchanged -- classification is orthogonal to response validation
- All existing scenario tests continue to run for `protected` endpoints

## Open Questions

1. **S07 malformed_token_access endpoint selection**
   - What we know: Currently tests `self.endpoints[:5]`, which includes public endpoints
   - What's unclear: Should malformed_token_access also skip `auth-endpoint` classified endpoints? (Malformed tokens to login endpoints may be legitimate tests)
   - Recommendation: Skip only `public` endpoints for malformed_token_access. Auth-endpoints should still reject malformed tokens.

2. **S07 _test_undocumented_methods scope**
   - What we know: Tests undocumented HTTP methods on first 10 endpoints
   - What's unclear: Should undocumented methods tests be skipped for public endpoints? (Public endpoints accepting undocumented methods could still be a vulnerability)
   - Recommendation: Do NOT skip undocumented methods for public endpoints -- those tests are about method restriction, not auth.

3. **S07 _test_cors_misconfiguration scope**
   - What we know: Tests CORS on first 5 endpoints
   - What's unclear: Should CORS tests be skipped for public endpoints?
   - Recommendation: Do NOT skip CORS tests for public endpoints -- CORS misconfiguration is about data access control, not authentication.

## Sources

### Primary (HIGH confidence)
- OpenAPI Specification v3.0.3 (https://spec.openapis.org/oas/v3.0.3.html) -- Security field inheritance rules, empty array semantics
- Swagger.io Authentication Docs (https://swagger.io/docs/specification/v3_0/authentication/) -- Public endpoint pattern with `security: []`
- Codebase analysis -- `openapi_parser.py`, `models.py`, `base_scenario.py`, `s07_access_controls.py`, `s08_api_responses.py`, `runner.py`, `vampi_openapi.json`

### Secondary (MEDIUM confidence)
- OpenAPI Learn Docs (https://learn.openapis.org/specification/security.html) -- Security scheme usage patterns
- Swagger 2.0 Authentication Docs (https://swagger.io/docs/specification/v2_0/authentication/authentication/) -- Confirmed same `security: []` pattern for Swagger 2.0

### Tertiary (LOW confidence)
- None -- all findings verified against official spec or codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pure Python, no new dependencies, verified against codebase
- Architecture: HIGH -- pattern follows Phase 2 precedent (standalone class, runner integration, scenario helpers), verified against existing code structure
- Pitfalls: HIGH -- OpenAPI security rules verified against official spec; VAmPI spec analyzed directly; FP mapping verified against actual report data
- Code examples: HIGH -- derived from reading actual codebase, not hypothetical

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable domain, no external dependency changes expected)
