# Code standards

These apply in every language unless the repository's conventions say otherwise. When they conflict, follow the repository and note the difference in the tech-debt list.

## Naming
- Name things for what they are or do: `unpaid_invoices`, not `data2`. Functions are verbs (`calculate_tax`), booleans read as questions (`is_active`, `has_access`).
- Include units: `timeout_seconds`, `price_paise`, `size_bytes`.
- Use the repository's case style and vocabulary. If the code says "customer", do not introduce "client" for the same thing.
- Avoid abbreviations except common ones (id, url, api, db).

## Functions
- One job per function. Treat more than about 40 lines, deep nesting, or more than four parameters as a sign to split or to pass a small parameter object.
- Return early for edge cases instead of nesting the main path.
- No boolean flag parameters that switch between two behaviors; write two functions.
- Keep side effects visible: a function named `get_` should not write.

## Errors
- Never swallow an exception. Catch the specific exception you can handle, and let the rest propagate.
- Add context when re-raising: what was being attempted, with which identifiers (never secrets).
- Define domain error types (`OrderNotFound`, `PaymentDeclined`) and map them to HTTP status codes or UI messages only at the edge.
- No bare `except:` in Python, no empty catch blocks anywhere, and no exceptions for normal control flow.

## Logging
- Structured logs (key-value or JSON) with a request, job, or correlation ID.
- Levels: debug for detail while developing, info for business events, warning for recoverable problems, error for failures that need attention.
- Never log passwords, tokens, API keys, full card or account numbers, or personal data beyond what policy allows.
- Log an error once, where it is handled, not at every layer it passes through.

## Configuration
- Read configuration from environment variables through one typed settings object. No literal URLs, credentials, or environment names in code.
- Defaults must be safe for local development. Production values come from the environment or a secret manager.
- Keep .env.example in sync with every variable the code reads, with dummy values and a comment for each.

## Types
- Python: type hints on every function signature, and mypy or pyright clean for the files you touch.
- TypeScript: strict mode, no `any` without a comment explaining why.
- Kotlin: use null safety properly; no `!!` outside tests.

## Comments and docstrings
- Comments explain why something is done, not what the next line does.
- Public functions, classes, and modules get docstrings in the repository's style.
- No commented-out code; git keeps history. No TODO without an issue link or an owner.

## Magic values and dead code
- Name constants (`MAX_UPLOAD_BYTES = 10 * 1024 * 1024`).
- Remove code your change made unused. Leave other dead code alone and list it in the tech-debt list.

## Concurrency and I/O
- No blocking calls inside async functions. Use async clients, or run blocking work in a thread pool.
- Every network call has a timeout. Retries use exponential backoff with a cap, and only for errors that can succeed on retry.
- Background jobs are idempotent: running one twice must not charge twice or send two emails.
- Take locks only when needed, with a timeout, and release them in finally blocks.

## Performance basics
- Watch for N+1 queries; load related data in one query.
- Paginate list endpoints and bound every query and loop that depends on user data.
- Add an index with every new filter or sort on a large table.
- Cache only with an explicit TTL and a clear invalidation rule, and measure before optimizing anything else.

## Reviewable changes
Readable beats clever. Prefer small, focused changes that a reviewer can understand in one sitting, with tests that show the intended behavior.
