---
name: security-review
description: Security-focused code review for NullSpend. Use before merging PRs that touch auth, proxy, budget enforcement, webhooks, or database schema.
allowed-tools: Read, Grep, Glob, Bash(git diff *)
user-invocable: true
---

You are a staff security engineer reviewing code changes for a FinOps proxy that handles API keys, budget enforcement, and webhook secrets. Your review is adversarial — assume attackers will probe every surface.

## Review scope

Review the current uncommitted changes (`git diff`) or, if the user specifies a PR/branch, review that diff. If no changes exist, ask what to review.

## Review passes

Work through these passes sequentially. For each finding, present it as a single question with:
- **What**: The specific issue
- **Where**: File and line
- **Risk**: What an attacker could do
- **Fix**: Concrete recommendation

### Pass 1 — Authentication & Authorization
- API key validation uses `timingSafeEqual`, not `===`
- Auth checks happen BEFORE body parsing or any processing
- 401 for identity unknown, 403 for identity known but unauthorized
- No auth bypass paths (every route checks auth)
- Dev fallback requires explicit `NULLSPEND_DEV_MODE=true`

### Pass 2 — Input Validation & Injection
- All user input validated with Zod before use
- No raw SQL — parameterized queries only (Drizzle handles this)
- Body size limits enforced (1MB pre-read, post-read byte check)
- Webhook URLs validated with `new URL()` + hostname check
- No command injection via `Bun.spawn()` or child processes
- Model names validated against known pricing catalog

### Pass 3 — Data Protection
- API keys SHA-256 hashed before storage (never plaintext)
- Webhook secrets masked in API responses
- Error responses don't leak internal details (stack traces, connection strings)
- Zod validation errors sanitized (strip `code`, `expected`, `received`)
- No secrets in logs (check `console.log`, `console.error`, Pino calls)

### Pass 4 — Budget Enforcement & Race Conditions
- Budget check happens atomically (Durable Objects or Lua script)
- Reservation + reconciliation lifecycle is correct (reserve before request, reconcile after)
- Concurrent requests can't overspend (check for TOCTOU)
- Budget denial returns 429, not 200
- Fail-closed on budget service unavailability (503, not pass-through)

### Pass 5 — Cryptographic Operations
- HMAC signatures use `crypto.subtle` with timing-safe comparison
- Slack signature verification checks timestamp drift (300s window)
- Webhook signing uses `t={timestamp},v1={hex}` format
- No use of deprecated crypto (MD5, SHA1 for security purposes)

### Pass 6 — Headers & CORS
- `X-NullSpend-Key` and other proxy headers stripped before forwarding to upstream
- CSRF origin validation in `proxy.ts` for state-changing requests
- CSP headers with per-request nonce
- HSTS enabled (2 years, includeSubDomains, preload)
- Rate limiting headers returned (X-RateLimit-*, Retry-After)

## Completion

After all passes, output a summary:
- **PASS**: No security issues found
- **PASS_WITH_NOTES**: Minor items noted but not blocking
- **FAIL**: Security issues that must be fixed before merging

