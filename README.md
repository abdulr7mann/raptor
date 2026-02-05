- [![Twitter](https://img.shields.io/twitter/follow/abdulr7mann?style=social)](https://twitter.com/intent/follow?screen_name=abdulr7mann)
- [![Discord](https://user-images.githubusercontent.com/7288322/34429152-141689f8-ecb9-11e7-8003-b5a10a5fcb29.png?label=Join&style=social)](https://discord.gg/pN5dPYu)

# Raptor [![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?label=Tweet%20it&style=social)](https://twitter.com/intent/tweet?text=Raptor%20-%20Adaptive%20API%20security%20testing%20that%20learns%20before%20it%20strikes.%20Auto-discovery,%20OWASP%20tests,%20minimal%20false%20positives.%20by%20@abdulr7mann%20https://github.com/abdulr7mann/raptor&hashtags=security,api,pentest,owasp,hacking)

An adaptive API security testing toolkit that learns before it strikes. It discovers authentication schemes, classifies endpoints, and executes OWASP-based security tests with high accuracy and minimal false positives. Works with REST, GraphQL, and spec-less APIs.

## Features

- **Auto-Discovery**: Detects auth schemes (Bearer, API key, OAuth2, session cookies), API architecture (REST/GraphQL), and endpoint classification
- **Spec-less Mode**: Just provide a URL - discovers OpenAPI specs or fuzzes endpoints with Kiterunner
- **Response Learning**: Analyzes success/failure patterns to eliminate HTTP 200 + fail body false positives
- **Smart Filtering**: Skips irrelevant tests (no rate limit bypass tests when no rate limiting exists)
- **Path Parameter Injection**: Detects dynamic path parameters (`/users/v1/{username}`) and tests for SQLi/BOLA
- **13 OWASP Tests**: Token reuse, IDOR, injection, privilege escalation, mass assignment, user enumeration, and more
- **Confidence Levels**: Findings classified as CONFIRMED, LIKELY, or UNCERTAIN with validation signals
- **Evidence Capture**: Full HTTP request/response with syntax highlighting in HTML reports
- **Auto-Update**: Automatically pulls latest changes from git on startup (disable with `--no-update`)

## Installation

```bash
git clone https://github.com/abdulr7mann/raptor.git
cd raptor
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Usage

### With OpenAPI/Swagger spec
```bash
python run_pentest.py --input swagger.json --config pentest.yaml
```

### With Postman collection
```bash
python run_pentest.py --input collection.json --env environment.json --config pentest.yaml
```

### Spec-less mode (auto-discovery)
```bash
python run_pentest.py --url https://api.example.com --config pentest.yaml
```

### Run specific scenarios
```bash
python run_pentest.py --input swagger.json --config pentest.yaml --scenarios s01,s03,s07
```

### Fast scan (higher relevance threshold)
```bash
python run_pentest.py --input swagger.json --config pentest.yaml --fast
```

### Skip auto-update check
```bash
python run_pentest.py --input swagger.json --config pentest.yaml --no-update
```

## Config Example

```yaml
base_url: "http://localhost:5000"
auth:
  type: "oauth2"
  client_id: "your-client-id"
  client_secret: "your-secret"
  token_url: "http://localhost:5000/oauth/token"
output_dir: "reports"
scenarios:
  - s01  # Token Reuse
  - s02  # Rate Limiting
  - s03  # IDOR
  - s07  # Access Controls
```

## Test Scenarios

| ID | Category | Description |
|----|----------|-------------|
| S01 | Token Reuse | Tests for improper token invalidation |
| S02 | Rate Limiting | Detects missing or bypassable rate limits |
| S03 | IDOR | Insecure direct object reference (path usernames, unauthorized password change) |
| S04 | Injection | SQL, NoSQL, command, SSTI injection via path/query/body params |
| S05 | Auth Hijacking | JWT attacks, user enumeration via login responses |
| S06 | Function Auth | Broken function-level authorization |
| S07 | Access Controls | Authentication bypass attempts |
| S08 | Data Exposure | Sensitive data in responses, mass assignment detection |
| S09 | Business Logic | Flow manipulation and abuse |
| S10 | Mass Assignment | Property injection via excess fields |
| S11 | Security Misconfig | Headers, CORS, debug endpoints |
| S12 | Unsafe Consumption | SSRF and external resource abuse |
| S13 | Resource Exhaustion | DoS via large payloads, deep nesting |

## Output

Reports are generated in HTML and JSON formats with:
- Findings grouped by severity with confidence levels
- Full HTTP evidence (request + response)
- Syntax-highlighted code blocks
- "Not Applicable" section for skipped tests
- Filter by confidence level

## Requirements

- Python 3.10+

### Kiterunner (Auto-installed)

For spec-less mode, Raptor uses [Kiterunner](https://github.com/assetnote/kiterunner) for intelligent endpoint discovery.

**Kiterunner is auto-installed** when you run spec-less mode (`--url`) for the first time. No manual setup needed.

- Binary is downloaded to `~/.local/bin/`
- Wordlists are fetched remotely from Assetnote CDN (no local download)
- Falls back to built-in wordlist if installation fails

Manual install (optional):
```bash
python scripts/setup_kiterunner.py
```
```diff
- Only use this tool on APIs you have authorization to test.
- Unauthorized security testing is illegal.
```
