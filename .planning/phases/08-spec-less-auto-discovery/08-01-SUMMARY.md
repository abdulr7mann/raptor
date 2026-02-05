---
phase: 08-spec-less-auto-discovery
plan: 01
subsystem: core-discovery
tags: [spec-discovery, openapi, swagger, graphql, auto-discovery]
depends_on:
  requires:
    - 05-01 (RequestBudget from api_discovery)
    - 05-02 (ApiProfiler pattern)
  provides:
    - SpecDiscoverer class for probing common spec paths
    - SpecType enum for detected specification types
  affects:
    - 08-02 (EndpointProber will use SpecDiscoverer results)
    - 08-03 (CLI integration for spec-less mode)
tech_stack:
  added: []
  patterns: ["common-path-probing", "introspection-query"]
file_tracking:
  key_files:
    created:
      - api_pentest/core/spec_discoverer.py
      - api_pentest/core/__init__.py
    modified: []
decisions:
  - key: graphql-introspection-minimal
    choice: Minimal introspection query for detection
    reason: Full introspection too verbose for discovery phase; minimal query confirms GraphQL presence
  - key: spec-paths-order
    choice: JSON paths first, then YAML, then GraphQL
    reason: JSON is most common; YAML rare; GraphQL last as fallback
metrics:
  duration: 1m 48s
  completed: 2026-02-05
---

# Phase 08 Plan 01: Spec Discoverer Summary

**One-liner:** SpecDiscoverer probes 17 common spec paths (OpenAPI/Swagger/GraphQL) and returns spec content + type if found

## What Was Built

### SpecType Enum
Three specification types detectable:
- `OPENAPI_30` - OpenAPI 3.x specifications
- `SWAGGER_20` - Swagger 2.0 specifications
- `GRAPHQL` - GraphQL introspection responses

### SpecDiscoverer Class
Core auto-discovery component with:
- **SPEC_PATHS constant** - 17 ordered paths to probe:
  - JSON: /openapi.json, /swagger.json, /api-docs, /api/openapi.json, etc.
  - YAML: /openapi.yaml, /swagger.yaml
  - GraphQL: /graphql, /api/graphql, /gql, /query
- **discover() method** - Iterates paths, respects RequestBudget, returns (content, type)
- **_detect_spec_type()** - Parses JSON, checks for OpenAPI/Swagger/GraphQL markers
- **_try_graphql_introspection()** - POST minimal introspection query for GraphQL endpoints

### Key Design Decisions
1. **GraphQL paths use POST introspection** - Plain GET doesn't work for GraphQL; introspection is read-only (safe)
2. **Minimal introspection query** - `{ __schema { types { name } } }` just confirms GraphQL presence
3. **RequestBudget respected** - No request storms; stops early if budget exhausted
4. **Accept header for flexibility** - `application/json, application/yaml, */*` for various server configs

## Commits

| Hash | Message |
|------|---------|
| cec1686 | feat(08-01): create SpecDiscoverer for auto-discovery at common paths |
| 4441d63 | feat(08-01): export SpecDiscoverer and SpecType from core module |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| api_pentest/core/spec_discoverer.py | created | 251 |
| api_pentest/core/__init__.py | created | 12 |

## Verification Results

| Check | Status |
|-------|--------|
| Import from spec_discoverer | PASS |
| SpecType enum values | ['openapi_3.x', 'swagger_2.0', 'graphql'] |
| SPEC_PATHS count | 17 (>= 15 required) |
| Module line count | 251 (>= 100 required) |
| RequestBudget import pattern | PASS |
| http_client.request pattern | PASS |
| Export from api_pentest.core | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 08-02: EndpointProber can now use SpecDiscoverer to find specs before falling back to endpoint fuzzing.

**Dependencies satisfied:**
- SpecDiscoverer importable from api_pentest.core
- SpecType enum available for type checking
- RequestBudget integration verified
