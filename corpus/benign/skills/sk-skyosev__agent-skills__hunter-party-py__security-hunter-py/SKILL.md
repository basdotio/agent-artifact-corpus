---
name: security-hunter-py
description: |
  Audit Python code for security vulnerabilities — hardcoded secrets, injection risks,
  missing input validation at trust boundaries, insecure defaults, auth gaps, sensitive data
  exposure, and unsafe patterns like eval, pickle, or shell injection.

  Use when: reviewing Python code before deployment, auditing trust boundaries, preparing
  for a security review, onboarding third-party integrations, or hardening an application.
  Reports omit empty sections — no placeholder headings, empty tables, or negative statements like "no issues found".
disable-model-invocation: true  
---

# Security Hunter

Audit code for **security vulnerabilities** — places where untrusted input flows into sensitive operations without
validation, secrets are embedded in source, defaults are permissive, or auth checks are missing. The goal: **every
trust boundary validates its inputs, no secrets live in code, and the principle of least privilege is applied
throughout.**

## When to Use

- Reviewing code before production deployment
- Auditing trust boundaries (API endpoints, form handlers, webhooks)
- Preparing for a formal security review or pen test
- Onboarding third-party integrations or new external data sources
- Hardening an application after a security incident

## Core Principles

1. **Trust boundaries are the perimeter.** Every point where external data enters the system — HTTP requests, file
   uploads, environment variables, database reads, third-party API responses, CLI arguments — is a trust boundary.
   Input must be validated, sanitized, or escaped before it flows into operations that could be exploited.

2. **Secrets never belong in source control.** API keys, passwords, tokens, certificates, and connection
   strings must come from a secure source — environment variables, secret managers, vault services, or encrypted
   config — never from source files, comments, or committed configuration.

3. **Default to deny.** Defaults should be restrictive: CORS origins explicit not `*`, auth required not optional,
   permissions minimal not broad. Permissive defaults are the most common class of security misconfiguration.

4. **Defense in depth.** No single validation layer is sufficient. Validate at the boundary, escape at the output,
   enforce at the data layer. If one layer fails, another should catch the exploit.

5. **Fail closed.** When auth/authz checks fail or raise, the result should be denial, not access. Error paths must
   not bypass security controls.

## What to Hunt

### 1. Hardcoded Secrets

API keys, passwords, tokens, or connection strings embedded directly in source code.

**Signals:**

- String literals matching key patterns: `sk_live_`, `AKIA`, `ghp_`, `password=`, `secret=`
- Connection strings with embedded credentials: `postgres://user:pass@host`
- Base64-encoded strings in auth headers or config
- `.env` files or secret-bearing config committed to the repo
- Comments containing credentials ("temporary key: xyz123")
- Default values in function signatures: `def connect(password="admin123")`

**Action:** Move to a secure secret source (environment variables, secret manager, vault). Add the pattern to
`.gitignore`. Rotate any committed secret immediately — it's already compromised if the repo was ever shared.

### 2. Injection Vulnerabilities

Untrusted input concatenated into strings that are interpreted as code, queries, or commands.

**Signals:**

- SQL: string concatenation or f-strings in query strings instead of parameterized queries
  (`cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")`)
- Command injection: `os.system()`, `subprocess.call(shell=True)`, `subprocess.Popen(shell=True)` with user-controlled
  arguments
- Path traversal: user input in `open()`, `pathlib.Path()`, or URL construction without sanitization
- Template injection: user input rendered in Jinja2/Mako templates with `| safe` or autoescape disabled
- Regex: user input passed directly to `re.compile()` (ReDoS risk)
- `eval()`, `exec()`, `compile()` with dynamic input
- `pickle.loads()` / `pickle.load()` on untrusted data (arbitrary code execution)
- `yaml.load()` without `Loader=SafeLoader` (arbitrary code execution)

**Action:** Use parameterized queries, allowlists, path canonicalization, template auto-escaping, or regex escaping.
Never concatenate untrusted input into interpreted strings.

### 3. Missing Input Validation at Trust Boundaries

Endpoints, handlers, or integration points that accept external data without schema validation or sanitization.

**Signals:**

- API handlers that access `request.json`, `request.args`, `request.form` without validation
  (no Pydantic, marshmallow, attrs validators, etc.)
- File upload handlers without type/size/content validation
- Webhook handlers without signature verification
- URL parameters used directly in business logic without parsing/validation
- Form inputs passed to database operations without sanitization
- CLI arguments from `argparse`/`click` used without additional validation for security-sensitive operations

**Action:** Add schema validation at every trust boundary. Validate type, format, range, and length. Reject invalid
input explicitly — don't coerce or default.

### 4. Insecure Defaults and Configuration

Permissive defaults that weaken security posture when not explicitly overridden.

**Signals:**

- CORS: `Access-Control-Allow-Origin: *` or `credentials: True` with wildcard origin
- CSRF: protection disabled or missing on state-changing endpoints
- Cookie: missing `Secure`, `HttpOnly`, or `SameSite` attributes
- TLS: certificate validation disabled (`verify=False` in requests, `ssl._create_unverified_context()`)
- Rate limiting: absent on auth endpoints or public APIs
- Debug mode: `DEBUG=True` or `app.run(debug=True)` in production config
- Django: `ALLOWED_HOSTS = ['*']`, `SECRET_KEY` hardcoded, `DEBUG = True`
- Flask: `app.secret_key` hardcoded in source

**Action:** Restrict defaults. Require explicit opt-in for permissive settings with justification.

### 5. Authentication and Authorization Gaps

Missing or inconsistent auth checks that allow unauthorized access or privilege escalation.

**Signals:**

- Routes/endpoints without auth decorators where peer routes have them
- Authorization checks that compare user IDs with string equality on user-controlled values
- Role checks using client-provided role claims without server-side verification
- Admin functionality accessible by changing a URL parameter or request body field
- Session tokens without expiry, rotation, or revocation
- Password handling: plain-text storage, weak hashing (MD5, SHA1), missing salting
  (use `bcrypt`, `argon2`, or `passlib` instead)

**Action:** Ensure every endpoint has explicit auth/authz. Check authorization server-side against the session, not
client-provided claims. Use bcrypt/argon2/passlib for password hashing.

### 6. Sensitive Data Exposure

Personal data, secrets, or internal details leaked through logs, errors, responses, or storage.

**Signals:**

- Logging of request bodies, auth headers, or user PII (`logging.info(f"User data: {request.json}")`)
- Error responses that include stack traces, internal paths, or database details (debug mode in production)
- API responses that return more fields than the client needs (no field filtering)
- Sensitive data stored in plaintext files or unencrypted databases
- PII in URLs (email, SSN, tokens in query parameters — logged by default in most servers)
- Tracebacks with local variables exposed to end users

**Action:** Strip sensitive fields from logs and error responses. Filter API responses to only required fields. Use
structured logging with field-level redaction.

### 7. Dependency and Supply-Chain Risks

Package dependencies with known vulnerabilities, unvetted install scripts, or lockfile integrity issues.

**Signals:**

- `requirements.txt` dependencies without pinned versions (`requests` instead of `requests==2.31.0`)
- Lockfile (`poetry.lock`, `Pipfile.lock`, `uv.lock`) not committed to the repo
- Packages with `setup.py` that execute arbitrary code during install
- Dependencies with known CVEs (check via `pip-audit` or `safety`)
- Importing from URLs or running `pip install` from untrusted sources at runtime

**Action:** Commit the lockfile. Pin dependency versions. Run `pip-audit` (or `safety check`) and address
critical/high findings. Review setup scripts in new dependencies before adding them.

### 8. Unsafe Code Patterns

Language-level patterns that create exploitable conditions.

**Signals:**

- `pickle.loads()` / `pickle.load()` on untrusted data (arbitrary code execution)
- `yaml.load(data)` without `Loader=yaml.SafeLoader` (arbitrary code execution)
- `eval()`, `exec()`, `compile()` with user-controlled input
- `__import__()` or `importlib.import_module()` with user-controlled arguments
- `subprocess` with `shell=True` and string arguments derived from user input
- `tempfile.mktemp()` instead of `tempfile.mkstemp()` (race condition)
- `hashlib.md5()` / `hashlib.sha1()` for security-sensitive hashing (use SHA-256+ or bcrypt)
- `random.random()` for security tokens (use `secrets` module instead)
- XML parsing with `xml.etree.ElementTree` without defusing (XXE attacks) — use `defusedxml`
- `marshal.loads()` on untrusted data

**Action:** Use `yaml.safe_load()` instead of `yaml.load()`, `secrets.token_urlsafe()` instead of `random`, `defusedxml`
for XML parsing, `subprocess.run()` with list arguments instead of `shell=True`. Never deserialize untrusted data with
`pickle`.

### 9. Framework-Specific Security Misconfigurations

Security patterns specific to popular Python web frameworks that go beyond general best practices.

**Signals:**

- **FastAPI**: `CORSMiddleware` with `allow_origins=["*"]` combined with `allow_credentials=True` (credential leakage),
  routes missing `Depends(get_current_user)` where peer routes require auth, Pydantic `Settings` with hardcoded
  `secret_key` or `jwt_secret` default values, `uvicorn.run(host="0.0.0.0")` without TLS in production config
- **Django**: `ALLOWED_HOSTS = ['*']` in production settings, `SECRET_KEY` hardcoded in `settings.py` (not from env),
  `DEBUG = True` in production settings module, `@csrf_exempt` on state-changing views without justification,
  `SECURE_SSL_REDIRECT = False` and `SESSION_COOKIE_SECURE = False` in production,
  `AUTH_PASSWORD_VALIDATORS = []` (empty password validation)
- **Flask**: `app.secret_key` hardcoded in source, `app.run(debug=True)` in production entrypoint,
  no `SESSION_COOKIE_SECURE` or `SESSION_COOKIE_HTTPONLY` configured, `send_from_directory()` or `send_file()`
  with user-controlled paths without sanitization

**Action:** Move secrets to environment variables or secret managers. Enable framework security features explicitly.
Audit route-level auth coverage against a peer-comparison table. Ensure production settings modules disable debug
and enforce HTTPS.

## Audit Workflow

### Phase 1: Map Trust Boundaries

1. **Resolve audit surface.** The prompt may specify the scope as:
   - **Diff**: files changed on the current branch vs base (`main`/`master`)
   - **Path**: specific files, folders, or layers
   - **Codebase**: the entire project
   If unspecified, default to **codebase**. For diff mode, resolve the file list:
   ```bash
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)
   SCOPE=$(git diff --name-only $(git merge-base HEAD $BASE)...HEAD)
   ```
   Constrain all subsequent scans to the resolved surface.
2. Identify trust boundaries: API route handlers, webhooks, file upload endpoints, third-party integration points,
   CLI argument parsers, config loaders.
3. Identify auth/authz middleware and where it's applied.

### Phase 2: Scan for Security Signals

```bash
EXCLUDE='--glob !**/venv/** --glob !**/.venv/** --glob !**/dist/** --glob !**/*_test.py --glob !**/test_*.py'

# Hardcoded secrets (common patterns)
rg --pcre2 '(sk_live_|AKIA|ghp_|password\s*=\s*["\x27]|secret\s*=\s*["\x27])' $EXCLUDE
rg --pcre2 '(postgres|mysql|mongodb)://\w+:\w+@' $EXCLUDE

# Injection: eval, exec, compile, pickle, yaml.load
rg '\beval\s*\(|\bexec\s*\(|\bcompile\s*\(' --type py $EXCLUDE
rg 'pickle\.(loads?|load)\s*\(' --type py $EXCLUDE
rg 'yaml\.load\s*\(' --type py $EXCLUDE

# Shell injection: subprocess with shell=True, os.system
rg 'shell\s*=\s*True|os\.system\s*\(' --type py $EXCLUDE

# SQL injection: f-strings or .format() in queries
rg --pcre2 '(execute|query)\s*\(\s*f["\x27]' --type py $EXCLUDE
rg --pcre2 '(execute|query)\s*\([^)]*\.format\(' --type py $EXCLUDE

# Insecure config
rg --pcre2 'verify\s*=\s*False|DEBUG\s*=\s*True|ALLOWED_HOSTS\s*=\s*\[\s*["\x27]\*' $EXCLUDE

# Missing auth (route definitions — project-specific, adapt pattern)
rg '@(app|router)\.(get|post|put|patch|delete)\s*\(' --type py $EXCLUDE

# Logging of sensitive data
rg --pcre2 'log(ger)?\.(info|debug|warning).*\b(password|token|secret|authorization|cookie)\b' -i --type py $EXCLUDE

# Insecure random
rg 'random\.(random|randint|choice|sample)\s*\(' --type py $EXCLUDE

# XML parsing without defusedxml
rg 'xml\.etree|xml\.dom|xml\.sax' --type py $EXCLUDE

# tempfile.mktemp (race condition)
rg 'mktemp\s*\(' --type py $EXCLUDE
```

### Phase 3: Trace Data Flows

For each trust boundary found in Phase 1:

1. Does untrusted input pass through validation before reaching sensitive operations?
2. Are query parameters, body fields, and headers validated for type, format, and range?
3. Could a malicious input reach `eval`, `exec`, a database query, `subprocess`, or `pickle.loads()`?

### Phase 4: Evaluate Auth Coverage

1. List all routes/endpoints. For each: is auth middleware applied?
2. Identify authorization logic. Is it server-side? Does it rely on client claims?
3. Check session management: expiry, rotation, revocation.

### Phase 5: Produce Report

## Output Format

Save as `YYYY-MM-DD-security-hunter-audit-{$LLM-name}.md` in the project's docs folder (or project root if no docs
folder exists).

```md
# Security Hunter Audit — {date}

## Scope

- Surface: {diff / path / codebase}
- Files: {count or list}
- Exclusions: {list}

## Trust Boundary Map

| # | Boundary | Location | Validation | Auth |
| - | -------- | -------- | ---------- | ---- |
| 1 | POST /api/users | file:line | Pydantic model | JWT middleware |
| 2 | Webhook /hooks/stripe | file:line | None | None |

## Findings

### Hardcoded Secrets

| # | Location | Pattern | Severity | Action |
| - | -------- | ------- | -------- | ------ |
| 1 | file:line | `sk_live_...` Stripe key | Critical | Move to env, rotate immediately |

### Injection Risks

| # | Location | Type | Untrusted Input | Action |
| - | -------- | ---- | --------------- | ------ |
| 1 | file:line | SQL injection | f-string in `cursor.execute()` | Use parameterized query |
| 2 | file:line | Pickle deserialization | Untrusted bytes in `pickle.loads()` | Use JSON or msgpack |

### Missing Input Validation

| # | Location | Boundary | Input | Action |
| - | -------- | -------- | ----- | ------ |
| 1 | file:line | POST /api/orders | `request.json` used without validation | Add Pydantic model |

### Insecure Defaults

| # | Location | Setting | Current | Action |
| - | -------- | ------- | ------- | ------ |
| 1 | file:line | TLS verification | `verify=False` | Enable verification |

### Auth/Authz Gaps

| # | Location | Endpoint | Issue | Action |
| - | -------- | -------- | ----- | ------ |
| 1 | file:line | GET /admin/users | No auth decorator | Add admin auth |

### Sensitive Data Exposure

| # | Location | Data | Channel | Action |
| - | -------- | ---- | ------- | ------ |
| 1 | file:line | Auth token | logging.info() | Remove from logs |

### Unsafe Patterns

| # | Location | Pattern | Risk | Action |
| - | -------- | ------- | ---- | ------ |
| 1 | file:line | `yaml.load(data)` | Arbitrary code execution | Use `yaml.safe_load()` |

### Dependency / Supply-Chain Risks

| # | Location | Issue | Severity | Action |
| - | -------- | ----- | -------- | ------ |
| 1 | requirements.txt | No lockfile committed | High | Commit lockfile |

## Recommendations (Priority Order)

1. **Critical**: {hardcoded secrets to rotate, injection vulnerabilities, pickle on untrusted data, auth bypasses}
2. **Must-fix**: {missing input validation, insecure defaults, auth gaps, dependency CVEs}
3. **Should-fix**: {sensitive data exposure, unsafe patterns, supply-chain hygiene}
```

## Operating Constraints

- **No code edits.** This skill produces an audit report only. Implementation is a separate step.
- **No empty sections.** Include only categories with findings. Omit a heading, table, or list entirely when it would contain zero items — do not include empty tables, placeholder subsections, or negative statements like "no dead exports", "none found", or "no issues".
- **Scope: security vulnerabilities only.** Do not flag type invariants (→ invariant-hunter-py), type design
  (→ type-hunter-py), structural complexity (→ simplicity-hunter-py), module boundary issues (→ boundary-hunter-py),
  class/interface design (→ solid-hunter-py), missing documentation (→ doc-hunter-py), test quality (→ test-hunter-py),
  or cosmetic style (→ slop-hunter-py). If a finding doesn't answer "could this be exploited?", it doesn't belong here.
- **Evidence required.** Every finding must cite `file/path.py:line` with the exact code.
- **Severity matters.** Use Critical / Must-fix / Should-fix. A hardcoded production secret is not the same severity
  as a missing `SameSite` cookie attribute. Prioritize accordingly.
- **Context over pattern-matching.** A `re.compile()` with a hardcoded pattern is fine. A `re.compile(user_input)` is
  a ReDoS risk. Grep finds both — judgment separates them.
- **No false confidence.** This audit catches common patterns, not all vulnerabilities. It is not a substitute for
  professional penetration testing or automated security scanning.
