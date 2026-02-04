# Phase 5: API Discovery & Profiling - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Probe APIs to discover authentication scheme, architecture type, and build a reusable profile that captures everything learned. The profile feeds into Phase 6 (adaptive test execution) and Phase 7 (advanced validation). This phase does NOT execute security tests — it only observes and records.

</domain>

<decisions>
## Implementation Decisions

### Auth Detection Strategy
- Spec-first: extract auth schemes from OpenAPI `securityDefinitions`/`components.securitySchemes` when available — cheapest, most reliable signal
- Active probing as fallback: when no spec or spec lacks security info, probe endpoints with unauthenticated requests and parse `WWW-Authenticate` headers and 401/403 response patterns
- Schemes to detect: Bearer token, API key (header + query param), Basic auth, session cookie, OAuth2 (detect grant type from token endpoint behavior)
- Multi-auth handling: detect all schemes present, map which endpoints use which scheme (some APIs mix public API key + admin Bearer)
- Probing method: send unauthenticated requests to 3-5 representative endpoints (mix of GET and POST), parse 401/403 responses for auth hints, never attempt actual authentication during discovery

### Profile Contents & Reuse
- Profile captures: auth scheme(s), architecture type (REST/GraphQL/SOAP), base URL, endpoint count, content types observed, server fingerprint (Server header), discovered security headers, endpoint classifications (from Phase 3), response pattern signatures (from Phase 2)
- Persistence: single JSON file, named by target (e.g., `profiles/vampi-api.profile.json`)
- Staleness: profile includes hash of input spec + target base URL; changed hash triggers re-discovery
- Includes `created_at` timestamp for manual staleness judgment
- Schema versioning: `profile_version` field — incompatible profile versions trigger automatic re-discovery

### Discovery Aggressiveness
- Spec-first, probe-second: extract maximum information from spec before making any requests; active probing fills gaps only
- Request budget: cap discovery at ~20-30 requests; use HEAD/OPTIONS where possible before full GET/POST
- Rate limiting: if target returns 429 during discovery, back off and log rate limit headers; discovery should never trigger abuse protections
- No mutation during discovery: only GET, HEAD, OPTIONS; never POST/PUT/DELETE during discovery phase
- Fail gracefully: if discovery is incomplete (target down, rate limited), proceed with partial profile and log gaps

### GraphQL Handling
- Detection: check common endpoints (`/graphql`, `/api/graphql`, `/gql`) with introspection query; also detect from spec if `x-graphql` hints or `/graphql` paths exist
- Introspection: if detected, send standard `__schema` introspection query; extract types, queries, mutations, subscriptions at top level
- Disabled introspection: mark as GraphQL with `introspection_available: false`; use any spec/schema info available; log that test coverage will be limited
- Schema depth: top-level only during discovery — types, fields, arguments; deep traversal is a test-time concern, not discovery

### Claude's Discretion
- JSON profile schema design (field names, nesting structure)
- Internal architecture of discovery components
- Exact request ordering and timing during active probing
- How to integrate Phase 2 (response patterns) and Phase 3 (endpoint classification) data into the profile
- Error handling and retry logic internals

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-api-discovery-profiling*
*Context gathered: 2026-02-04*
