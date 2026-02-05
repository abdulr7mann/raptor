# Phase 6: Adaptive Test Execution - Research

**Researched:** 2026-02-05
**Domain:** Test selection, relevance scoring, response format handling, scenario applicability
**Confidence:** HIGH

## Summary

Phase 6 builds an adaptive test execution system that uses the API profile from Phase 5 to select only relevant tests for each endpoint, adjust test parameters to match discovered API characteristics, and handle diverse response formats gracefully. The core principle: tests should feel intelligent -- if a test doesn't make sense for an endpoint, skip it visibly rather than running and producing nonsensical findings.

The implementation requires four coordinated subsystems: (1) a scenario applicability declaration system where each scenario declares what architectures and classifications it applies to, (2) a relevance scoring calculator that combines architecture match, classification match, and prerequisite presence into a score, (3) a parameter adapter that configures tests to use the correct auth scheme, content type, and success validation from the profile, and (4) a response format handler that safely parses JSON, XML, and plain text responses without crashing.

The codebase already has the foundational pieces: `ApiProfile` with `architecture_type`, `auth_schemes`, and `classifications` from Phase 5, `EndpointClassification` enum from Phase 3, `ResponsePatternLearner.is_real_success()` from Phase 2, and `PrerequisiteResult` from Phase 4. The runner already passes these objects to scenarios via `BaseScenario.setup()`. This phase adds the filtering/selection logic in the runner and the format handling in the http client or base scenario.

**Primary recommendation:** Add an `APPLICABILITY` class attribute to `BaseScenario` declaring architecture/classification requirements. Build a `RelevanceCalculator` that scores test-endpoint pairs and filters below threshold. Extend `Evidence` parsing in scenarios with Content-Type-aware format detection. The runner checks applicability before instantiating scenarios, and each scenario's tests check per-endpoint relevance before execution.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | N/A | RelevanceScore, ScenarioApplicability dataclasses | Consistent with existing codebase patterns |
| Python stdlib `json` | N/A | JSON response parsing | Already used throughout codebase |
| Python stdlib `xml.etree.ElementTree` | N/A | XML response parsing (fallback) | Standard library, no new deps |
| `defusedxml` | 0.7.1 | Safe XML parsing (XXE protection) | Industry standard for security-conscious XML parsing |
| Python stdlib `enum` | N/A | Extend existing enums | Consistent with models.py, api_discovery.py |
| Python stdlib `logging` | N/A | Skip reason logging | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requests` (existing) | 2.32.4 | Content-Type header access | Already captures headers in Evidence |
| Python stdlib `re` | N/A | Content-Type parsing (extract charset, boundary) | Already used in multiple modules |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| defusedxml | stdlib xml.etree only | Vulnerable to XXE; defusedxml is drop-in replacement with security defaults |
| Custom relevance formula | ML-based scoring | Overkill for this scope; simple weighted sum is transparent and debuggable |
| Per-scenario applicability methods | Central registry | Decentralized (on scenario) is more maintainable; follows existing pattern of scenario-owned metadata |

**Installation:**
```bash
pip install defusedxml>=0.7.1
# Or add to requirements.txt: defusedxml>=0.7.1
```

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  core/
    api_discovery.py         # READ ONLY: ApiProfile, ArchitectureType consumed
    models.py                # MODIFIED: Add ScenarioApplicability dataclass
    response_formats.py      # NEW: ResponseFormatHandler for JSON/XML/text parsing
    relevance.py             # NEW: RelevanceCalculator, RelevanceScore
    endpoint_classifier.py   # READ ONLY: EndpointClassification consumed
    ...
  scenarios/
    base_scenario.py         # MODIFIED: Add APPLICABILITY attribute, format handling methods
    s01_token_reuse.py       # MODIFIED: Add APPLICABILITY declaration
    s03_idor.py              # MODIFIED: Add APPLICABILITY declaration
    s04_injection.py         # MODIFIED: Add APPLICABILITY declaration
    s07_access_controls.py   # MODIFIED: Add APPLICABILITY declaration (already uses classification)
    ...                      # All scenarios get APPLICABILITY
  runner.py                  # MODIFIED: Add applicability filter, relevance threshold check
```

### Pattern 1: Scenario Applicability Declaration
**What:** Each scenario declares what architectures, classifications, and prerequisites it applies to via a class attribute.
**When to use:** Every scenario class.
**Why:** CONTEXT.md locked decision: "Scenario applicability is explicit -- each scenario declares what architectures/classifications it applies to. Runner filters before executing."

```python
# Source: CONTEXT.md design decision + existing BaseScenario pattern

from dataclasses import dataclass, field
from enum import Enum, auto
from api_pentest.core.api_discovery import ArchitectureType

class ApplicabilityMode(Enum):
    """How to interpret the applicability list."""
    ANY = auto()      # Applies if ANY listed value matches
    ALL = auto()      # Applies only if ALL listed values match
    EXCLUDE = auto()  # Applies if NONE of the listed values match

@dataclass
class ScenarioApplicability:
    """Declares when a scenario is relevant."""
    architectures: list[ArchitectureType] = field(default_factory=list)
    architecture_mode: ApplicabilityMode = ApplicabilityMode.ANY
    # Empty list = applies to all architectures

    classifications: list[str] = field(default_factory=list)
    classification_mode: ApplicabilityMode = ApplicabilityMode.ANY
    # Values: "public", "protected", "auth-endpoint"
    # Empty list = applies to all classifications

    requires_prerequisites: list[str] = field(default_factory=list)
    # e.g. ["rate_limiting"] for S02, ["cors"] for S07 CORS test
    # Empty list = no prerequisite requirements

# Usage in a scenario:
class S04Injection(BaseScenario):
    APPLICABILITY = ScenarioApplicability(
        architectures=[ArchitectureType.REST, ArchitectureType.GRAPHQL],
        # Injection applies to both REST and GraphQL
    )

class S07AccessControls(BaseScenario):
    APPLICABILITY = ScenarioApplicability(
        classifications=["protected"],  # Skip PUBLIC endpoints
        classification_mode=ApplicabilityMode.ANY,
    )

# GraphQL-specific scenario example:
class S15GraphQLDepthLimit(BaseScenario):  # hypothetical
    APPLICABILITY = ScenarioApplicability(
        architectures=[ArchitectureType.GRAPHQL],
        architecture_mode=ApplicabilityMode.ANY,
        # Only runs on GraphQL APIs
    )
```

### Pattern 2: Relevance Score Calculation
**What:** Compute a 0.0-1.0 score for test-endpoint relevance using weighted factors.
**When to use:** Before executing each test on each endpoint.
**Why:** CONTEXT.md locked decision: "Score factors: architecture match (+0.4, mandatory for GraphQL-specific tests), classification match (+0.3), prerequisite present (+0.3). Default threshold: 0.3."

```python
# Source: CONTEXT.md scoring formula

from dataclasses import dataclass

@dataclass
class RelevanceScore:
    """Breakdown of relevance calculation."""
    total: float
    architecture_score: float
    classification_score: float
    prerequisite_score: float
    skip_reason: str = ""  # Populated if total < threshold

class RelevanceCalculator:
    """Calculates test-endpoint relevance scores."""

    WEIGHT_ARCHITECTURE = 0.4
    WEIGHT_CLASSIFICATION = 0.3
    WEIGHT_PREREQUISITE = 0.3

    def __init__(self, api_profile, prerequisite_results: dict, threshold: float = 0.3):
        self.profile = api_profile
        self.prereqs = prerequisite_results
        self.threshold = threshold

    def calculate(
        self,
        scenario_applicability: ScenarioApplicability,
        endpoint: Endpoint,
    ) -> RelevanceScore:
        """Calculate relevance score for scenario-endpoint pair."""
        arch_score = 0.0
        class_score = 0.0
        prereq_score = 0.0
        skip_reason = ""

        # Architecture matching
        if scenario_applicability.architectures:
            profile_arch = ArchitectureType(self.profile.architecture_type)
            if profile_arch in scenario_applicability.architectures:
                arch_score = self.WEIGHT_ARCHITECTURE
            elif scenario_applicability.architecture_mode == ApplicabilityMode.ANY:
                # Hard skip for architecture mismatch on strict tests
                skip_reason = f"Architecture mismatch: {profile_arch.value} not in {[a.value for a in scenario_applicability.architectures]}"
        else:
            # No architecture requirement = full score
            arch_score = self.WEIGHT_ARCHITECTURE

        # Classification matching
        if scenario_applicability.classifications:
            ep_class = endpoint.classification.value
            if ep_class in scenario_applicability.classifications:
                class_score = self.WEIGHT_CLASSIFICATION
            else:
                skip_reason = skip_reason or f"Classification mismatch: {ep_class} not in {scenario_applicability.classifications}"
        else:
            class_score = self.WEIGHT_CLASSIFICATION

        # Prerequisite matching
        if scenario_applicability.requires_prerequisites:
            all_present = True
            for prereq_name in scenario_applicability.requires_prerequisites:
                prereq = self.prereqs.get(prereq_name)
                if not prereq or prereq.status != DetectionStatus.PRESENT:
                    all_present = False
                    skip_reason = skip_reason or f"Prerequisite not present: {prereq_name}"
                    break
            if all_present:
                prereq_score = self.WEIGHT_PREREQUISITE
        else:
            prereq_score = self.WEIGHT_PREREQUISITE

        total = arch_score + class_score + prereq_score

        if total < self.threshold and not skip_reason:
            skip_reason = f"Score {total:.2f} below threshold {self.threshold}"

        return RelevanceScore(
            total=total,
            architecture_score=arch_score,
            classification_score=class_score,
            prerequisite_score=prereq_score,
            skip_reason=skip_reason if total < self.threshold else "",
        )
```

### Pattern 3: Content-Type Driven Response Parsing
**What:** Detect response format from Content-Type header and parse accordingly with graceful fallback.
**When to use:** When scenarios need to inspect response body structure.
**Why:** CONTEXT.md locked decision: "Content-Type driven parsing -- detect from response header, parse accordingly. JSON -> json.loads, XML -> xml parser, else treat as text. Graceful degradation -- if parsing fails, treat as plain text."

```python
# Source: requests library Content-Type header access + defusedxml docs

import json
import re
from typing import Any
import defusedxml.ElementTree as ET

class ResponseFormatHandler:
    """Parses response bodies based on Content-Type with safe defaults."""

    JSON_TYPES = frozenset({
        "application/json",
        "application/vnd.api+json",
        "application/hal+json",
        "application/problem+json",
        "text/json",
    })

    XML_TYPES = frozenset({
        "application/xml",
        "text/xml",
        "application/soap+xml",
        "application/xhtml+xml",
        "application/atom+xml",
        "application/rss+xml",
    })

    @staticmethod
    def detect_content_type(evidence) -> str:
        """Extract base content type from Content-Type header."""
        ct_header = evidence.response_headers.get(
            "Content-Type",
            evidence.response_headers.get("content-type", "")
        )
        # Strip charset, boundary, etc: "application/json; charset=utf-8" -> "application/json"
        base_type = ct_header.split(";")[0].strip().lower()
        return base_type

    def parse(self, evidence) -> tuple[Any, str]:
        """Parse response body based on Content-Type.

        Returns:
            Tuple of (parsed_data, format_type) where:
            - parsed_data: dict/list for JSON, Element for XML, str for text
            - format_type: "json", "xml", or "text"
        """
        content_type = self.detect_content_type(evidence)
        body = evidence.response_body

        if not body:
            return None, "empty"

        # Try JSON
        if content_type in self.JSON_TYPES or content_type.endswith("+json"):
            try:
                return json.loads(body), "json"
            except (json.JSONDecodeError, TypeError):
                pass  # Fall through to text

        # Try XML (using defusedxml for safety)
        if content_type in self.XML_TYPES or content_type.endswith("+xml"):
            try:
                # defusedxml protects against XXE and entity expansion
                root = ET.fromstring(body)
                return root, "xml"
            except ET.ParseError:
                pass  # Fall through to text

        # Fallback: plain text
        return body, "text"

    def parse_json_safe(self, evidence) -> dict | list | None:
        """Parse as JSON if possible, return None otherwise."""
        parsed, fmt = self.parse(evidence)
        if fmt == "json" and isinstance(parsed, (dict, list)):
            return parsed
        return None
```

### Pattern 4: Parameter Adaptation from Profile
**What:** Tests use auth scheme, content type, and success criteria from the API profile.
**When to use:** Every test that makes requests.
**Why:** CONTEXT.md locked decision: "Auth from profile -- tests use the auth scheme discovered in Phase 5. Content-Type from profile -- tests send payloads matching what the API expects. Fallback to conservative defaults."

```python
# Source: ApiProfile structure from Phase 5 + existing BaseScenario token handling

class BaseScenario(ABC):
    """Extended with profile-aware parameter adaptation."""

    def get_auth_header_from_profile(self) -> str | None:
        """Get authorization header based on profile's detected auth scheme.

        Uses the API profile to determine the correct auth format.
        Falls back to Bearer token if OAuth handler is configured.
        """
        profile = getattr(self, 'api_profile', None)

        # If we have a profile, check what auth scheme it detected
        if profile and profile.auth_schemes:
            primary_scheme = profile.auth_schemes[0]
            scheme_type = primary_scheme.get("scheme_type", "")

            if scheme_type == "bearer" and self.oauth:
                token_ctx = self.oauth.acquire_token()
                return token_ctx.authorization_header if token_ctx else None

            elif scheme_type == "apiKey":
                # API key from config (already handled by endpoint headers)
                api_key = self.config.get("api_key")
                if api_key:
                    key_name = primary_scheme.get("details", {}).get("name", "X-API-Key")
                    key_in = primary_scheme.get("details", {}).get("in", "header")
                    if key_in == "header":
                        return None  # Handled via headers dict, not auth_token

            elif scheme_type == "basic":
                # Basic auth from config
                username = self.config.get("basic_auth_user", "")
                password = self.config.get("basic_auth_pass", "")
                if username:
                    import base64
                    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
                    return f"Basic {creds}"

        # Fallback: use OAuth handler if available
        if self.oauth:
            token_ctx = self.oauth.acquire_token()
            return token_ctx.authorization_header if token_ctx else None

        return None

    def get_content_type_from_profile(self) -> str:
        """Get expected Content-Type based on profile observation.

        Returns the most commonly observed content type from the profile,
        defaulting to application/json if not determined.
        """
        profile = getattr(self, 'api_profile', None)

        if profile and profile.content_types_observed:
            # Prefer JSON if observed, otherwise first observed type
            for ct in profile.content_types_observed:
                if "json" in ct:
                    return ct
            return profile.content_types_observed[0]

        # Conservative default
        return "application/json"
```

### Anti-Patterns to Avoid
- **Running GraphQL tests on REST APIs:** The relevance calculator must hard-skip GraphQL-specific tests when `profile.architecture_type != "GraphQL"`. This is not a soft penalty -- architecture mismatch for specialized tests returns score 0.0.
- **Hardcoded auth assumptions:** Never assume `Authorization: Bearer` without checking the profile. The profile may indicate `apiKey`, `Basic`, or session cookies.
- **Crashing on malformed responses:** XML parsing especially can throw exceptions. Always wrap in try/except and fall back to text treatment.
- **Skipping silently:** When a test is skipped due to low relevance, ALWAYS log the reason. Silent skips are confusing.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML parsing with untrusted input | `xml.etree.ElementTree` directly | `defusedxml.ElementTree` | stdlib XML is vulnerable to XXE, billion laughs, external entity attacks |
| Content-Type negotiation | Custom header parsing | `response.headers.get("Content-Type", "").split(";")[0]` | requests library already provides case-insensitive header access |
| JSON parsing with error handling | Custom try/catch everywhere | Centralized `ResponseFormatHandler.parse_json_safe()` | Single point of maintenance, consistent error handling |
| Relevance threshold configuration | Hardcoded magic number | CLI flag `--relevance-threshold` + config key | User control is essential for security tools (exhaustive vs fast modes) |

**Key insight:** The "intelligence" of test selection comes from combining existing profile data (Phase 5) with explicit applicability declarations. Don't try to infer applicability at runtime -- declare it statically and filter before execution.

## Common Pitfalls

### Pitfall 1: Incomplete Scenario Applicability Annotations
**What goes wrong:** Some scenarios don't declare APPLICABILITY, causing them to run unconditionally and produce false positives on incompatible APIs.
**Why it happens:** Forgetting to add APPLICABILITY to existing scenarios when retrofitting.
**How to avoid:** Audit ALL 13 scenarios (S01-S13) and add explicit APPLICABILITY declarations. Default to broad applicability (empty lists = applies to all) rather than forgetting entirely.
**Warning signs:** GraphQL injection tests running against REST APIs, auth tests running against public endpoints.

### Pitfall 2: Relevance Score Threshold Too High
**What goes wrong:** Setting threshold at 0.7+ causes most tests to be skipped, missing vulnerabilities.
**Why it happens:** Over-optimization for "clean" reports instead of security coverage.
**How to avoid:** Keep default at 0.3 (conservative for security testing). Offer `--fast` mode with higher threshold (0.6) for quick scans, but warn that it reduces coverage.
**Warning signs:** Very few tests running, unusually clean reports, low endpoint coverage.

### Pitfall 3: XML Parsing Crashes on Malformed Input
**What goes wrong:** `ET.fromstring()` throws `ParseError` and crashes the scenario mid-execution.
**Why it happens:** Many APIs return malformed XML (unclosed tags, invalid characters, HTML masquerading as XML).
**How to avoid:** Always wrap XML parsing in try/except, fall back to plain text. Use defusedxml which is slightly more lenient. Log the parse error but continue execution.
**Warning signs:** Scenarios ending abruptly with stack traces containing "xml.etree".

### Pitfall 4: Auth Scheme Mismatch
**What goes wrong:** Tests use Bearer tokens against an API that expects API keys in headers, or Basic auth.
**Why it happens:** Not reading `profile.auth_schemes[0].scheme_type` before constructing auth header.
**How to avoid:** Always check profile auth scheme first. If OAuth handler exists but profile says apiKey, don't use the OAuth handler's token.
**Warning signs:** All authenticated requests returning 401, but profile shows successful auth scheme detection.

### Pitfall 5: Skips Not Logged
**What goes wrong:** Tests skip silently, user doesn't understand why coverage is low.
**Why it happens:** Early returns without logging, or logging at DEBUG level.
**How to avoid:** Every skip must log at INFO level with the skip reason. Use `self.add_skip_result()` (already exists in BaseScenario) consistently.
**Warning signs:** Test counts in summary don't match expected, no explanation in logs.

## Code Examples

Verified patterns from official sources and codebase analysis:

### Scenario with Full Applicability Declaration
```python
# Source: Codebase analysis + CONTEXT.md design

from api_pentest.core.api_discovery import ArchitectureType
from api_pentest.core.models import ScenarioApplicability, ApplicabilityMode
from api_pentest.scenarios.base_scenario import BaseScenario

class S03IDOR(BaseScenario):
    """S03 - Insecure Direct Object Reference detection."""

    SCENARIO_ID = "S03"
    SCENARIO_NAME = "Insecure Direct Object Reference"
    OWASP_ID = "API1:2023"
    OWASP_NAME = "Broken Object Level Authorization"

    # IDOR applies to REST and HYBRID, not pure GraphQL (different access patterns)
    APPLICABILITY = ScenarioApplicability(
        architectures=[ArchitectureType.REST, ArchitectureType.HYBRID, ArchitectureType.UNKNOWN],
        classifications=["protected"],  # Only test authenticated endpoints
        # No prerequisite requirements
    )
```

### Runner Filtering with Relevance Check
```python
# Source: Codebase runner.py pattern + CONTEXT.md requirements

def run(self, scenario_ids: list[str] | None = None):
    # ... existing setup code ...

    # Build relevance calculator with profile and prereqs
    relevance_calc = RelevanceCalculator(
        api_profile=self.api_profile,
        prerequisite_results=self.prerequisite_results,
        threshold=self.config.get("relevance_threshold", 0.3),
    )

    for sid in selected:
        scenario_class = self._load_scenario_class(sid)

        # Check scenario-level applicability against API profile
        applicability = getattr(scenario_class, 'APPLICABILITY', ScenarioApplicability())

        # Quick architecture check at scenario level
        if applicability.architectures:
            profile_arch = ArchitectureType(self.api_profile.architecture_type)
            if profile_arch not in applicability.architectures:
                logger.info(
                    "Skipping %s: architecture %s not in %s",
                    sid, profile_arch.value,
                    [a.value for a in applicability.architectures],
                )
                continue

        # Scenario passes architecture check, instantiate and run
        scenario = scenario_class()
        scenario.setup(
            endpoints=self.endpoints,
            # ... existing parameters ...
            relevance_calculator=relevance_calc,  # Pass calculator to scenario
            api_profile=self.api_profile,         # Pass profile for parameter adaptation
        )
        results = scenario.run()
```

### Safe Response Format Detection
```python
# Source: requests library docs + defusedxml PyPI docs

import json
import defusedxml.ElementTree as ET
from typing import Any

def parse_response_body(evidence) -> tuple[Any, str]:
    """Parse response based on Content-Type, with safe fallbacks.

    Returns:
        (parsed_data, format_type) where format_type is "json", "xml", or "text"
    """
    content_type = (
        evidence.response_headers.get("Content-Type", "") or
        evidence.response_headers.get("content-type", "")
    ).split(";")[0].strip().lower()

    body = evidence.response_body
    if not body:
        return None, "empty"

    # JSON detection and parsing
    if "json" in content_type:
        try:
            return json.loads(body), "json"
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("JSON parse failed despite Content-Type: %s", e)
            # Fall through to text

    # XML detection and parsing (using defusedxml for safety)
    if "xml" in content_type:
        try:
            # defusedxml.ElementTree.fromstring() is a safe drop-in
            root = ET.fromstring(body)
            return root, "xml"
        except ET.ParseError as e:
            logger.debug("XML parse failed despite Content-Type: %s", e)
            # Fall through to text

    # Default: plain text
    return body, "text"
```

### CLI Flag for Relevance Threshold
```python
# Source: Codebase pattern from run_pentest.py + CONTEXT.md requirement

import argparse

def main():
    parser = argparse.ArgumentParser(description="API Security Pentest Toolkit")
    # ... existing arguments ...

    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.3,
        help="Minimum relevance score (0.0-1.0) to run a test. "
             "Lower = more tests, higher coverage. "
             "Higher = faster, fewer tests. Default: 0.3",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: raise relevance threshold to 0.6 for quicker scans",
    )

    args = parser.parse_args()

    config["relevance_threshold"] = args.relevance_threshold
    if args.fast:
        config["relevance_threshold"] = max(0.6, args.relevance_threshold)
        print("Fast mode: relevance threshold set to 0.6")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Run all tests unconditionally | Context-aware test selection | 2024-2025 | Major -- reduces noise, improves relevance |
| Hardcoded Bearer auth | Profile-driven auth adaptation | Phase 5 (2026) | Tests work with apiKey, Basic, OAuth2, cookies |
| Crash on XML errors | defusedxml + graceful fallback | 2021 (defusedxml 0.7.1) | Security + stability |
| HTTP status only for success | Learned response patterns | Phase 2 (2026) | Catches soft failures (200 with error body) |

**Deprecated/outdated:**
- `xml.etree.ElementTree` for untrusted input: Replaced by defusedxml for security
- Unconditional test execution: Replaced by applicability + relevance scoring

## Open Questions

Things that couldn't be fully resolved:

1. **GraphQL-specific scenario set**
   - What we know: Architecture filtering will skip REST-only tests on GraphQL APIs
   - What's unclear: Which existing scenarios have GraphQL-specific variants needed? Are S04 injections applicable to GraphQL (yes, via query variables)?
   - Recommendation: For Phase 6, annotate existing scenarios. GraphQL-specific scenarios (depth limiting, introspection abuse) are future work.

2. **Relevance score persistence**
   - What we know: Scores are calculated per-run
   - What's unclear: Should scores be cached in the profile for reporting?
   - Recommendation: Calculate at runtime, log to report. Profile caching is optional future enhancement.

3. **HYBRID architecture handling**
   - What we know: Some APIs expose both REST and GraphQL endpoints
   - What's unclear: Should HYBRID run all tests or intelligently route?
   - Recommendation: HYBRID should match both REST and GraphQL applicability lists. Run the superset of applicable tests.

## Sources

### Primary (HIGH confidence)
- `requests` library documentation (psf/requests) - Content-Type header access, response.json(), response.text
- defusedxml PyPI documentation - Safe XML parsing API, version 0.7.1
- CONTEXT.md - Locked decisions for scoring formula, architecture matching, format handling
- Codebase analysis - api_discovery.py, base_scenario.py, runner.py, models.py

### Secondary (MEDIUM confidence)
- [GraphQL Cop security scanner](https://github.com/dolevf/graphql-cop) - Test organization pattern (exclusion-based filtering)
- OWASP API Security Testing Guide - Response format handling best practices

### Tertiary (LOW confidence)
- Web search results on test relevance scoring - General patterns, not Python-specific

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - defusedxml is the industry standard, stdlib json is universal
- Architecture patterns: HIGH - Based directly on codebase structure and CONTEXT.md decisions
- Pitfalls: HIGH - Derived from codebase analysis and security testing experience
- Code examples: HIGH - Verified against existing codebase patterns and library docs

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable domain, no rapid changes expected)
