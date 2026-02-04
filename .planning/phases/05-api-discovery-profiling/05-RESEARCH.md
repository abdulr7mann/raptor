# Phase 5: API Discovery & Profiling - Research

**Researched:** 2026-02-04
**Domain:** API authentication detection, architecture fingerprinting, GraphQL introspection, profile persistence
**Confidence:** HIGH

## Summary

Phase 5 builds a discovery engine that probes an API to identify its authentication scheme(s), architecture type (REST/GraphQL/SOAP), and constructs a reusable JSON profile aggregating all learned information. The phase does NOT execute security tests -- it only observes and records.

The core architecture follows a two-tier strategy locked by CONTEXT.md: spec-first extraction (parse OpenAPI `securityDefinitions`/`components.securitySchemes`), then active probing as fallback (send unauthenticated requests, parse `WWW-Authenticate` headers and 401/403 patterns). This approach is directly implementable because the codebase already has `OpenAPIParser._extract_security_schemes()` which returns raw scheme dicts, and `PentestHttpClient` which captures full response headers in Evidence objects. The existing `PrerequisiteChecker` (Phase 4) establishes the pattern: standalone detector class in `api_pentest/core/`, integrated into runner's pre-scan flow, with results passed to downstream consumers.

GraphQL detection requires checking well-known endpoints (`/graphql`, `/api/graphql`, `/gql`) with introspection queries. The standard introspection query uses the `__schema` root field to extract `queryType`, `mutationType`, `subscriptionType`, and all types with their fields. When introspection is disabled (common in production), the profile records `introspection_available: false` and logs the limitation. Clairvoyance-style blind probing is out of scope per CONTEXT.md -- the requirement is to "attempt introspection," not guarantee discovery when disabled.

The profile is a single JSON file with a schema version field, content hash for staleness detection, and all discovered metadata. It integrates Phase 2 (response patterns) and Phase 3 (endpoint classifications) data, making it the single source of truth about a target API's characteristics.

**Primary recommendation:** Build an `ApiDiscovery` module in `api_pentest/core/api_discovery.py` with `AuthDetector`, `ArchitectureDetector`, and `ApiProfiler` classes. Run discovery after endpoint classification (Phase 3) and prerequisite detection (Phase 4), before scenarios. Persist profile to JSON in a `profiles/` directory. Integrate into `runner.py` following the established pre-scan pattern.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | N/A | Profile and detection result data structures | Consistent with models.py, prerequisite_detector.py |
| Python stdlib `hashlib` | N/A | SHA-256 hash of input spec + base URL for staleness detection | Standard library, deterministic, no external deps |
| Python stdlib `json` | N/A | Profile serialization/deserialization | Already used throughout codebase |
| Python stdlib `enum` | N/A | AuthSchemeType, ArchitectureType enums | Consistent with existing enums in models.py |
| Python stdlib `pathlib` | N/A | Profile file path management | Already used in InputDetector |
| Python stdlib `logging` | N/A | Discovery progress and gap logging | Consistent with codebase convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requests` (existing) | 2.32.4 | HTTP requests via PentestHttpClient | Already a project dependency |
| `pyyaml` (existing) | 6.0.2 | Config loading (already installed) | If config extensions needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom auth detection | `openapi3` Python lib for spec parsing | Overkill -- we only need securitySchemes extraction, which is 10 lines of dict access already in OpenAPIParser |
| Custom GraphQL introspection | `graphql-core`'s `get_introspection_query()` | Would add a heavy dependency for one query string; the standard introspection query is a static string we embed |
| hashlib SHA-256 for staleness | File modification time | Content hash is deterministic and spec-change-aware; mtime fails if spec is regenerated with same content |

**Installation:**
```bash
# No new dependencies needed -- pure Python using existing project dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  core/
    api_discovery.py         # NEW: AuthDetector, ArchitectureDetector, ApiProfiler, ApiProfile
    models.py                # MODIFIED: Add AuthScheme, ArchitectureType, ApiProfile dataclasses
    openapi_parser.py        # READ ONLY: _extract_security_schemes() already exists
    http_client.py           # READ ONLY: Evidence already captures headers
    endpoint_classifier.py   # READ ONLY: classifications consumed by profile
    response_patterns.py     # READ ONLY: patterns consumed by profile
    prerequisite_detector.py # READ ONLY: prerequisite results consumed by profile
    ...
  runner.py                  # MODIFIED: Add discovery step after prereq detection, before scenarios
profiles/                    # NEW: Directory for persisted API profiles
  vampi-api.profile.json     # Example profile output
```

### Pattern 1: Spec-First, Probe-Second Auth Detection
**What:** Extract auth schemes from OpenAPI spec first, then probe unauthenticated to fill gaps.
**When to use:** Every discovery run.
**Why:** CONTEXT.md locked decision: "extract auth schemes from OpenAPI securityDefinitions/components.securitySchemes when available -- cheapest, most reliable signal."

```python
# Source: OpenAPI 3.0 spec (learn.openapis.org/specification/security.html)
# and Swagger 2.0 spec (swagger.io/docs/specification)

from dataclasses import dataclass, field
from enum import Enum

class AuthSchemeType(Enum):
    BEARER = "bearer"
    API_KEY = "apiKey"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    SESSION_COOKIE = "session_cookie"
    OPENID_CONNECT = "openIdConnect"
    UNKNOWN = "unknown"

@dataclass
class DetectedAuthScheme:
    scheme_type: AuthSchemeType
    name: str                          # e.g. "bearerAuth", "api_key"
    source: str                        # "spec" or "probe"
    details: dict = field(default_factory=dict)  # scheme-specific info
    # For apiKey: {"in": "header", "name": "X-API-Key"}
    # For bearer: {"format": "JWT"}
    # For oauth2: {"flows": {"clientCredentials": {"tokenUrl": "..."}}}
    endpoints: list[str] = field(default_factory=list)  # which endpoints use this scheme

class AuthDetector:
    """Detects authentication schemes using spec extraction + active probing."""

    def __init__(self, openapi_spec: dict | None, http_client, endpoints, base_url: str):
        self.spec = openapi_spec
        self.http = http_client
        self.endpoints = endpoints
        self.base_url = base_url

    def detect(self) -> list[DetectedAuthScheme]:
        schemes = []
        # Tier 1: Spec extraction
        if self.spec:
            schemes.extend(self._extract_from_spec())
        # Tier 2: Active probing (fills gaps)
        if not schemes:
            schemes.extend(self._probe_unauthenticated())
        return schemes

    def _extract_from_spec(self) -> list[DetectedAuthScheme]:
        """Extract from securityDefinitions (Swagger 2.0) or
        components.securitySchemes (OpenAPI 3.x)."""
        raw_schemes = {}
        if "securityDefinitions" in self.spec:
            raw_schemes = self.spec["securityDefinitions"]
        elif "components" in self.spec:
            raw_schemes = self.spec.get("components", {}).get("securitySchemes", {})

        detected = []
        for name, scheme_def in raw_schemes.items():
            scheme_type = self._map_spec_type(scheme_def)
            detected.append(DetectedAuthScheme(
                scheme_type=scheme_type,
                name=name,
                source="spec",
                details=self._extract_scheme_details(scheme_def),
                endpoints=self._find_endpoints_using_scheme(name),
            ))
        return detected

    def _map_spec_type(self, scheme_def: dict) -> AuthSchemeType:
        """Map OpenAPI type field to AuthSchemeType enum."""
        spec_type = scheme_def.get("type", "").lower()
        if spec_type == "http":
            http_scheme = scheme_def.get("scheme", "").lower()
            if http_scheme == "bearer":
                return AuthSchemeType.BEARER
            elif http_scheme == "basic":
                return AuthSchemeType.BASIC
            return AuthSchemeType.UNKNOWN
        elif spec_type == "apikey":
            return AuthSchemeType.API_KEY
        elif spec_type == "oauth2":
            return AuthSchemeType.OAUTH2
        elif spec_type == "openidconnect":
            return AuthSchemeType.OPENID_CONNECT
        # Swagger 2.0 uses type: "basic" directly
        elif spec_type == "basic":
            return AuthSchemeType.BASIC
        return AuthSchemeType.UNKNOWN
```

### Pattern 2: WWW-Authenticate Header Probing
**What:** Send unauthenticated requests and parse 401 response headers per RFC 7235.
**When to use:** When no spec is available or spec lacks security info.
**Why:** CONTEXT.md: "Active probing as fallback: probe endpoints with unauthenticated requests and parse WWW-Authenticate headers."

```python
# Source: RFC 7235 (rfc-editor.org/rfc/rfc7235)
# and MDN WWW-Authenticate (developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/WWW-Authenticate)

import re

def _probe_unauthenticated(self) -> list[DetectedAuthScheme]:
    """Send unauthenticated requests, parse 401/403 responses."""
    schemes = []
    seen_types = set()

    # Select 3-5 representative endpoints (mix of GET and POST)
    probe_endpoints = self._select_probe_endpoints(count=5)

    for ep in probe_endpoints:
        if ep.method.upper() not in ("GET", "HEAD", "OPTIONS"):
            # For non-safe methods during discovery, use HEAD or OPTIONS
            evidence = self.http.request(
                method="HEAD", url=ep.url, headers={},
            )
        else:
            evidence = self.http.request(
                method=ep.method, url=ep.url, headers={},
            )

        if evidence.response_status in (401, 403):
            detected = self._parse_www_authenticate(evidence)
            for d in detected:
                if d.scheme_type not in seen_types:
                    seen_types.add(d.scheme_type)
                    schemes.append(d)
            # Also detect cookie-based auth from Set-Cookie
            cookie_scheme = self._detect_session_cookie(evidence)
            if cookie_scheme and AuthSchemeType.SESSION_COOKIE not in seen_types:
                seen_types.add(AuthSchemeType.SESSION_COOKIE)
                schemes.append(cookie_scheme)

    return schemes

def _parse_www_authenticate(self, evidence) -> list[DetectedAuthScheme]:
    """Parse WWW-Authenticate header per RFC 7235.

    Syntax: challenge = auth-scheme [ 1*SP ( token68 / #auth-param ) ]
    Examples:
      WWW-Authenticate: Bearer realm="example"
      WWW-Authenticate: Basic realm="api"
      WWW-Authenticate: Bearer, Basic realm="api"
    """
    schemes = []
    www_auth = None
    for header_name, header_val in evidence.response_headers.items():
        if header_name.lower() == "www-authenticate":
            www_auth = header_val
            break

    if not www_auth:
        # No WWW-Authenticate header -- infer from status code patterns
        return self._infer_from_status(evidence)

    # Parse multiple challenges (comma-separated at top level)
    # RFC 7235: challenges can be comma-separated in one header
    # Simple approach: split on scheme keywords
    scheme_pattern = re.compile(
        r'\b(Bearer|Basic|Digest|Negotiate|HOBA|OAuth)\b',
        re.IGNORECASE,
    )
    matches = scheme_pattern.finditer(www_auth)

    for match in matches:
        scheme_name = match.group(1).lower()
        scheme_type_map = {
            "bearer": AuthSchemeType.BEARER,
            "basic": AuthSchemeType.BASIC,
            "digest": AuthSchemeType.UNKNOWN,  # We track but don't deeply support
            "negotiate": AuthSchemeType.UNKNOWN,
            "hoba": AuthSchemeType.UNKNOWN,
            "oauth": AuthSchemeType.OAUTH2,
        }
        scheme_type = scheme_type_map.get(scheme_name, AuthSchemeType.UNKNOWN)

        # Extract realm if present
        realm_match = re.search(r'realm="([^"]*)"', www_auth[match.start():])
        realm = realm_match.group(1) if realm_match else ""

        schemes.append(DetectedAuthScheme(
            scheme_type=scheme_type,
            name=scheme_name,
            source="probe",
            details={"realm": realm, "raw_header": www_auth},
        ))

    return schemes
```

### Pattern 3: Architecture Detection
**What:** Determine if the API is REST, GraphQL, SOAP, or hybrid.
**When to use:** Every discovery run.
**Why:** DISC-04 requirement: "Detect API architecture type."

```python
class ArchitectureType(Enum):
    REST = "REST"
    GRAPHQL = "GraphQL"
    SOAP = "SOAP"
    GRPC_WEB = "gRPC-web"   # gRPC over HTTP (browser-facing)
    HYBRID = "hybrid"        # Multiple types detected
    UNKNOWN = "unknown"

class ArchitectureDetector:
    """Detects API architecture type from spec and probing."""

    GRAPHQL_PATHS = ["/graphql", "/api/graphql", "/gql", "/query"]

    def __init__(self, openapi_spec: dict | None, http_client, base_url: str):
        self.spec = openapi_spec
        self.http = http_client
        self.base_url = base_url.rstrip("/")

    def detect(self) -> tuple[ArchitectureType, dict]:
        """Returns (architecture_type, details_dict)."""
        signals = {
            "rest": False,
            "graphql": False,
            "soap": False,
        }
        details = {}

        # Spec signals
        if self.spec:
            if self.spec.get("openapi") or self.spec.get("swagger"):
                signals["rest"] = True
            # Check for GraphQL paths in spec
            paths = self.spec.get("paths", {})
            for path_key in paths:
                if any(gql_path in path_key.lower()
                       for gql_path in self.GRAPHQL_PATHS):
                    signals["graphql"] = True

        # Active probing: check for GraphQL endpoints
        graphql_result = self._probe_graphql()
        if graphql_result:
            signals["graphql"] = True
            details["graphql"] = graphql_result

        # Count signals
        detected = [k for k, v in signals.items() if v]
        if len(detected) > 1:
            return ArchitectureType.HYBRID, details
        elif "graphql" in detected:
            return ArchitectureType.GRAPHQL, details
        elif "soap" in detected:
            return ArchitectureType.SOAP, details
        elif "rest" in detected:
            return ArchitectureType.REST, details
        else:
            return ArchitectureType.UNKNOWN, details
```

### Pattern 4: GraphQL Introspection
**What:** Detect GraphQL endpoints and attempt schema introspection.
**When to use:** During architecture detection.
**Why:** DISC-06 requirement: "GraphQL schema introspection."

```python
# Source: graphql.org/learn/introspection/
# and github gist craigbeck/b90915d49fda19d5b2b17ead14dcd6da

# The standard introspection query (top-level only per CONTEXT.md)
GRAPHQL_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          type {
            kind
            name
            ofType { kind name ofType { kind name } }
          }
          defaultValue
        }
        type {
          kind
          name
          ofType { kind name ofType { kind name } }
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        type {
          kind
          name
          ofType { kind name }
        }
        defaultValue
      }
      interfaces { kind name }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes { kind name }
    }
    directives {
      name
      description
      locations
      args {
        name
        type {
          kind
          name
          ofType { kind name }
        }
        defaultValue
      }
    }
  }
}
"""

def _probe_graphql(self) -> dict | None:
    """Check common GraphQL endpoints and attempt introspection."""
    for path in self.GRAPHQL_PATHS:
        url = f"{self.base_url}{path}"

        # Step 1: Send introspection query
        evidence = self.http.request(
            method="POST",
            url=url,
            headers={"Content-Type": "application/json"},
            body={"query": GRAPHQL_INTROSPECTION_QUERY},
        )

        if evidence.response_status == 200:
            try:
                body = json.loads(evidence.response_body)
                if "data" in body and "__schema" in body.get("data", {}):
                    schema = body["data"]["__schema"]
                    return {
                        "endpoint": url,
                        "introspection_available": True,
                        "query_type": schema.get("queryType", {}).get("name"),
                        "mutation_type": schema.get("mutationType", {}).get("name"),
                        "subscription_type": schema.get("subscriptionType", {}).get("name"),
                        "type_count": len(schema.get("types", [])),
                        "directive_count": len(schema.get("directives", [])),
                    }
                elif "errors" in body:
                    # GraphQL endpoint exists but introspection disabled
                    return {
                        "endpoint": url,
                        "introspection_available": False,
                        "reason": "Introspection query returned errors",
                    }
            except (json.JSONDecodeError, TypeError):
                continue

        # Step 2: Try GET with query param (some servers support this)
        evidence_get = self.http.request(
            method="GET",
            url=f"{url}?query={{__typename}}",
            headers={},
        )
        if evidence_get.response_status == 200:
            try:
                body = json.loads(evidence_get.response_body)
                if "data" in body:
                    return {
                        "endpoint": url,
                        "introspection_available": False,
                        "reason": "GraphQL detected via __typename, introspection not attempted via GET",
                    }
            except (json.JSONDecodeError, TypeError):
                continue

    return None
```

### Pattern 5: API Profile with Staleness Detection
**What:** Persist discovered information as JSON with content-based staleness.
**When to use:** At the end of discovery, and at the start of each scan to check reuse.
**Why:** DISC-05 requirement: "Build API profile." CONTEXT.md: "profile includes hash of input spec + target base URL."

```python
# Source: Python stdlib hashlib (docs.python.org/3/library/hashlib.html)

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROFILE_VERSION = 1  # Increment on breaking schema changes

@dataclass
class ApiProfile:
    """Complete API profile capturing all discovery results."""
    profile_version: int = PROFILE_VERSION
    created_at: str = ""
    content_hash: str = ""         # SHA-256 of spec + base_url
    base_url: str = ""
    input_format: str = ""         # e.g. "openapi_3.0"
    endpoint_count: int = 0

    # Auth discovery
    auth_schemes: list[dict] = field(default_factory=list)

    # Architecture
    architecture_type: str = ""
    architecture_details: dict = field(default_factory=dict)

    # Endpoint classifications (from Phase 3)
    classifications: dict = field(default_factory=dict)
    # {"public": 3, "protected": 7, "auth-endpoint": 1}

    # Response patterns (from Phase 2)
    response_pattern_count: int = 0

    # Server info
    server_fingerprint: str = ""    # Server header value
    content_types_observed: list[str] = field(default_factory=list)
    security_headers: dict = field(default_factory=dict)

    # Prerequisite results (from Phase 4)
    prerequisites: dict = field(default_factory=dict)

    # Discovery gaps
    gaps: list[str] = field(default_factory=list)

def compute_content_hash(spec_data: dict | None, base_url: str) -> str:
    """Deterministic hash of spec content + base URL."""
    content = json.dumps(spec_data, sort_keys=True) if spec_data else ""
    content += f"|{base_url}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def save_profile(profile: ApiProfile, profiles_dir: str, target_name: str) -> Path:
    """Save profile to JSON file."""
    path = Path(profiles_dir)
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{target_name}.profile.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(asdict(profile), f, indent=2, default=str)
    return file_path

def load_profile(file_path: Path) -> ApiProfile | None:
    """Load profile from JSON, return None if incompatible version."""
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("profile_version", 0) != PROFILE_VERSION:
        return None  # Incompatible version triggers re-discovery
    return ApiProfile(**data)

def is_profile_stale(profile: ApiProfile, current_hash: str) -> bool:
    """Check if profile is stale by comparing content hashes."""
    return profile.content_hash != current_hash
```

### Pattern 6: Runner Integration
**What:** Discovery runs as the final pre-scan step, after classification and prerequisites.
**When to use:** Every scan run.
**Why:** Follows the established runner pattern: parse -> oauth -> http -> learn -> classify -> prereq -> discover -> scenarios.

```python
# In runner.py, after prerequisite detection and before scenario loop:
from api_pentest.core.api_discovery import ApiDiscovery

discovery = ApiDiscovery(
    openapi_spec=self._get_raw_spec(),
    http_client=self.http,
    endpoints=self.endpoints,
    config=self.config,
    response_learner=self.response_learner,
    prerequisite_results=self.prerequisite_results,
)

# Check for cached profile first
profile = discovery.load_cached_profile()
if profile and not discovery.is_stale(profile):
    self.api_profile = profile
    logger.info("Loaded cached API profile (hash match)")
else:
    self.api_profile = discovery.discover()
    discovery.save_profile(self.api_profile)
    logger.info("Discovery complete, profile saved")
```

### Anti-Patterns to Avoid
- **Probing all endpoints during discovery:** CONTEXT.md caps at ~20-30 requests. Select 3-5 representative endpoints, not all endpoints. Use HEAD/OPTIONS before full GET.
- **Mutating requests during discovery:** CONTEXT.md: "only GET, HEAD, OPTIONS; never POST/PUT/DELETE." Exception: GraphQL introspection POST is a read-only query.
- **Failing hard on incomplete discovery:** CONTEXT.md: "if discovery is incomplete, proceed with partial profile and log gaps." Never raise exceptions that halt the scan.
- **Re-running discovery when profile is still valid:** Check content hash first. Only re-discover if spec or base URL changed.
- **Building a custom WWW-Authenticate parser for all edge cases:** RFC 7235 parsing has many edge cases (multiple challenges, quoted strings, token68). Keep the parser simple -- match known scheme names (Bearer, Basic, Digest, OAuth) via regex. Don't aim for full RFC compliance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request sending | Custom urllib/socket code | Existing `PentestHttpClient.request()` | Already handles timeouts, SSL, retries, evidence capture |
| OpenAPI spec parsing | Custom JSON traversal for securitySchemes | Existing `OpenAPIParser._extract_security_schemes()` | Already handles Swagger 2.0 vs OpenAPI 3.x differences |
| JSON serialization | Custom format/encoding | `json.dumps()` + `dataclasses.asdict()` | Standard library, handles nested dataclasses |
| Content hashing | Custom hash algorithm | `hashlib.sha256()` | Standard, deterministic, collision-resistant |
| File path handling | String concatenation | `pathlib.Path` | Already used in `InputDetector`, handles cross-platform |
| Full GraphQL introspection query | Build query dynamically | Static query string constant | The standard query is well-defined and stable; no need to generate it |

**Key insight:** Phase 5 is an integration phase that aggregates data from Phases 2, 3, and 4 into a unified profile, plus adds auth/architecture detection. Most infrastructure already exists. The new code is detection logic (what to look for) and the profile aggregation/persistence layer.

## Common Pitfalls

### Pitfall 1: Swagger 2.0 vs OpenAPI 3.x Security Scheme Locations
**What goes wrong:** Code only checks `components.securitySchemes` and misses Swagger 2.0 specs that use `securityDefinitions` at the root level.
**Why it happens:** Swagger 2.0 and OpenAPI 3.x use different paths for the same concept.
**How to avoid:** Always check both locations. The existing `OpenAPIParser._extract_security_schemes()` already handles this:
  - Swagger 2.0: `data.get("securityDefinitions", {})`
  - OpenAPI 3.x: `data.get("components", {}).get("securitySchemes", {})`
**Warning signs:** Auth detection returns empty for Swagger 2.0 specs that clearly define security.

### Pitfall 2: Swagger 2.0 Type Mapping Differences
**What goes wrong:** Swagger 2.0 uses `type: "basic"` directly, while OpenAPI 3.x uses `type: "http"` with `scheme: "basic"`. Code maps only the 3.x format.
**Why it happens:** The `type` field has different valid values in different spec versions.
**How to avoid:** Map both:
  - OpenAPI 3.x: `type: "http"` + `scheme: "bearer"` -> AuthSchemeType.BEARER
  - OpenAPI 3.x: `type: "apiKey"` -> AuthSchemeType.API_KEY
  - OpenAPI 3.x: `type: "oauth2"` -> AuthSchemeType.OAUTH2
  - Swagger 2.0: `type: "basic"` -> AuthSchemeType.BASIC (direct mapping, no `scheme` field)
**Warning signs:** Swagger 2.0 basic auth specs get classified as UNKNOWN.

### Pitfall 3: GraphQL POST for Introspection Violates "No Mutation" Rule
**What goes wrong:** CONTEXT.md says "only GET, HEAD, OPTIONS; never POST/PUT/DELETE during discovery." But GraphQL introspection requires POST.
**Why it happens:** GraphQL introspection is conceptually a read operation but uses POST as its transport method.
**How to avoid:** Treat GraphQL introspection POST as an exception to the no-mutation rule. The introspection query is read-only by design -- it queries schema metadata, never mutates data. Document this exception. As additional safety, try `GET` with query parameter first (some GraphQL servers support `GET /graphql?query={__typename}`).
**Warning signs:** Overly strict HTTP method filtering blocks GraphQL detection entirely.

### Pitfall 4: WWW-Authenticate Parsing Complexity
**What goes wrong:** RFC 7235 allows multiple challenges in one header, comma-separated parameters within challenges, quoted strings with escaped characters. A naive parser breaks.
**Why it happens:** The RFC syntax is surprisingly complex: `challenge = auth-scheme [ 1*SP ( token68 / #auth-param ) ]`.
**How to avoid:** Keep the parser simple and focused. Match known scheme keywords (Bearer, Basic, Digest, OAuth) via regex. Extract realm if present. Don't try to parse unknown schemes or handle nested quoting. For this toolkit, identifying the scheme type is sufficient -- we don't need to parse every parameter.
**Warning signs:** Parser crashes or returns garbage for multi-challenge headers like `Bearer realm="api", Basic realm="admin"`.

### Pitfall 5: Profile JSON Serialization of Complex Objects
**What goes wrong:** `dataclasses.asdict()` doesn't handle `Enum` values, `frozenset`, `set`, or `datetime` objects. JSON serialization fails.
**Why it happens:** The profile aggregates data from multiple modules, some using non-JSON-serializable types.
**How to avoid:** Use a `default` handler in `json.dumps()` that converts enums to `.value`, sets to lists, and datetimes to ISO strings. Or normalize all data to JSON-safe types before storing in the profile.
**Warning signs:** `TypeError: Object of type Enum is not JSON serializable` when saving profile.

### Pitfall 6: Discovery Request Budget Exhaustion
**What goes wrong:** Auth probing (5 endpoints) + GraphQL checks (4 paths x 2 methods) + architecture detection could exceed the ~20-30 request budget.
**Why it happens:** Each detection sub-system probes independently without awareness of total budget.
**How to avoid:** Track request count across all detection subsystems. Share a request counter. Prioritize spec extraction (zero requests). For active probing, use HEAD/OPTIONS first (cheaper). Stop probing early if budget is nearly exhausted and log the gap.
**Warning signs:** Discovery takes unusually long or the target starts returning 429s during discovery.

### Pitfall 7: Empty or Missing Server Header
**What goes wrong:** Code expects `Server` header for fingerprinting but many APIs don't send it (proxied behind Cloudflare, etc.).
**Why it happens:** Server header is optional in HTTP and often stripped by reverse proxies.
**How to avoid:** Treat server fingerprint as optional. If not present, record `"unknown"` and move on. Never fail discovery because of a missing header.
**Warning signs:** Profile has `server_fingerprint: null` causing downstream KeyError.

## Code Examples

### Complete VAmPI Auth Detection Walkthrough

The VAmPI OpenAPI spec contains:
```json
{
  "components": {
    "securitySchemes": {
      "bearerAuth": {
        "bearerFormat": "JWT",
        "scheme": "bearer",
        "type": "http"
      }
    }
  }
}
```

Expected detection result:
```python
DetectedAuthScheme(
    scheme_type=AuthSchemeType.BEARER,
    name="bearerAuth",
    source="spec",
    details={"format": "JWT", "scheme": "bearer", "type": "http"},
    endpoints=[
        "POST /books/v1",         # security: [{bearerAuth: []}]
        "GET /books/v1/{book_title}",
        "GET /me",
        "DELETE /users/v1/{username}",
        "PUT /users/v1/{username}/email",
        "PUT /users/v1/{username}/password",
    ],
)
```

Endpoints without security (login, register, createdb, user list) should NOT appear in the endpoints list.

### Profile JSON Schema Example

```json
{
  "profile_version": 1,
  "created_at": "2026-02-04T12:00:00Z",
  "content_hash": "a1b2c3d4e5f6...",
  "base_url": "http://localhost:5000",
  "input_format": "openapi_3.0",
  "endpoint_count": 13,

  "auth_schemes": [
    {
      "scheme_type": "bearer",
      "name": "bearerAuth",
      "source": "spec",
      "details": {"format": "JWT", "scheme": "bearer"},
      "endpoints": ["POST /books/v1", "GET /me", "..."]
    }
  ],

  "architecture_type": "REST",
  "architecture_details": {},

  "classifications": {
    "public": 5,
    "protected": 7,
    "auth-endpoint": 1
  },

  "response_pattern_count": 8,

  "server_fingerprint": "Werkzeug/2.3.7 Python/3.11.8",
  "content_types_observed": ["application/json"],
  "security_headers": {
    "x-content-type-options": "nosniff"
  },

  "prerequisites": {
    "rate_limiting": {"status": "ABSENT", "reason": "..."},
    "cors": {"status": "ABSENT", "reason": "..."},
    "csp": {"status": "ABSENT", "reason": "..."}
  },

  "gaps": []
}
```

### Endpoint-to-Auth Scheme Mapping

```python
def _find_endpoints_using_scheme(self, scheme_name: str) -> list[str]:
    """Find which endpoints reference a given security scheme.

    Checks both per-operation security and global security in the spec.
    """
    using_scheme = []
    global_security = self.spec.get("security", [])
    global_uses_scheme = any(
        scheme_name in sec_req
        for sec_req in global_security
        if isinstance(sec_req, dict)
    )

    paths = self.spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "delete", "patch", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            op_security = operation.get("security")
            if op_security is not None:
                # Explicit per-operation security
                if any(scheme_name in sec_req
                       for sec_req in op_security
                       if isinstance(sec_req, dict)):
                    using_scheme.append(f"{method.upper()} {path}")
            elif global_uses_scheme:
                # Inherits global security
                using_scheme.append(f"{method.upper()} {path}")

    return using_scheme
```

### Server Fingerprinting During Probing

```python
def _collect_server_info(self, evidence_list: list) -> dict:
    """Extract server fingerprint and security headers from responses."""
    server_header = ""
    content_types = set()
    security_headers = {}

    security_header_names = {
        "x-content-type-options", "x-frame-options",
        "strict-transport-security", "x-xss-protection",
        "content-security-policy", "referrer-policy",
        "permissions-policy", "x-permitted-cross-domain-policies",
    }

    for evidence in evidence_list:
        for header_name, header_val in evidence.response_headers.items():
            lower_name = header_name.lower()
            if lower_name == "server" and not server_header:
                server_header = header_val
            elif lower_name == "content-type":
                # Normalize: "application/json; charset=utf-8" -> "application/json"
                ct = header_val.split(";")[0].strip().lower()
                content_types.add(ct)
            elif lower_name in security_header_names:
                security_headers[lower_name] = header_val

    return {
        "server_fingerprint": server_header or "unknown",
        "content_types_observed": sorted(content_types),
        "security_headers": security_headers,
    }
```

### Request Budget Tracking

```python
class RequestBudget:
    """Tracks and limits the number of discovery requests."""

    def __init__(self, max_requests: int = 30):
        self.max_requests = max_requests
        self.used = 0

    def can_request(self) -> bool:
        return self.used < self.max_requests

    def record(self):
        self.used += 1

    @property
    def remaining(self) -> int:
        return max(0, self.max_requests - self.used)

# Usage in detectors:
def _probe_unauthenticated(self) -> list[DetectedAuthScheme]:
    probe_endpoints = self._select_probe_endpoints(count=5)
    for ep in probe_endpoints:
        if not self.budget.can_request():
            logger.warning("Discovery request budget exhausted, %d endpoints unprobed",
                           len(probe_endpoints) - probe_endpoints.index(ep))
            break
        evidence = self.http.request(...)
        self.budget.record()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Swagger 2.0 `securityDefinitions` at root | OpenAPI 3.x `components.securitySchemes` | OpenAPI 3.0 (2017) | Must check both locations for backward compatibility |
| Swagger 2.0 `type: "basic"` | OpenAPI 3.x `type: "http"` + `scheme: "basic"` | OpenAPI 3.0 (2017) | Type mapping must handle both formats |
| GraphQL introspection always enabled | Production servers commonly disable introspection | Apollo Server NODE_ENV=production default | Must handle disabled introspection gracefully |
| GraphQL directive fields `onOperation`/`onFragment`/`onField` | `locations` field | graphql-js v14+ (~2018) | Standard introspection query should use `locations` not legacy fields |
| Manual profile management | Content-hash-based staleness detection | Current best practice | Automatic re-discovery when spec changes |

**Deprecated/outdated:**
- GraphQL introspection query using `onOperation`, `onFragment`, `onField` directive fields -- replaced by `locations` field in modern GraphQL implementations. The introspection query constant should use `locations`.

## Open Questions

1. **How should the profile be named when no spec file is provided?**
   - What we know: CONTEXT.md says "named by target (e.g., `profiles/vampi-api.profile.json`)." When a spec file is provided, we can derive the name from the file name.
   - What's unclear: When probing a raw URL with no spec, what name to use.
   - Recommendation: Derive from the base URL hostname (e.g., `localhost-5000.profile.json`). Sanitize non-filename characters.

2. **Should the profile store the full GraphQL schema or just summary statistics?**
   - What we know: CONTEXT.md says "top-level only during discovery -- types, fields, arguments; deep traversal is a test-time concern."
   - What's unclear: How much of the introspection result to persist. Full schema could be large.
   - Recommendation: Store summary (type count, query/mutation/subscription type names, top-level type names) in the profile. If full schema is needed for Phase 7, save it as a separate file alongside the profile.

3. **How to test auth detection for API key and session cookie schemes?**
   - What we know: VAmPI uses Bearer/JWT only. CONTEXT.md says "validated against at least one target per scheme." The blocker section notes: "Only VAmPI available."
   - What's unclear: Where to find test targets for API key and session cookie auth.
   - Recommendation: Write the detection code for all schemes. Unit test with mocked HTTP responses for API key (check for `X-API-Key` header pattern in 401 responses) and session cookie (check for `Set-Cookie` in responses). Integration test against VAmPI for Bearer. Flag integration testing for other schemes as a gap.

4. **Should discovery integrate with the existing `OAuth2Handler`?**
   - What we know: Discovery should never attempt actual authentication (CONTEXT.md). But it could leverage the OAuth2Handler's config to identify the expected token URL and grant type.
   - What's unclear: Whether to pass OAuth2Handler to discovery or keep discovery completely auth-unaware.
   - Recommendation: Keep discovery auth-unaware. Discovery identifies auth schemes; it doesn't authenticate. The OAuth2Handler config is a user-provided hint, not a discovery input. If the spec says OAuth2, that's the discovery finding. Whether the user has configured OAuth2 credentials is a separate concern.

5. **Where to insert discovery in the runner flow?**
   - What we know: Current flow is parse -> oauth -> http -> learn -> classify -> prereq -> scenarios.
   - What's unclear: Whether discovery should run before or after prerequisites.
   - Recommendation: After prerequisites. The profile aggregates all pre-scan results including prerequisite detection. Flow becomes: parse -> oauth -> http -> learn -> classify -> prereq -> **discover** -> scenarios. Discovery consumes all prior results and produces the profile.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `openapi_parser.py` -- `_extract_security_schemes()` handles both Swagger 2.0 and OpenAPI 3.x
- Codebase analysis: `http_client.py` -- `PentestHttpClient.request()` returns `Evidence` with full headers
- Codebase analysis: `prerequisite_detector.py` -- Established pattern for detector classes + runner integration
- Codebase analysis: `endpoint_classifier.py` -- `EndpointClassification` enum and `classify_all()` pattern
- Codebase analysis: `response_patterns.py` -- `ResponsePatternLearner.patterns` dict for profile integration
- Codebase analysis: `runner.py` -- Pre-scan flow: parse -> oauth -> http -> learn -> classify -> prereq -> scenarios
- Codebase analysis: `models.py` -- Existing enum and dataclass patterns
- Codebase analysis: `vampi_openapi.json` -- VAmPI security scheme: `bearerAuth` with `type: http`, `scheme: bearer`, `bearerFormat: JWT`
- OpenAPI security specification -- [learn.openapis.org/specification/security.html](https://learn.openapis.org/specification/security.html)
- RFC 7235 WWW-Authenticate -- [rfc-editor.org/rfc/rfc7235](https://www.rfc-editor.org/rfc/rfc7235)
- MDN WWW-Authenticate reference -- [developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/WWW-Authenticate](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/WWW-Authenticate)
- GraphQL introspection -- [graphql.org/learn/introspection/](https://graphql.org/learn/introspection/)

### Secondary (MEDIUM confidence)
- OpenAPI Swagger 2.0 vs 3.x security differences -- [blog.stoplight.io/difference-between-open-v2-v3-v31](https://blog.stoplight.io/difference-between-open-v2-v3-v31) (verified against official OpenAPI docs)
- GraphQL introspection query template -- [gist.github.com/craigbeck/b90915d49fda19d5b2b17ead14dcd6da](https://gist.github.com/craigbeck/b90915d49fda19d5b2b17ead14dcd6da) (cross-verified with graphql.org)
- Clairvoyance tool for blind GraphQL probing -- [github.com/nikitastupin/clairvoyance](https://github.com/nikitastupin/clairvoyance) (out of scope for Phase 5 but noted for future)

### Tertiary (LOW confidence)
- Python `hashlib` for content hashing -- [docs.python.org/3/library/hashlib.html](https://docs.python.org/3/library/hashlib.html) (verified via stdlib, HIGH confidence for this specific use)
- None remaining at LOW confidence -- all findings verified against codebase or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pure Python stdlib, no new dependencies, verified against existing codebase patterns
- Architecture: HIGH -- Follows established Phase 2/3/4 integration patterns verified in runner.py and prerequisite_detector.py
- Auth detection (spec-based): HIGH -- OpenAPI security scheme structure verified against official docs and VAmPI spec
- Auth detection (probe-based): HIGH -- RFC 7235 WWW-Authenticate syntax verified against official RFC and MDN
- GraphQL introspection: HIGH -- Standard query verified against graphql.org official docs
- Profile persistence: HIGH -- Standard json/hashlib/pathlib stdlib usage
- Pitfalls: HIGH -- Based on codebase analysis, RFC specs, and spec version differences

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable -- no external dependency changes, pure internal architecture work with well-established HTTP/GraphQL standards)
