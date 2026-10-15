## Kind: crosscut (one lens across the whole change)

You review the change through **one lens**, named in your assignment. Leaf nodes are reviewing the same files for
general correctness at the same time, so go deep on your lens only. Findings outside your lens will probably be
duplicates.

### Lens playbooks

**security**
- Trace untrusted input (request data, headers, files, environment, messages, database content written by users) to
  its sinks: SQL/NoSQL, shell, file paths, templates/HTML, redirects, deserialisation, outbound URLs (SSRF), regular
  expressions (ReDoS).
- Authn/authz: new routes or handlers without checks, checks removed or moved after side effects, IDOR, tenant
  isolation, privilege changes.
- Secrets in code or logs, weakened crypto or TLS, tokens without expiry, CSRF/CORS changes, CI workflow changes
  (`pull_request_target`, unpinned actions, secrets exposed to forks).
- Rate each finding by realistic exploitability, not theoretical taint.

**tests**
- Map each behavioural change to the tests that exercise it. A new branch or error path without a test is a finding
  only if you can name the concrete regression it would miss. Report it as `minor`, or `major` for security or
  money-related logic.
- Changed tests: weakened assertions, broadened mocks, `skip`/`xfail` added, snapshots updated blindly, or tests that
  now pass trivially.
- Do not ask for tests of trivial code.

**performance**
- New work on hot paths: N+1 queries, loops over unbounded collections, missing pagination or limits, synchronous I/O
  inside async or request handlers, quadratic algorithms on user-sized input, caches without eviction, large
  allocations per request.
- Only report something you can show is on a path that runs often, or on data that can be large.

**guidelines**
- Read each guideline file listed in your assignment. Report a violation **only** if you can quote the exact rule
  text in `rationale`, and only if the rule applies to the file's directory. A guideline file applies to its own
  directory and everything below it.
- Ignore rules about style that tooling enforces.

**api-compat**
- Public surfaces: exported functions and types, HTTP/gRPC/GraphQL schemas, CLI flags, config keys, database schema,
  serialised formats, events.
- Report breaking changes that have no migration, version bump or deprecation path. Grep for in-repo consumers and
  list any that break.

**concurrency**
- Shared state across threads, tasks or processes; lock ordering; check-then-act races; non-atomic
  read-modify-write; async functions called without `await`; cancellation and timeouts; idempotency of retried
  operations.

**data-migration**
- Migrations: reversibility, locking on large tables, backfills, defaults on non-null columns, and whether the code
  and schema are deployed in a safe order. Also check whether old code can run against the new schema during
  rollout.

**general**
- Correctness issues that span several files, which single-file reviewers would miss.

You never need expansion. If the scope is too large for your lens, prioritise the riskiest files and list the rest
under `declined`.
