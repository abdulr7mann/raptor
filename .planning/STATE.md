# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** Accuracy -- findings must be real vulnerabilities, not false positives
**Current focus:** Phase 6: Adaptive Test Execution COMPLETE.

## Current Position

Phase: 6 of 7 (Adaptive Test Execution)
Plan: 2 of 2 in current phase -- COMPLETE
Status: Phase complete
Last activity: 2026-02-05 -- Completed 06-03-PLAN.md (Runner Integration)

Progress: [#########.] ~86% (6/7 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 3.8min
- Total execution time: 53min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-evidence-report-quality | 2/2 | 8min | 4min |
| 02-response-pattern-learning | 2/2 | 6min | 3min |
| 03-endpoint-classification | 2/2 | 6min | 3min |
| 04-prerequisite-aware-testing | 2/2 | 5min | 2.5min |
| 05-api-discovery-profiling | 2/2 | 9min | 4.5min |
| 06-adaptive-test-execution | 2/2 | 12min | 6min |

**Recent Trend:**
- Last 5 plans: 06-03 (5min), 06-01 (7min), 05-02 (5min), 05-01 (4min), 04-02 (2min)
- Trend: stable at 4-6min/plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 7 phases derived from requirement dependencies, not research's 3-phase suggestion. Research combined too much into single phases, losing verifiable delivery boundaries.
- [Roadmap]: Phase 1 starts with reporting fixes (no new capabilities needed) to establish clean output before measuring FP elimination.
- [Roadmap]: FIX requirements distributed to the phases that implement the capability fixing them, not grouped into a separate "fixes" phase.
- [01-01]: Collect-then-emit pattern for threshold-gated findings preserves original threshold logic while producing per-endpoint output.
- [01-01]: S11 security_headers restructured from header-first to endpoint-first loop for natural per-endpoint findings.
- [01-02]: HttpLexer used for both request and response evidence highlighting (simpler than separate lexers).
- [01-02]: Evidence HTML pre-rendered in Python via _format_evidence_html() returning Markup, not via Jinja2 filter.
- [01-02]: Deduplication key is (title, endpoint) tuple -- first occurrence kept, duplicates silently dropped.
- [01-02]: Evidence bodies never truncated -- removed [:2000] from Evidence.to_dict().
- [02-01]: POST/PUT/DELETE endpoints only probed without auth to avoid state mutation.
- [02-01]: is_real_success() defaults to True when no pattern learned (no regression).
- [02-01]: is_success_status() preserved unchanged for backward compatibility.
- [02-02]: Targeted is_real_success replacement at 11 attack-validation sites; baseline/precondition checks preserved as is_success_status.
- [02-02]: S13 type_confusion, oversized_payload, encoding_attacks kept as is_success_status -- they check server errors/infrastructure limits, not body-level success.
- [03-01]: Auth-endpoint path detection runs before OpenAPI security tier -- purpose-based classification is independent of security requirement.
- [03-01]: Default classification is PROTECTED (conservative -- assume auth needed unless positive signal).
- [03-01]: _get_raw_spec() re-loads input file via InputDetector rather than caching during parse_input().
- [03-02]: Only auth-related S07 tests skip public endpoints; non-auth tests (undocumented methods, CORS, debug) unchanged.
- [03-02]: EXPECTED_AUTH_FIELDS on S08 class, not BaseScenario -- scenario-specific constant.
- [04-01]: Three-state DetectionStatus (PRESENT/ABSENT/UNCERTAIN) -- UNCERTAIN means bypass tests still run (conservative).
- [04-01]: Only header_bypass_attempt is gated; burst_requests, response_time_degradation, rate_limit_header_check remain ungated (detection tests).
- [04-01]: PrerequisiteChecker runs after classification and before scenario loop.
- [04-02]: String prefix convention ("Precondition not met:") for filtering prerequisite skips -- no model changes needed.
- [04-02]: Not Applicable section placed between Findings and Test Results in HTML report.
- [04-02]: S11._test_security_headers() deliberately not gated -- missing headers IS the finding.
- [05-01]: Swagger 2.0 type:'basic' mapped directly without scheme field check (differs from OpenAPI 3.x type:'http'+scheme:'basic').
- [05-01]: GraphQL introspection POST allowed as read-only exception to no-mutation rule.
- [05-01]: WWW-Authenticate parser uses simple regex matching for known schemes (Bearer, Basic, OAuth).
- [05-01]: RequestBudget shared across all detection subsystems with 30-request default cap.
- [05-02]: Profile version check rejects incompatible cached profiles (forces re-discovery).
- [05-02]: Discovery step runs after prerequisites and before scenario loop in runner.
- [05-02]: Target name derived from input_file stem or base_url hostname for profile files.
- [06-01]: ApplicabilityMode enum with ANY/ALL/EXCLUDE for flexible matching.
- [06-01]: Weighted scoring: architecture 0.4, classification 0.3, prerequisite 0.3.
- [06-01]: Default threshold 0.3 allows tests with at least one dimension match.
- [06-01]: defusedxml for XXE-protected XML parsing in ResponseFormatHandler.
- [06-02]: S03 IDOR excludes GraphQL (different pattern for object references).
- [06-02]: S08 API Responses excludes auth-endpoint (returns credentials by design).
- [06-02]: api_profile.content_types_observed used for content-type adaptation.
- [06-03]: Pre-filtered endpoints passed to scenario.setup() rather than letting scenarios filter internally.
- [06-03]: Skipped test output limited to first 3 per scenario to avoid log spam.
- [06-03]: Fast mode sets threshold to max(0.6, current) for quicker scans.

### Pending Todos

None yet.

### Blockers/Concerns

- Python version compatibility: jsonschema 4.26.0 requires Python >= 3.10. Verify project minimum before Phase 5.
- Diverse test targets: Only VAmPI available. Need additional API targets to avoid overfitting. Identify during Phase 5 execution.

## Session Continuity

Last session: 2026-02-05
Stopped at: Completed 06-03-PLAN.md. Phase 6 complete. Ready for Phase 7.
Resume file: None
