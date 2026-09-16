---
name: security-hunter-go
description: |
  Audit Go code for security vulnerabilities — hardcoded secrets, injection risks (SQL,
  command, template, path), missing input validation at trust boundaries, insecure defaults,
  auth gaps, sensitive data exposure, unsafe package usage, and weak crypto.

  Use when: reviewing Go code before deployment, auditing trust boundaries, preparing for
  a security review, onboarding third-party integrations, or hardening an application.
disable-model-invocation: true
---

# Security Hunter

Audit code for **security vulnerabilities** — places where untrusted input flows into sensitive operations without
validation, secrets are embedded in source, defaults are permissive, or auth checks are missing. The goal: **every
trust boundary validates its inputs, no secrets live in code, and the principle of least privilege is applied
throughout.**

## When to Use

- Reviewing code before production deployment
- Auditing trust boundaries (API endpoints, gRPC handlers, webhooks, CLI input)
- Preparing for a formal security review or pen test
- Onboarding third-party integrations or new external data sources
- Hardening an application after a security incident

## Core Principles

1. **Trust boundaries are the perimeter.** Every point where external data enters the system — HTTP requests, gRPC
   calls, file uploads, environment variables, database reads, third-party API responses — is a trust boundary. Input
   must be validated, sanitized, or escaped before it flows into operations that could be exploited.

2. **Secrets belong in the environment, never in code.** API keys, passwords, tokens, certificates, and connection
   strings must come from environment variables, secret managers, or encrypted config — never from source files,
   comments, or committed config.

3. **Default to deny.** Defaults should be restrictive: CORS origins explicit not `*`, auth required not optional,
   permissions minimal not broad. Permissive defaults are the most common class of security misconfiguration.

4. **Defense in depth.** No single validation layer is sufficient. Validate at the boundary, escape at the output,
   enforce at the data layer. If one layer fails, another should catch the exploit.

5. **Fail closed.** When auth/authz checks fail or return errors, the result should be denial, not access. Error paths
   must not bypass security controls.

## What to Hunt

### 1. Hardcoded Secrets

API keys, passwords, tokens, or connection strings embedded directly in source code.

**Signals:**

- String literals matching key patterns: `sk_live_`, `AKIA`, `ghp_`, `Bearer `, `password=`
- Connection strings with embedded credentials: `postgres://user:pass@host`
- Base64-encoded strings in auth headers or config
- `.env` files or secret-bearing config committed to the repo
- Comments containing credentials ("temporary key: xyz123")
- `const` or `var` declarations with secret-looking values

**Action:** Move to environment variables or a secret manager. Add the pattern to `.gitignore`. Rotate any committed
secret immediately — it's already compromised if the repo was ever shared.

### 2. Injection Vulnerabilities

Untrusted input concatenated into strings that are interpreted as code, queries, or commands.

**Signals:**

- SQL: string concatenation or `fmt.Sprintf` in query strings instead of parameterized queries (`db.Query(sql, args...)`)
- Command injection: `exec.Command` with user-controlled arguments, especially via shell (`sh -c`)
- Path traversal: user input in `os.Open()`, `filepath.Join()`, or URL construction without canonicalization
- Template injection: user input rendered via `text/template` in a web/HTML context (no auto-escaping) instead of
  `html/template`. Note: `text/template` is fine for non-HTML output (config files, CLI output, code generation)
- LDAP injection: user input in LDAP filter strings
- Header injection: user input in HTTP response headers without sanitization
- Regex: user input passed directly to `regexp.Compile` (ReDoS risk)

**Action:** Use parameterized queries, allowlists, `filepath.Clean` + prefix checking, `html/template`, or regex
escaping. Never concatenate untrusted input into interpreted strings.

### 3. Missing Input Validation at Trust Boundaries

Endpoints, handlers, or integration points that accept external data without validation.

**Signals:**

- HTTP handlers that read `r.Body`, `r.URL.Query()`, or `r.FormValue()` without validation
- gRPC handlers that use request fields without validation
- File upload handlers without type/size/content validation
- Webhook handlers without signature verification (HMAC)
- CLI commands that use `os.Args` or flag values without validation
- JSON unmarshalling without struct tag validation or post-unmarshal checks

**Action:** Add validation at every trust boundary. Validate type, format, range, and length. Reject invalid input
explicitly — don't coerce or default.

### 4. Insecure Defaults and Configuration

Permissive defaults that weaken security posture when not explicitly overridden.

**Signals:**

- CORS: `Access-Control-Allow-Origin: *` or credentials with wildcard origin
- TLS: `InsecureSkipVerify: true` in `tls.Config`
- TLS: minimum version not set explicitly. Go's defaults changed over time and differ by role: the **client**
  minimum rose to TLS 1.2 in Go 1.18, but the **server** minimum stayed TLS 1.0 until **Go 1.22**. The *effective*
  default is layered: the build toolchain's defaults, amended to the `go` directive in `go.mod`, then overridden by
  `//go:debug` directives and finally the `GODEBUG` environment (the `tls10server` setting is removed in Go 1.27).
  For compliance-sensitive servers, recommend an **explicit `MinVersion`** outright — simpler and more robust than
  reasoning about four layered defaults (trade-off, stated: an explicit pin opts out of future automatic increases
  to Go's default minimum and must be maintained deliberately). When assessing the effective default instead,
  inspect all four layers
- HTTP server without timeouts (`ReadTimeout`, `WriteTimeout`, `IdleTimeout`)
- Cookie: missing `Secure`, `HttpOnly`, or `SameSite` attributes
- Rate limiting absent on auth endpoints or public APIs
- Debug endpoints or pprof exposed in production
- Permissive file permissions (`os.WriteFile` with `0666` or `0777`)

**Action:** Restrict defaults. Require explicit opt-in for permissive settings with justification.

### 5. Authentication and Authorization Gaps

Missing or inconsistent auth checks that allow unauthorized access or privilege escalation.

**Signals:**

- Routes/endpoints without auth middleware where peer routes have it
- Authorization checks that compare user IDs with string equality on user-controlled values
- Role checks using client-provided claims without server-side verification
- Admin functionality accessible by changing a URL parameter or request body field
- JWT validation without audience, issuer, or expiry checks
- Password handling: plain-text storage, weak hashing (MD5, SHA1), missing salting
- Session tokens without expiry, rotation, or revocation

**Action:** Ensure every endpoint has explicit auth/authz. Check authorization server-side against the session, not
client-provided claims. Use bcrypt/scrypt/argon2 for password hashing.

### 6. Sensitive Data Exposure

Personal data, secrets, or internal details leaked through logs, errors, responses, or storage.

**Signals:**

- Logging request bodies, auth headers, or user PII (`log.Printf("%+v", request)`)
- Error responses that include stack traces, internal paths, or database details
- API responses that return more fields than the client needs (no field filtering)
- Sensitive data in URLs (tokens in query parameters — logged by servers and proxies)
- Errors wrapped with `fmt.Errorf` that include sensitive context sent to clients
- `panic` stack traces exposed to clients in production

**Action:** Strip sensitive fields from logs and error responses. Use separate internal/external error messages. Recover
panics in HTTP middleware and return generic errors.

### 7. Unsafe Package and CGO Risks

Usage of `unsafe`, `reflect`, or CGO that bypasses Go's type safety and memory safety.

**Signals:**

- `import "unsafe"` outside of performance-critical, well-audited code
- `reflect` used to bypass unexported field access
- CGO code without input validation at the Go/C boundary
- `//go:linkname` directives accessing internal runtime functions
- `//go:nosplit`, `//go:noescape` pragmas without justification
- `unsafe.Pointer` arithmetic for memory manipulation

**Action:** Audit each usage. Ensure unsafe code is isolated, documented, and justified. Verify CGO boundaries validate
all inputs. Prefer pure Go alternatives where possible.

### 8. Exploitable Concurrency

Concurrency defects **framed by exploitability** — reachable or triggerable by an external actor. General data-race
and synchronization *correctness* is owned by invariant-hunter-go §8; do not duplicate it here.

**Signals:**

- Unbounded goroutine creation from user input (goroutine bomb / DoS)
- Deadlocks reachable from external requests (a client can wedge the server)
- TOCTOU-style check/act races on auth or permission decisions
- Resource exhaustion via concurrent request amplification (fan-out per request without bounds)

**Action:** Bound goroutine creation (worker pools, semaphores). Make auth check-and-act atomic. Route plain
race-condition findings to invariant-hunter-go.

### 9. Dependency and Supply-Chain Risks

Module dependencies with known vulnerabilities or integrity issues.

**Signals:**

- `go.sum` not committed when the module has dependencies requiring checksums (a module with no such
  requirements legitimately has no `go.sum` — check before flagging)
- Dependencies with known CVEs — run `govulncheck` when available; it is the canonical detector here
- `replace` directives in `go.mod` pointing to local paths in production
- Using deprecated or unmaintained modules for security-sensitive operations
- Checksum-database trust model weakened: `GOSUMDB=off` (global verification disable), or `GOPRIVATE` /
  `GONOPROXY` / `GONOSUMDB` patterns broader than the organization's actual private namespaces. Note the
  calibration: private modules bypassing the public checksum database via `GOPRIVATE`/`GONOSUMDB` is the
  *expected* configuration, not inherently suspicious — flag the mismatches, not the mechanism

**Action:** Commit `go.sum` (when checksums are required). Run `govulncheck`. Pin dependency versions. Audit
transitive dependencies for security-sensitive code paths. Note: exclusion globs do not apply to this category —
`govulncheck` and `go.sum` auditing operate module-wide by construction.

## Audit Workflow

### Phase 1: Map Trust Boundaries

1. **Resolve audit surface.** The prompt may specify the scope as:
   - **Diff**: files changed relative to the base branch — committed, staged, unstaged, and untracked
   - **Path**: specific files, folders, or packages
   - **Codebase**: the entire project (the default when unspecified; set `SCOPE=.`)

   **Party mode:** when the orchestrator supplies a scope snapshot (a resolved file list), use it verbatim and do
   not re-resolve. The resolution below applies to standalone runs only.

   For diff mode, resolve fail-closed:
   ```bash
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@')
   if [ -z "$BASE" ]; then
     for b in origin/main origin/master main master; do
       git rev-parse -q --verify "$b" >/dev/null && BASE=$b && break
     done
   fi
   # If BASE is still empty: STOP. Ask for an explicit base. Do not continue.

   SCOPE=$( { git diff --name-only --diff-filter=d "$BASE"...HEAD;
              git diff --name-only --diff-filter=d HEAD;
              git ls-files --others --exclude-standard; } | sort -u )
   DELETED=$( { git diff --name-only --diff-filter=D "$BASE"...HEAD;
                git diff --name-only --diff-filter=D HEAD; } | sort -u )
   ```
   If `$SCOPE` is empty, run no scans: write the report with "Audit completed: 0 findings — empty diff scope",
   listing `$DELETED` under "Deleted in diff" if non-empty, and stop. If the resolved surface exceeds what can be
   read within the context budget, report the file count and ask to narrow or chunk.

   **Two surfaces.** Findings are reported only against the **target scope** (`$SCOPE`) — every finding anchors
   (file:line) there. Related files may still be *read* as **context**: tracing a data flow from a handler to a
   query often crosses files outside the scope. Exception: dependency analysis (§9) is module-wide by
   construction regardless of scope.
2. Identify trust boundaries: HTTP handlers, gRPC services, webhook endpoints, CLI argument parsers, config loaders.
3. Identify auth/authz middleware and where it's applied.

### Phase 2: Scan for Security Signals

**Toolchain first — prefer the repository's existing invocation.** If the project has a configured security
scanner (`gosec` — a widely used third-party scanner covering much of the grep list below with taint awareness —
`golangci-lint` with security linters, or a CI security step), run that and triage its output. Note `gosec` skips
`*_test.go` by default and needs `-tests` to cover them — running gosec does not by itself cover test files. Run
`govulncheck` for §9 when available. Never install or reconfigure tools for the audit; if a tool is unavailable,
record "skipped/unavailable" in the report and rely on the scans below. If a relevant tool is absent from the
project, recommend enabling it *in the report*.

**Exclusion profiles are per scan class, not global:**

```bash
# Secret detection: vendor-only. Tests, testdata, generated output, config, and documentation all stay
# in scope — a committed credential is compromised regardless of which file class carries it.
# (Accepted residual risk: credentials inside vendored content belong to dependency/upstream scanning.)
EXCLUDE_SECRETS='--glob !**/vendor/**'

# Code scans: exclude vendor, testdata, and generated code (authoritative marker: a
# "// Code generated .* DO NOT EDIT." line before the first non-comment text; globs approximate).
EXCLUDE='--glob !**/vendor/** --glob !**/testdata/** --glob !**/*_test.go --glob !**/*.pb.go --glob !**/*_gen.go --glob !**/*_generated.go'
```

Run every scan against the target scope (`SCOPE=.` in codebase mode):

```bash
# Hardcoded secrets (common patterns) — deliberately not restricted to Go files
rg --pcre2 '(sk_live_|AKIA|ghp_|password\s*=\s*"|secret\s*=\s*")' $EXCLUDE_SECRETS -- $SCOPE
rg --pcre2 '(postgres|mysql|mongodb)://\w+:\w+@' $EXCLUDE_SECRETS -- $SCOPE

# SQL injection: string formatting in queries
rg --pcre2 '(Query|Exec|QueryRow)\s*\(\s*(fmt\.Sprintf|".*\+|`.*\+)' --type go $EXCLUDE -- $SCOPE
rg 'fmt\.Sprintf.*SELECT|fmt\.Sprintf.*INSERT|fmt\.Sprintf.*UPDATE|fmt\.Sprintf.*DELETE' --type go $EXCLUDE -- $SCOPE

# Command injection
rg 'exec\.Command\s*\(' --type go $EXCLUDE -- $SCOPE
rg 'os/exec' --type go $EXCLUDE -- $SCOPE

# Path traversal
rg '(os\.Open|os\.ReadFile|os\.Create|ioutil\.ReadFile)' --type go $EXCLUDE -- $SCOPE

# Template injection (text/template used in web/HTML context — triage: check if output is served to browsers)
rg '"text/template"' --type go $EXCLUDE -- $SCOPE

# Insecure TLS
rg 'InsecureSkipVerify\s*:\s*true' --type go $EXCLUDE -- $SCOPE

# Unsafe package
rg '"unsafe"' --type go $EXCLUDE -- $SCOPE
rg 'go:linkname' --type go $EXCLUDE -- $SCOPE

# Weak crypto — context matters for both scans: math/rand is only a concern in security-sensitive
# contexts (token generation), and MD5/SHA1 are legitimate for non-security checksums (git objects,
# dedup keys, ETags); flag only cryptographic use (passwords, signatures, certificates)
rg '"crypto/md5"|"crypto/sha1"' --type go $EXCLUDE -- $SCOPE
rg '"math/rand"' --type go $EXCLUDE -- $SCOPE

# Missing HTTP timeouts
rg 'http\.ListenAndServe|&http\.Server\{' --type go $EXCLUDE -- $SCOPE

# Sensitive data in logs
rg --pcre2 'log\.\w+\(.*\b(password|token|secret|authorization|cookie)\b' -i --type go $EXCLUDE -- $SCOPE

# File permissions
rg '0666|0777|os\.ModePerm' --type go $EXCLUDE -- $SCOPE

# pprof in non-debug code
rg 'net/http/pprof|runtime/pprof' --type go $EXCLUDE -- $SCOPE

# Regex from user input
rg 'regexp\.(Compile|MustCompile)' --type go $EXCLUDE -- $SCOPE

# Unbounded goroutines from user input
rg 'go\s+func|go\s+\w+\(' --type go $EXCLUDE -- $SCOPE
```

### Phase 3: Trace Data Flows

For each trust boundary found in Phase 1:

1. Does untrusted input pass through validation before reaching sensitive operations?
2. Are query parameters, body fields, and headers validated for type, format, and range?
3. Could a malicious input reach `exec.Command`, a SQL query, or template rendering?

### Phase 4: Evaluate Auth Coverage

1. List all routes/endpoints. For each: is auth middleware applied?
2. Identify authorization logic. Is it server-side? Does it rely on client claims?
3. Check session/token management: expiry, rotation, revocation.

### Phase 5: Produce Report

## Output Format

Save as `YYYY-MM-DD-security-hunter-audit-{model-name}.md` — `{model-name}` is the executing model's short name
(e.g. `fable-5`) — in the project's docs folder (or project root if no docs folder exists). If the caller specifies
an output path or return mode (e.g. the party-hunter orchestrator), it overrides this default.

Severity levels, used for per-finding labels and the Recommendations grouping:

- **Critical** — exploitable now, causes data loss, or breaks behavior on production paths.
- **High** — a defect with likely user-visible, security, or reliability impact if left unaddressed.
- **Medium** — correctness or maintainability risk without imminent impact.
- **Low** — hygiene; no behavioral risk.

```md
# Security Hunter Audit — {date}

## Scope

- Surface: {diff / path / codebase}
- Files: {count or list}
- Exclusions: {list}
- {Deleted in diff: {list} — only for diff scope with deletions}
- Audit completed: {N} findings
- Tooling: {gosec / govulncheck / golangci-lint — run, or skipped/unavailable}

## Trust Boundary Map

| # | Boundary | Location | Validation | Auth |
| - | -------- | -------- | ---------- | ---- |
| 1 | POST /api/users | file:line | Struct validation | JWT middleware |
| 2 | Webhook /hooks/stripe | file:line | None | None |

## Findings

### Hardcoded Secrets

| # | Location | Pattern | Severity | Action |
| - | -------- | ------- | -------- | ------ |
| 1 | file:line | `sk_live_...` Stripe key | Critical | Move to env, rotate immediately |

### Injection Risks

| # | Location | Type | Untrusted Input | Action |
| - | -------- | ---- | --------------- | ------ |
| 1 | file:line | SQL injection | `r.URL.Query().Get("id")` in fmt.Sprintf | Use parameterized query |

### Missing Input Validation

| # | Location | Boundary | Input | Action |
| - | -------- | -------- | ----- | ------ |
| 1 | file:line | POST /api/orders | `json.Decode` without validation | Add struct validation |

### Insecure Defaults

| # | Location | Setting | Current | Action |
| - | -------- | ------- | ------- | ------ |
| 1 | file:line | TLS verification | `InsecureSkipVerify: true` | Remove or justify |

### Auth/Authz Gaps

| # | Location | Endpoint | Issue | Action |
| - | -------- | -------- | ----- | ------ |
| 1 | file:line | GET /admin/users | No auth middleware | Add admin auth |

### Sensitive Data Exposure

| # | Location | Data | Channel | Action |
| - | -------- | ---- | ------- | ------ |
| 1 | file:line | Auth token | log.Printf | Remove from logs |

### Unsafe/CGO Risks

| # | Location | Pattern | Risk | Action |
| - | -------- | ------- | ---- | ------ |
| 1 | file:line | `unsafe.Pointer` arithmetic | Memory corruption | Audit and document |

### Exploitable Concurrency

| # | Location | Pattern | Risk | Action |
| - | -------- | ------- | ---- | ------ |
| 1 | file:line | Per-request goroutine fan-out without bounds | DoS | Add worker pool / semaphore |

### Dependency / Supply-Chain Risks

| # | Location | Issue | Severity | Action |
| - | -------- | ----- | -------- | ------ |
| 1 | go.mod | No go.sum committed | High | Commit go.sum |

## Recommendations (Priority Order)

1. **Critical**: {hardcoded secrets to rotate, injection vulnerabilities, auth bypasses}
2. **High**: {missing input validation, insecure defaults, auth gaps, dependency CVEs}
3. **Medium**: {sensitive data exposure, unsafe usage, exploitable concurrency}
4. **Low**: {supply-chain hygiene, missing cookie attributes on non-sensitive cookies}
```

## Operating Constraints

- **No code edits.** This skill produces an audit report only. Implementation is a separate step.
- **No empty finding sections.** Include only categories with findings. Omit a heading, table, or list entirely when it would contain zero items — do not include empty tables, placeholder subsections, or negative statements like "no dead exports", "none found", or "no issues". Execution status is exempt: the "Audit completed: N findings" line in the Scope section is always present, even at zero findings.
- **Scope: security vulnerabilities only.** If a finding doesn't answer "could this be exploited?", it belongs to
  another hunter — do not flag it here. Named boundary: general data-race and synchronization correctness belongs
  to invariant-hunter-go; this skill keeps only exploitability-framed concurrency (§8).
- **Evidence required.** Every finding must cite `file/path.go:line` with the exact code.
- **Severity matters.** A hardcoded production secret is not the same severity as a missing `SameSite` cookie
  attribute. Use the four levels defined in Output Format and prioritize accordingly.
- **Context over pattern-matching.** `regexp.MustCompile` with a hardcoded pattern is fine. `regexp.Compile(userInput)`
  is a ReDoS risk. Grep finds both — judgment separates them.
- **No false confidence.** This audit catches common patterns, not all vulnerabilities. It is not a substitute for
  professional penetration testing or automated security scanning.
