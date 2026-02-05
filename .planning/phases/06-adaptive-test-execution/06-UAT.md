---
status: complete
phase: 06-adaptive-test-execution
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md]
started: 2026-02-05T14:30:00Z
updated: 2026-02-05T14:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CLI --relevance-threshold flag
expected: Running `python run_pentest.py --help` shows --relevance-threshold option with description about minimum relevance score (0.0-1.0).
result: pass

### 2. CLI --fast flag
expected: Running `python run_pentest.py --help` shows --fast option with description about raising threshold to 0.6 for quicker scans.
result: pass

### 3. Relevance threshold validation
expected: Running `python run_pentest.py -i test.json --relevance-threshold 1.5` shows error about threshold must be between 0.0 and 1.0.
result: pass

### 4. Scenario APPLICABILITY import
expected: Running `python -c "from api_pentest.scenarios.s03_idor import S03IDOR; print(S03IDOR.APPLICABILITY)"` shows ScenarioApplicability with architectures excluding GraphQL.
result: pass

### 5. ResponseFormatHandler JSON parsing
expected: Running `python -c "from api_pentest.core.response_formats import ResponseFormatHandler; h=ResponseFormatHandler(); print(h.JSON_TYPES)"` shows frozenset containing 'application/json'.
result: pass

### 6. RelevanceCalculator import and scoring
expected: Running `python -c "from api_pentest.core.relevance import RelevanceCalculator, RelevanceScore; s=RelevanceScore(0.7, 0.4, 0.3, 0.0, ''); print(f'Score: {s.total}')"` shows "Score: 0.7".
result: pass

### 7. BaseScenario has APPLICABILITY
expected: Running `python -c "from api_pentest.scenarios.base_scenario import BaseScenario; print(hasattr(BaseScenario, 'APPLICABILITY'))"` shows True.
result: pass

### 8. Runner has relevance_calculator attribute
expected: Running `python -c "from api_pentest.runner import PentestRunner; r=PentestRunner({}); print(hasattr(r, 'relevance_calculator'))"` shows True.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
