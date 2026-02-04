# Phase 1: Evidence & Report Quality - Research

**Researched:** 2026-02-04
**Domain:** Python report generation, HTML escaping/XSS prevention, finding deduplication, aggregate finding decomposition
**Confidence:** HIGH

## Summary

This phase fixes the output of existing security tests so every finding includes its endpoint, HTTP evidence, and is unique. The current codebase has a functional report generator (`api_pentest/reporting/report_generator.py`) that produces JSON and HTML reports but has four systematic issues: (1) aggregate findings from scenarios S01, S02, S05, and S11 are missing endpoint and evidence fields, (2) the HTML report has an XSS vulnerability because evidence blocks are inserted without escaping, (3) there is no deduplication of findings, and (4) the Evidence model truncates response bodies at 2000 characters.

The project already has Jinja2 in `requirements.txt` but does not use it -- the HTML report uses manual `str.replace()` with a hardcoded template string. The fix strategy is to migrate the report generator to use Jinja2 with `autoescape=True` (solving XSS), add Pygments for syntax-highlighted evidence blocks, implement post-processing deduplication keyed on `(title, endpoint, method)`, and refactor aggregate scenarios to emit per-endpoint findings.

**Primary recommendation:** Use Jinja2 with autoescape (already a dependency) for HTML generation, Pygments for evidence syntax highlighting, and a simple set-based deduplication pass as post-processing before report generation.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.0+ | HTML report template rendering with autoescape | Already in requirements.txt; Python standard for safe HTML templating; autoescape prevents XSS by default |
| html (stdlib) | 3.2+ | Fallback HTML escaping via `html.escape()` | Python stdlib, zero dependencies; use for non-template escaping (JSON serialization edge cases) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pygments | 2.19+ | Syntax highlighting for HTTP evidence blocks | HTML report evidence display; has built-in `HttpLexer` and `JsonLexer` |
| MarkupSafe | 2.1+ | Safe string type used by Jinja2 | Installed automatically as Jinja2 dependency; `Markup()` class for pre-escaped content |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pygments for highlighting | Plain `<pre>` blocks with CSS | Simpler but no semantic highlighting; Pygments adds ~3MB but provides HTTP-aware tokenization |
| Jinja2 autoescape | Manual `html.escape()` everywhere | Manual escaping is error-prone -- every new template variable requires remembering to escape; Jinja2 autoescape is automatic |
| Jinja2 templates | Keep manual str.replace() | Current approach; no autoescape, fragile, hard to maintain; Jinja2 is already a dependency |

**Installation:**
```bash
pip install pygments>=2.19.0
```
Note: Jinja2 and MarkupSafe are already in requirements.txt. Only Pygments needs to be added.

## Architecture Patterns

### Recommended Project Structure
```
api_pentest/
  reporting/
    report_generator.py   # ReportGenerator class (refactored)
    templates/
      report.html         # Jinja2 HTML template (extracted from inline string)
    dedup.py              # Deduplication post-processor
  core/
    models.py             # Finding, Evidence, TestResult (modified)
```

### Pattern 1: Jinja2 Environment with Autoescape for Report Generation
**What:** Replace manual `str.replace()` HTML generation with Jinja2 `Environment(autoescape=True)` rendering
**When to use:** Any time HTML output is generated from user-controlled or API-response data
**Example:**
```python
# Source: Jinja2 official docs (https://jinja.palletsprojects.com/en/stable/api/)
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("api_pentest/reporting/templates"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

def generate_html(self, results, findings):
    template = env.get_template("report.html")
    html = template.render(
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=self._build_summary(results, findings),
        findings=sorted(findings, key=lambda f: list(Severity).index(f.severity)),
        results=results,
    )
    path = self.output_dir / f"report_{self._timestamp}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)
```

### Pattern 2: Pygments Syntax-Highlighted Evidence Blocks
**What:** Use Pygments `highlight()` with `HttpLexer` for request/response and `JsonLexer` for JSON bodies, outputting inline-styled HTML
**When to use:** Rendering HTTP evidence in HTML reports
**Example:**
```python
# Source: Pygments docs (https://pygments.org/docs/quickstart/)
from pygments import highlight
from pygments.lexers import HttpLexer, JsonLexer, TextLexer
from pygments.formatters import HtmlFormatter
from markupsafe import Markup
import json

def format_evidence_html(evidence: Evidence) -> Markup:
    """Format evidence as syntax-highlighted HTML. Returns Markup (pre-escaped)."""
    formatter = HtmlFormatter(
        noclasses=True,   # inline styles, no external CSS needed
        style="monokai",  # dark theme matching report
        nowrap=False,     # wrap in <div class="highlight">
    )

    # Format request
    request_text = (
        f"{evidence.request_method} {evidence.request_url}\n"
        + "\n".join(f"{k}: {v}" for k, v in evidence.request_headers.items())
    )
    if evidence.request_body:
        request_text += "\n\n" + _format_body(evidence.request_body)

    # Format response
    response_text = f"HTTP/1.1 {evidence.response_status}\n"
    response_text += "\n".join(
        f"{k}: {v}" for k, v in evidence.response_headers.items()
    )
    if evidence.response_body:
        response_text += "\n\n" + evidence.response_body

    request_html = highlight(request_text, HttpLexer(), formatter)
    response_html = highlight(response_text, HttpLexer(), formatter)

    # Markup() tells Jinja2 this content is already safe (pre-escaped by Pygments)
    return Markup(
        f'<div class="evidence-request"><strong>Request</strong>{request_html}</div>'
        f'<div class="evidence-response"><strong>Response</strong>{response_html}</div>'
        f'<div class="evidence-timing">Response time: {evidence.response_time_ms:.0f}ms</div>'
    )
```

### Pattern 3: Post-Processing Deduplication
**What:** Deduplicate findings after all scenarios have run, using a composite key of (title, endpoint, HTTP method)
**When to use:** After `runner.py` collects all findings from all scenarios, before passing to report generator
**Example:**
```python
def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Remove duplicate findings. Keep first occurrence.
    Key: (title, endpoint, method extracted from endpoint string).
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []

    for finding in findings:
        # Extract method from endpoint string like "GET /users/v1"
        # or use empty string if endpoint has no method prefix
        key = (finding.title, finding.endpoint)
        if key not in seen:
            seen.add(key)
            unique.append(finding)

    return unique
```

### Pattern 4: Aggregate Finding Decomposition (Split per Endpoint)
**What:** Refactor aggregate tests that loop over multiple endpoints and emit a single finding into per-endpoint findings
**When to use:** Scenarios S01, S02, S05, S11 that currently report "accepted by N/M endpoints" as one finding
**Example (before):**
```python
# CURRENT: Single aggregate finding, no endpoint, no evidence
if ratio > 0.8:
    self.log_finding(
        severity=Severity.MEDIUM,
        title="Token accepted across most endpoints",
        description=f"A single token was accepted by {accepted_count}/{tested} endpoints.",
        remediation="Implement fine-grained scope validation.",
    )
```
**Example (after):**
```python
# FIXED: Per-endpoint findings with evidence
for ep in self.endpoints:
    evidence = self.make_request(ep, token=token)
    if self.is_success_status(evidence.response_status):
        self.log_finding(
            severity=Severity.MEDIUM,
            title="Token accepted across most endpoints",
            description=(
                f"A single token was accepted at this endpoint. "
                f"Token may have excessive scope."
            ),
            endpoint=f"{ep.method} {ep.url}",
            evidence=evidence,
            remediation="Implement fine-grained scope validation per endpoint.",
        )
```

### Anti-Patterns to Avoid
- **Inline HTML construction with f-strings for evidence:** The current `evidence_block` at `report_generator.py:119-123` builds HTML with unescaped response bodies. Never insert API response data into HTML without escaping.
- **Deduplication during scan execution:** Running dedup inside scenarios changes test behavior. Keep it as post-processing only.
- **Truncating evidence bodies in the model:** `Evidence.to_dict()` at line 116 truncates `response_body[:2000]`. The decision is "never truncate response bodies." Remove the truncation from the model; let the report formatter handle display.
- **Using `|safe` filter for untrusted data in Jinja2:** Pygments output is safe (it escapes internally), but raw evidence strings are not. Only use `|safe` or `Markup()` for content that has been pre-escaped by a trusted library.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping | Custom `_escape()` function (current) | Jinja2 `autoescape=True` | Current `_escape()` misses single-quote escaping; Jinja2 handles all HTML entities automatically via MarkupSafe |
| HTTP evidence syntax highlighting | Manual CSS coloring with regex | Pygments `HttpLexer` + `HtmlFormatter` | HTTP has complex grammar (headers, status lines, bodies); Pygments tokenizes it correctly |
| JSON body highlighting | Manual string formatting | Pygments `JsonLexer` | Handles nested structures, string escaping, number formatting |
| HTML template rendering | `str.replace("{{var}}", value)` (current) | Jinja2 `Environment.get_template()` | Current approach has no escaping, no conditionals, no loops; Jinja2 provides all three with autoescape |

**Key insight:** The project already depends on Jinja2 but doesn't use it. The current manual HTML construction is the root cause of both the XSS vulnerability and the fragile template code. Migrating to Jinja2 solves both problems simultaneously.

## Common Pitfalls

### Pitfall 1: Escaping Evidence in Wrong Layer
**What goes wrong:** Escaping response bodies in `Evidence.to_dict()` (model layer) breaks JSON report output with double-escaped entities (`&amp;amp;`). Or escaping too late in the HTML template leaves a window for XSS.
**Why it happens:** Unclear boundary between "store raw data" and "render safely."
**How to avoid:** Keep `Evidence` model raw (no escaping). Escape only at render time: Jinja2 autoescape handles HTML; JSON serialization handles JSON. The model stores truth; renderers handle presentation.
**Warning signs:** `&amp;` appearing in JSON reports; `<script>` tags rendering in HTML reports.

### Pitfall 2: Pygments Output Double-Escaping in Jinja2
**What goes wrong:** Pygments `HtmlFormatter` produces HTML with `<span>` tags. If Jinja2 autoescape is on and the output is passed as a regular string, Jinja2 will escape the `<span>` tags, showing raw HTML entities instead of styled code.
**Why it happens:** Jinja2 autoescape escapes everything that is not marked as `Markup`.
**How to avoid:** Wrap Pygments output in `markupsafe.Markup()` before passing to Jinja2, or use the `|safe` filter in the template for the Pygments HTML variable. Since Pygments itself escapes the code content, the `<span>` wrapper tags are safe.
**Warning signs:** Evidence blocks showing `&lt;span style=...&gt;` instead of colored text.

### Pitfall 3: Deduplication Key Too Broad or Too Narrow
**What goes wrong:** If dedup key is just `(title)`, legitimate separate findings on different endpoints collapse into one. If key includes too much (e.g., full description), findings that differ only in wording are not deduped.
**Why it happens:** Finding uniqueness is domain-specific -- same vulnerability on different endpoints is separate; same vulnerability with different descriptions on same endpoint is a duplicate.
**How to avoid:** Use `(title, endpoint)` as the key. The `endpoint` field already contains the HTTP method (e.g., "GET /users/v1"). Different parameters on the same endpoint produce different titles (e.g., "SQLi via id" vs "SQLi via name"), so they are naturally distinct.
**Warning signs:** Reports with 1 finding where there should be 10 (too broad); reports with 10 identical-looking findings (too narrow).

### Pitfall 4: Aggregate Decomposition Creating Too Many Findings
**What goes wrong:** Splitting "token accepted by 7/10 endpoints" into 7 separate findings bloats the report with repetitive entries that all say the same thing.
**Why it happens:** Per-endpoint splitting is mechanically correct but not always the most useful report format.
**How to avoid:** The decision says "split aggregate tests into one finding per endpoint." This is correct -- the deduplication step will collapse true duplicates. Use the same vulnerability title for all split findings; the endpoint field distinguishes them. Consider adding a scenario/group ID so report consumers can see these came from the same test run (Claude's discretion).
**Warning signs:** Reports jumping from 58 findings to 200+ after decomposition. If this happens, review whether findings are being generated for clean endpoints (they should not be).

### Pitfall 5: Evidence Body Truncation Sneaking Back
**What goes wrong:** The `Evidence.to_dict()` method at line 116 truncates `response_body[:2000]`. The HTML template at line 123 further truncates to `[:500]`. These contradict the "never truncate" decision.
**Why it happens:** Original developers were protecting against large responses in reports.
**How to avoid:** Remove both truncations. The Evidence model stores full response bodies. The HTML template renders full bodies inside collapsible `<details>` blocks (already partially present). For the JSON report, the full body is serialized. Let consumers decide if they need to truncate.
**Warning signs:** Evidence blocks ending with `...` or cut off mid-sentence.

### Pitfall 6: Missing Single-Quote Escaping in Current _escape()
**What goes wrong:** The current `_escape()` function at `report_generator.py:184-192` does NOT escape single quotes (`'`). A response body containing `' onclick='alert(1)'` inside an HTML attribute delimited by single quotes would execute JavaScript.
**Why it happens:** Manual escaping functions miss edge cases. The function handles `&`, `<`, `>`, `"` but not `'`.
**How to avoid:** Use Jinja2 autoescape (handles all five characters via MarkupSafe) or `html.escape(text, quote=True)` from Python stdlib (escapes `'` as `&#x27;`).
**Warning signs:** XSS payloads with single quotes working in the report.

## Code Examples

Verified patterns from official sources:

### Jinja2 Environment Setup with Autoescape
```python
# Source: Jinja2 docs (https://jinja.palletsprojects.com/en/stable/api/)
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("api_pentest/reporting/templates"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

### Pygments HTTP Evidence Highlighting
```python
# Source: Pygments docs (https://pygments.org/docs/quickstart/,
#         https://pygments.org/docs/lexers/, https://pygments.org/docs/formatters/)
from pygments import highlight
from pygments.lexers import HttpLexer, JsonLexer, TextLexer
from pygments.formatters import HtmlFormatter
from markupsafe import Markup

# Dark-theme inline formatter (no external CSS required)
_formatter = HtmlFormatter(noclasses=True, style="monokai")

def highlight_http(text: str) -> Markup:
    """Highlight HTTP request/response text. Returns pre-escaped Markup."""
    return Markup(highlight(text, HttpLexer(), _formatter))

def highlight_json(text: str) -> Markup:
    """Highlight JSON body text. Returns pre-escaped Markup."""
    return Markup(highlight(text, JsonLexer(), _formatter))

def highlight_body(body: str) -> Markup:
    """Auto-detect body format and highlight."""
    stripped = body.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            import json
            json.loads(stripped)
            return highlight_json(stripped)
        except (json.JSONDecodeError, ValueError):
            pass
    return Markup(highlight(body, TextLexer(), _formatter))
```

### Post-Processing Deduplication in Runner
```python
# Integration point: runner.py, after all scenarios complete
def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Remove duplicate findings. Keep first occurrence, silently drop rest.
    Uniqueness key: title + endpoint (endpoint includes HTTP method).
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.title, finding.endpoint)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique

# In PentestRunner.run(), before report generation:
self.all_findings = deduplicate_findings(self.all_findings)
```

### html.escape for Non-Template Contexts
```python
# Source: Python docs (https://docs.python.org/3/library/html.html)
import html

# Use html.escape when not inside Jinja2 template (e.g., terminal output)
safe_text = html.escape(untrusted_string, quote=True)
# Escapes: & < > " ' (all five characters)
```

### Evidence Model Without Truncation
```python
# Modified Evidence.to_dict() -- remove [:2000] truncation
def to_dict(self) -> dict:
    return {
        "request": {
            "method": self.request_method,
            "url": self.request_url,
            "headers": self.request_headers,
            "body": self.request_body,
        },
        "response": {
            "status": self.response_status,
            "headers": self.response_headers,
            "body": self.response_body if self.response_body else "",
            "time_ms": self.response_time_ms,
        },
        "timestamp": self.timestamp,
    }
```

## Codebase Findings: Current State Inventory

Specific locations and issues that must be addressed in this phase:

### Files Requiring Modification

| File | What Changes | Why |
|------|-------------|-----|
| `api_pentest/core/models.py:116` | Remove `[:2000]` truncation from `Evidence.to_dict()` | Decision: never truncate response bodies |
| `api_pentest/reporting/report_generator.py` | Rewrite to use Jinja2 `Environment(autoescape=True)` | Fixes XSS (RPT-03), improves maintainability |
| `api_pentest/reporting/report_generator.py:119-123` | Replace unescaped evidence block with Pygments-highlighted, Jinja2-rendered block | Fixes XSS, adds syntax highlighting |
| `api_pentest/reporting/report_generator.py:184-192` | Remove `_escape()` function (replaced by Jinja2 autoescape) | Jinja2 handles escaping; `_escape()` misses single quotes |
| `api_pentest/scenarios/s01_token_reuse.py:65-73,118-126,168-177` | Split aggregate findings into per-endpoint findings with evidence | FIX-05, FIX-06 for S01 (3 findings) |
| `api_pentest/scenarios/s02_rate_limiting.py:95-106,142-150,189-197` | Split aggregate findings; add endpoint and evidence | FIX-05, FIX-06 for S02 (3 findings) |
| `api_pentest/scenarios/s05_auth_hijacking.py:72-80,114-122,156-167,201-209` | Split aggregate findings into per-endpoint findings | FIX-05, FIX-06 for S05 (4 findings) |
| `api_pentest/scenarios/s11_security_misconfig.py:124-133` | Split "Multiple endpoints" findings into per-endpoint | FIX-05, FIX-06 for S11 security headers (N findings) |
| `api_pentest/runner.py` | Add deduplication step before report generation | RPT-04 |
| `requirements.txt` | Add `pygments>=2.19.0` | New dependency for syntax highlighting |

### Aggregate Findings Inventory (FIX-05, FIX-06)

Scenarios with aggregate findings that need decomposition:

| Scenario | Method | Finding(s) | Current Problem |
|----------|--------|-----------|-----------------|
| S01 `_test_cross_endpoint_replay` | Loops all endpoints, single finding | "Token accepted across most endpoints" | No `endpoint=`, no `evidence=` |
| S01 `_test_old_token_after_refresh` | Loops 10 endpoints, single finding | "Old tokens not revoked after refresh" | No `endpoint=`, `evidence=` only last tested |
| S01 `_test_cross_user_token_swap` | Loops 10 endpoints, single finding | "Cross-user token swap accepted" | No `endpoint=`, no `evidence=` |
| S02 `_test_burst_requests` | Loops 5 endpoints, single aggregate finding | "No rate limiting detected" | No `endpoint=`, no `evidence=` |
| S02 `_test_response_time_degradation` | Single endpoint but no evidence on finding | "Response time degradation under load" | No `endpoint=`, no `evidence=` |
| S02 `_test_rate_limit_headers` | Single endpoint, finding has no evidence | "No rate limit headers in API responses" | No `endpoint=` (uses inline text), no `evidence=` |
| S05 `_test_expired_jwt` | Loops 10 endpoints, single finding | "Expired JWT tokens accepted" | No `endpoint=`, `evidence=` only last |
| S05 `_test_tampered_signature` | Loops 10 endpoints, single finding | "JWT signature verification bypassed" | No `endpoint=`, `evidence=` only last |
| S05 `_test_alg_none` | Loops 10 endpoints, single finding | "JWT alg:none attack successful" | No `endpoint=`, `evidence=` only last |
| S05 `_test_stripped_signature` | Loops 10 endpoints, single finding | "JWT with stripped signature accepted" | No `endpoint=`, `evidence=` only last |
| S11 `_test_security_headers` | Loops 10 endpoints, aggregate | "Missing security header: X" | `endpoint="Multiple endpoints"`, no `evidence=` |

### XSS Vulnerability Details (RPT-03)

**Location:** `report_generator.py:119-123`
```python
# VULNERABLE: Response body inserted without escaping
evidence_block = f"""<details><summary>View Evidence</summary>
<div class="evidence">Request: {ev['request']['method']} {ev['request']['url']}
Status: {ev['response']['status']}
Response Time: {ev['response']['time_ms']}ms
Body: {ev['response']['body'][:500]}</div></details>"""
```

**Attack vector:** An API response containing `<script>alert(document.cookie)</script>` in the body would execute when the HTML report is opened in a browser.

**Additional issue:** The `_escape()` function exists (line 184) and is used for finding titles/descriptions (lines 128-131) but is NOT applied to evidence output. Even if it were applied, it misses single-quote escaping.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cgi.escape()` | `html.escape()` | Python 3.2 (2011), `cgi.escape` removed in 3.8 | Must use `html.escape()` or Jinja2 autoescape |
| Jinja2 autoescape off by default | Still off by default, but `select_autoescape()` is standard | Jinja2 2.9 (2016) | Always pass `autoescape=True` or `select_autoescape()` |
| Manual CSS class coloring | Pygments inline styles via `noclasses=True` | Stable pattern | Self-contained HTML reports without external CSS |
| String concatenation for HTML | Template engines (Jinja2) | Long-standing best practice | Prevents XSS, improves maintainability |

**Deprecated/outdated:**
- `cgi.escape()`: Removed in Python 3.8. Use `html.escape()` or Jinja2 autoescape.
- Manual `str.replace("{{var}}", value)` HTML templating: The current codebase pattern. Replaced by Jinja2 template rendering with autoescape.

## Open Questions

Things that couldn't be fully resolved:

1. **Scenario/Group ID for Split Findings**
   - What we know: The decision defers this to Claude's discretion. When aggregate findings are split into per-endpoint findings, it may be useful to link them with a shared identifier (e.g., `group_id` or `scenario_run_id`).
   - What's unclear: Whether this adds enough value to justify adding a field to the Finding model, or if `scenario_id` + `title` is sufficient grouping.
   - Recommendation: Add an optional `group_id` field to Finding, populated when a test generates multiple related findings from one test run. This is low cost and high value for report consumers who want to understand "these 7 findings came from the same token reuse test."

2. **Terminal Progress Format**
   - What we know: Decision says "show progress during scan (endpoints tested, findings count), full summary at end." Current code already prints per-scenario summaries.
   - What's unclear: Whether to add a progress bar (like `tqdm`) or keep the current per-scenario line output.
   - Recommendation: Keep the current per-scenario output format but add a running counter line (e.g., `[3/13 scenarios] [12 endpoints tested] [4 findings]`). No need for `tqdm` dependency -- the scan runs scenarios sequentially and the current line-by-line output is sufficient. Enhance with colorama (already a dependency).

3. **Jinja2 Template Location**
   - What we know: Template could be a separate `.html` file loaded via `FileSystemLoader`, or an inline string loaded via `Environment(autoescape=True).from_string()`.
   - What's unclear: Whether to keep the template inline (simpler packaging, current pattern) or extract to a file (better maintainability).
   - Recommendation: Extract to `api_pentest/reporting/templates/report.html`. Use `PackageLoader` or `FileSystemLoader` with a path relative to the module. This is cleaner and allows future template modifications without touching Python code. The `from_string()` approach also works if packaging is a concern.

## Sources

### Primary (HIGH confidence)
- Jinja2 official docs (`/websites/jinja_palletsprojects_en_stable` via Context7) - autoescape configuration, Environment setup, select_autoescape, from_string usage, |safe filter, Markup class
- Python stdlib `html` module docs (https://docs.python.org/3/library/html.html) - `html.escape()` function, quote parameter behavior
- Pygments PyPI (https://pypi.org/project/Pygments/) - current version 2.19.2, Python 3.8+ support
- Pygments available lexers docs (https://pygments.org/docs/lexers/) - HttpLexer class, JsonLexer class
- Pygments quickstart docs (https://pygments.org/docs/quickstart/) - highlight() function, HtmlFormatter, noclasses option

### Secondary (MEDIUM confidence)
- OWASP XSS Prevention Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) - HTML escaping best practices
- Pygments styles docs (https://pygments.org/docs/styles/) - monokai style for dark theme

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Jinja2 verified via Context7 docs; Pygments verified via PyPI and official docs; html.escape verified via Python stdlib docs
- Architecture: HIGH - Patterns derived directly from codebase analysis and official library documentation
- Pitfalls: HIGH - XSS vulnerability confirmed by reading source code; escaping gaps confirmed by comparing `_escape()` to `html.escape()` specification; truncation issue confirmed in `Evidence.to_dict()`

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (30 days -- stable libraries, no fast-moving changes expected)
