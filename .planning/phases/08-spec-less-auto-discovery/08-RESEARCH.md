# Phase 8: Spec-less Auto-Discovery - Research

**Researched:** 2026-02-05
**Domain:** API Endpoint Discovery, Kiterunner Integration, Spec Detection
**Confidence:** MEDIUM

## Summary

This phase enables the toolkit to pentest APIs with just a URL and credentials by automatically discovering specifications or endpoints. The implementation involves two stages: (1) spec discovery at common paths, and (2) fallback to endpoint fuzzing via Kiterunner with a built-in wordlist backup.

Research confirms that Kiterunner is the industry-standard tool for API endpoint discovery, written in Go and invoked via subprocess. It uses compiled `.kite` wordlists derived from real Swagger/OpenAPI specifications for contextually-aware fuzzing. The existing codebase already has solid infrastructure (InputDetector, OpenAPI parser, HTTP client, RequestBudget) that can be extended.

**Primary recommendation:** Create a new `SpecDiscoverer` class for spec auto-discovery at common paths, and a `KiterunnerAdapter` class for subprocess invocation with graceful fallback to a bundled wordlist when Kiterunner binary is unavailable.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kiterunner | v1.0.2 | API endpoint fuzzing | Purpose-built for API discovery; uses real API patterns from Swagger datasets |
| shutil.which | stdlib | Binary detection | Standard Python way to check if executable exists |
| subprocess | stdlib | Process execution | Run Kiterunner and capture JSON output |
| requests | existing | HTTP requests | Already in codebase as PentestHttpClient |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyrate-limiter | 2.x+ | Rate limiting | If more sophisticated rate limiting needed beyond RequestBudget |
| tenacity | 8.x+ | Retry logic | If exponential backoff for discovery requests needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Kiterunner | ffuf | ffuf is general-purpose; Kiterunner is API-specific with intelligent param filling |
| Kiterunner | Arjun | Arjun focuses on parameter discovery, not endpoint discovery |
| Built-in wordlist | SecLists only | SecLists excellent but requires download; built-in ensures offline capability |

**Installation:**
```bash
# Kiterunner (optional - user must install separately)
# Download from: https://github.com/assetnote/kiterunner/releases
# Or on Arch: yay -S kiterunner-bin

# No new Python dependencies required - uses stdlib + existing deps
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
├── core/
│   ├── spec_discoverer.py     # NEW: Auto-discovery at common paths
│   ├── kiterunner_adapter.py  # NEW: Subprocess wrapper for Kiterunner
│   ├── endpoint_wordlist.py   # NEW: Built-in fallback wordlist
│   ├── input_detector.py      # Existing - extend for URL-only mode
│   └── http_client.py         # Existing - reuse for discovery
```

### Pattern 1: Two-Stage Discovery Pipeline
**What:** Try spec discovery first (cheap), fall back to endpoint fuzzing (expensive)
**When to use:** When `--url` provided without `--input`

```python
# Pseudo-code for discovery flow
class SpecDiscoverer:
    """Stage 1: Try to find API spec at common paths."""

    SPEC_PATHS = [
        "/openapi.json",
        "/swagger.json",
        "/api-docs",
        "/api/openapi.json",
        "/api/swagger.json",
        "/v1/swagger.json",
        "/v2/swagger.json",
        "/v3/swagger.json",
        "/swagger/v1/swagger.json",
        "/docs.json",
        "/api-docs.json",
        "/swagger.yaml",
        "/openapi.yaml",
        # GraphQL
        "/graphql",
        "/api/graphql",
        "/gql",
    ]

    def __init__(self, base_url: str, http_client, budget: RequestBudget):
        self.base_url = base_url.rstrip("/")
        self.http = http_client
        self.budget = budget

    def discover(self) -> tuple[str | None, str | None]:
        """Try spec paths, return (spec_content, spec_type) or (None, None)."""
        for path in self.SPEC_PATHS:
            if not self.budget.can_request():
                break
            url = f"{self.base_url}{path}"
            evidence = self.http.request("GET", url)
            self.budget.record()

            if evidence.response_status == 200:
                spec_type = self._detect_spec_type(evidence.response_body)
                if spec_type:
                    return evidence.response_body, spec_type
        return None, None

    def _detect_spec_type(self, body: str) -> str | None:
        """Detect if response is OpenAPI/Swagger/GraphQL."""
        # Check for OpenAPI/Swagger JSON markers
        # Check for GraphQL introspection response
        pass
```

### Pattern 2: Kiterunner Subprocess Adapter
**What:** Wrap Kiterunner CLI with graceful fallback
**When to use:** When spec discovery fails and fuzzing needed

```python
import json
import shutil
import subprocess
from typing import Iterator

class KiterunnerAdapter:
    """Stage 2: Fuzz endpoints via Kiterunner with fallback."""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.kr_path = shutil.which("kr")  # or "kiterunner"

    def is_available(self) -> bool:
        """Check if Kiterunner binary is installed."""
        return self.kr_path is not None

    def scan(self, target: str, wordlist: str = None) -> Iterator[dict]:
        """
        Run Kiterunner scan and yield discovered endpoints.

        Args:
            target: Base URL to scan
            wordlist: Path to .kite or .txt wordlist

        Yields:
            Dict with keys: method, path, status, length
        """
        if not self.is_available():
            raise KiterunnerNotFoundError("Kiterunner binary not found")

        cmd = [
            self.kr_path, "scan",
            target,
            "-o", "json",
            "-x", "5",  # max connections per host
        ]

        if wordlist:
            if wordlist.endswith(".kite"):
                cmd.extend(["-w", wordlist])
            else:
                cmd.extend(["-w", wordlist])
        else:
            # Use Assetnote remote wordlist (auto-cached)
            cmd.extend(["-A", "apiroutes-210228:5000"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        # Parse JSON output from stdout
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
```

### Pattern 3: Discovered Endpoint to Endpoint Model Conversion
**What:** Transform fuzzing results into Endpoint objects
**When to use:** After discovery completes

```python
from api_pentest.core.models import Endpoint, EndpointClassification

def discovered_to_endpoint(
    base_url: str,
    discovered: dict,
    source: str = "fuzzing"
) -> Endpoint:
    """Convert discovery result to Endpoint model."""
    method = discovered.get("method", "GET").upper()
    path = discovered.get("path", "/")

    return Endpoint(
        method=method,
        url=f"{base_url.rstrip('/')}{path}",
        name=f"{method} {path}",
        classification=EndpointClassification.PROTECTED,  # Conservative default
        classification_reason=f"Discovered via {source}",
    )
```

### Anti-Patterns to Avoid
- **Unbounded discovery requests:** Always use RequestBudget to cap discovery requests
- **Blocking on Kiterunner:** Use subprocess timeout to prevent hangs
- **Assuming Kiterunner installed:** Always check with shutil.which and fall back gracefully
- **Parsing stdout/stderr incorrectly:** Kiterunner sends visual output to stderr, results to stdout

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Binary detection | Custom PATH search | `shutil.which()` | Handles all platforms, PATHEXT on Windows |
| API wordlists | Scrape endpoints from scratch | SecLists/Assetnote | Curated from real APIs, continuously updated |
| Process execution | Low-level popen | subprocess.run | Safer, better error handling, timeout support |
| Rate limiting | sleep() loops | RequestBudget (existing) | Already integrated, shared across subsystems |
| Spec parsing | Regex JSON detection | InputDetector (existing) | Handles OpenAPI 2.0/3.0/3.1, Postman |

**Key insight:** The existing codebase already has infrastructure for most needs. Extend InputDetector and RequestBudget rather than building parallel systems.

## Common Pitfalls

### Pitfall 1: Discovery Request Storm
**What goes wrong:** Uncontrolled discovery hammers target with hundreds of requests
**Why it happens:** No rate limiting, Kiterunner defaults to aggressive scanning
**How to avoid:**
- Use existing RequestBudget with discovery-specific cap (e.g., 50 requests for spec discovery)
- Configure Kiterunner with `-x 5` (5 connections max)
- Add delays between fuzzing bursts
**Warning signs:** Target returns 429 Too Many Requests, IP gets blocked

### Pitfall 2: False Positive Endpoints
**What goes wrong:** Fuzzer reports endpoints that don't actually exist
**Why it happens:** Generic 200 responses, custom error pages, WAF interference
**How to avoid:**
- Validate discovered endpoints with follow-up request
- Check response content-type matches expected (application/json for APIs)
- Compare response length/hash to identify wildcard responses
**Warning signs:** Many discovered endpoints return identical responses

### Pitfall 3: Kiterunner Output Parsing Failures
**What goes wrong:** JSON parsing fails, results lost
**Why it happens:** Visual output mixed with results, non-JSON lines, stderr/stdout confusion
**How to avoid:**
- Always use `-o json` flag
- Parse stdout only (stderr has visual output)
- Skip unparseable lines gracefully
**Warning signs:** Empty results despite Kiterunner showing hits

### Pitfall 4: Blocking on Missing Kiterunner
**What goes wrong:** Tool crashes or hangs when Kiterunner not installed
**Why it happens:** No pre-check, subprocess blocks waiting for input
**How to avoid:**
- Check `shutil.which("kr")` before any subprocess call
- Raise descriptive error early if unavailable
- Fall back to built-in wordlist with simple HTTP probing
**Warning signs:** Long hangs, "command not found" errors

### Pitfall 5: GraphQL Not Detected
**What goes wrong:** GraphQL API missed, only REST testing performed
**Why it happens:** Introspection disabled, non-standard paths
**How to avoid:**
- Check multiple GraphQL paths (/graphql, /api/graphql, /gql, /query)
- Try simple `{__typename}` query even if introspection fails
- Leverage existing ArchitectureDetector.GRAPHQL_PATHS
**Warning signs:** API profile shows REST but target is actually GraphQL

## Code Examples

Verified patterns from official sources and existing codebase:

### CLI Argument Extension
```python
# In run_pentest.py - add --url flag
parser.add_argument(
    "--url", "-u",
    help="Base URL for spec auto-discovery (alternative to --input). "
         "Triggers automatic spec detection at common paths, "
         "falls back to endpoint fuzzing if no spec found.",
)

# Validation: --url XOR --input required
if not args.input and not args.url:
    parser.error("Either --input or --url is required")
if args.input and args.url:
    parser.error("Cannot use both --input and --url")
```

### Spec Discovery Integration
```python
# In runner.py - handle URL-only mode
def parse_input(self) -> list[Endpoint]:
    input_file = self.config.get("input_file", "")
    base_url = self.config.get("base_url", "")

    # New: URL-only mode triggers discovery
    if not input_file and base_url:
        return self._discover_from_url(base_url)

    # Existing: file-based parsing
    detector = InputDetector(
        file_path=input_file,
        environment_path=self.config.get("environment_file"),
        base_url_override=base_url,
    )
    self.endpoints = detector.parse()
    return self.endpoints

def _discover_from_url(self, base_url: str) -> list[Endpoint]:
    """Auto-discover API spec or endpoints from URL only."""
    self.init_http()

    # Stage 1: Try spec paths
    discoverer = SpecDiscoverer(
        base_url=base_url,
        http_client=self.http,
        budget=RequestBudget(max_requests=50),
    )
    spec_content, spec_type = discoverer.discover()

    if spec_content and spec_type:
        # Save to temp file, use existing parser
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write(spec_content)
            temp_path = f.name

        detector = InputDetector(file_path=temp_path, base_url_override=base_url)
        self.endpoints = detector.parse()
        return self.endpoints

    # Stage 2: Fall back to endpoint fuzzing
    return self._fuzz_endpoints(base_url)
```

### Built-in Fallback Wordlist
```python
# api_pentest/core/endpoint_wordlist.py
"""Built-in API endpoint wordlist for fallback when Kiterunner unavailable.

Curated from SecLists and common patterns. Small (~200 entries) for
fast scanning when external tools unavailable.
"""

API_ENDPOINTS = [
    # Spec discovery paths (already checked in SpecDiscoverer)
    # Common API versioning
    "/api",
    "/api/v1",
    "/api/v2",
    "/api/v3",
    "/v1",
    "/v2",
    "/v3",
    # Common resources
    "/users",
    "/api/users",
    "/accounts",
    "/api/accounts",
    "/auth",
    "/api/auth",
    "/login",
    "/api/login",
    "/token",
    "/api/token",
    "/oauth/token",
    "/api/oauth/token",
    "/register",
    "/api/register",
    "/profile",
    "/api/profile",
    "/me",
    "/api/me",
    # Admin
    "/admin",
    "/api/admin",
    "/dashboard",
    "/api/dashboard",
    # Common CRUD
    "/items",
    "/api/items",
    "/products",
    "/api/products",
    "/orders",
    "/api/orders",
    "/messages",
    "/api/messages",
    # Health/status
    "/health",
    "/api/health",
    "/status",
    "/api/status",
    "/ping",
    # Debug (security-relevant)
    "/debug",
    "/api/debug",
    "/actuator",
    "/actuator/health",
    "/actuator/env",
    "/.env",
    "/config",
    "/api/config",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| dirsearch/ffuf generic | Kiterunner API-aware | 2021 | Higher accuracy, fewer false positives |
| Manual wordlist only | Swagger-derived datasets | 2021 | Real API patterns, proper param types |
| Sync subprocess | async/subprocess with timeout | Python 3.7+ | No blocking on slow targets |

**Deprecated/outdated:**
- **gobuster for APIs:** General-purpose file discovery, misses API-specific patterns
- **Manual endpoint guessing:** Inefficient, low coverage

## Open Questions

Things that couldn't be fully resolved:

1. **Kiterunner JSON Output Structure**
   - What we know: Uses `-o json` flag, outputs to stdout, visual to stderr
   - What's unclear: Exact field names in JSON output (method, path, status, length?)
   - Recommendation: Test locally with Kiterunner to capture actual output format; handle unknown fields gracefully

2. **Remote Wordlist Caching**
   - What we know: `-A` flag auto-caches to `~/.cache/kiterunner/wordlists/`
   - What's unclear: Behavior when offline after initial cache, cache invalidation
   - Recommendation: Always have built-in fallback wordlist; don't rely on network for wordlists

3. **Kiterunner Multi-Platform Support**
   - What we know: Go binary with releases for Linux, macOS, Windows
   - What's unclear: Behavior differences across platforms
   - Recommendation: Use `shutil.which()` for cross-platform binary detection; document manual install requirement

## Sources

### Primary (HIGH confidence)
- [GitHub - assetnote/kiterunner](https://github.com/assetnote/kiterunner) - Official repository, installation, CLI usage
- [Python shutil documentation](https://docs.python.org/3/library/shutil.html) - shutil.which() for binary detection
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - Process execution patterns

### Secondary (MEDIUM confidence)
- [TCM Security - Kiterunner Guide](https://tcm-sec.com/kiterunner/) - Usage examples, wordlist configuration
- [SecLists API wordlists](https://github.com/danielmiessler/SecLists/tree/master/Discovery/Web-Content/api) - Fallback wordlist source
- [OAI/OpenAPI-Specification Issue #864](https://github.com/OAI/OpenAPI-Specification/issues/864) - Spec discovery paths discussion
- [GitHub Gist - Common API paths](https://gist.github.com/rodnt/250dd33af97d228cc94cd11504abef06) - Comprehensive spec path list

### Tertiary (LOW confidence)
- [Kiterunner Issue #18](https://github.com/assetnote/kiterunner/issues/18) - JSON output concerns (no resolution details)
- WebSearch results for rate limiting patterns - General best practices

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Kiterunner is well-documented but JSON output format needs local verification
- Architecture: HIGH - Patterns align with existing codebase (InputDetector, RequestBudget)
- Pitfalls: HIGH - Based on official documentation and common subprocess patterns

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable domain, Kiterunner hasn't had major updates)
