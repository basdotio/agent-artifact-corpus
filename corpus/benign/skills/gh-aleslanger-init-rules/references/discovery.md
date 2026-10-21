# Discovery reference (Phases B–D)

Read during Phases B–D. Label every finding VERIFIED / INFERRED / UNKNOWN.

## Phase B: what to establish

- **Structure:** apps, packages, libraries, modules, services, infrastructure, tests, generated output, docs.
- **Tooling:** languages, frameworks, build tooling, package manager (lockfile is evidence), build/test/lint/format/typecheck/static-analysis tools.
- **Versions:** the language/runtime version and the supported range, from:
  - version files: `.python-version`, `.nvmrc`/`.node-version`, `.tool-versions`, `mise.toml`, `rust-toolchain.toml`;
  - manifest fields: `requires-python`, `engines`, the `go` directive in `go.mod`, `edition`/`rust-version`, `composer.json` `php`, Gradle/Maven toolchain or `release`;
  - TS `target`/`lib`, Dockerfile base images, the CI matrix;
  - for frameworks and key libraries, the **locked** versions from the lockfile (not the manifest range).

  Derive the **minimum** version code must run on. When the CI matrix covers several versions, the lowest one counts. Surface conflicts between sources (e.g. `.python-version` 3.12 but `requires-python >=3.10`).
- **Deprecation tooling:** what already flags deprecated or outdated usage, with its command. Examples: ruff `UP` (pyupgrade) and its `target-version`, pyright/mypy deprecation reporting, `-W error::DeprecationWarning` in pytest config, eslint deprecation rules, TS `@deprecated` diagnostics, staticcheck `SA1019`, `go vet`, rustc/clippy deprecation lints, `-Xlint:deprecation`/`-Werror`, PHPStan deprecation rules. Also record where deprecation warnings show up (test and build output).
- **Architecture:** entry points, module/package boundaries, public interfaces, APIs, persistence, workers/queues, external integrations. Look for explicit architecture evidence:
  - ADRs and `docs/architecture*`;
  - dependency-rule tooling: import-linter, dependency-cruiser, eslint boundary/import rules, ArchUnit, Nx/Turborepo project constraints, Bazel/Gradle module visibility, Go `internal/`, TS project references or path aliases;
  - layering visible in the code (e.g. routes → services → repositories), and where it is violated;
  - the dependency direction between packages, and what is public versus internal per package.

  Record which rules are **enforced by tooling** (cite the config) versus **convention only** (cite 2–3 exemplars).
- **Performance:** look for explicit performance evidence before writing any performance rule:
  - benchmarks (pytest-benchmark, Go `Benchmark*`, criterion, JMH, vitest/jest bench);
  - load tests (k6, Locust, Gatling, JMeter);
  - budgets and thresholds (size-limit, bundlesize, Lighthouse CI budgets, perf assertions in tests);
  - SLO/latency targets in docs;
  - documented hot paths;
  - caching layers and their invalidation;
  - query patterns (eager loading, batching, pagination limits, indexes in migrations);
  - timeouts and pool sizes in config;
  - profiling or perf CI jobs.

  Note which evidence is executable (has a command) and which is documented only.
- **Code quality conventions:**
  - **Linting and types:** the enabled rule sets and severity (not just the linter's presence), type strictness, and suppression conventions (`noqa`, `eslint-disable`, `@ts-expect-error`, `#[allow]`) and how often they're used.
  - **Thresholds:** complexity and length limits, coverage thresholds.
  - **Errors and logging:** error-handling conventions (custom error types, result types, error wrapping, where errors get translated at boundaries) and the logging conventions.
  - **Tests:** test conventions (layout, fixtures, factories, mocking style, naming).
  - **Contribution process:** PR templates, CODEOWNERS, review checklists, `.editorconfig`.
  - **Coding standard:** the standard the repo actually adopts, and where it's enforced. Examples: PEP 8 via ruff/black/flake8, PSR-12 via phpcs, gofmt/golangci-lint, rustfmt/clippy, an eslint shared config (airbnb, standard), Google Java Style via checkstyle/spotless. Also look for style sections in `CONTRIBUTING*`, `STYLEGUIDE*`, or `docs/*standards*`.
  - **Conventions:** naming (file and directory case, test file names, identifiers, modules), import ordering, and module layout. Each must be confirmed by linter config or at least 3 consistent examples. Commit/PR conventions only when enforced (commitlint, conventional commits, changelog tooling).
  - **Reuse and duplication:** where the shared helpers, utils, types, constants, validators, and query helpers live (name the paths). Also any duplication tooling (jscpd, PMD CPD, pylint `duplicate-code`, Sonar) and its threshold.
  - **Exemplars:** 1–3 files that best represent "how code is written here" for each major kind of change (endpoint, service, component, migration, test).
- **Documentation:**
  - **Inventory:** READMEs (root and per package), `docs/`, `.env.example`, and where the commands, config/env vars, CLI flags, and public APIs are documented.
  - **Code-level docs:** docstring/JSDoc/rustdoc/godoc conventions and their linting (pydocstyle/ruff `D`, eslint-plugin-jsdoc, `missing_docs`).
  - **Changelog:** keep-a-changelog, changesets, release-please, or towncrier, and whether an entry is required per change.
  - **Doc tooling:** build tooling (MkDocs, Sphinx, Docusaurus, TypeDoc), link checks, doctests or tested examples, with their commands.
  - **Generated docs:** which docs are generated (OpenAPI, API reference) and from what.
  - **Drift:** existing doc drift, i.e. docs that contradict the code, including commands or paths in the README that don't exist.
- **Data:** persistence model, schemas, migrations (and their tool), transaction boundaries, generated models, source-of-truth files.
- **Security:** input validation, authentication, authorization, secret handling, env configuration, trust boundaries, sensitive data. Treat **authentication and authorization separately**; authentication never implies authorization.
- **Operations:** CI, deployment, releases, versioning, logging, monitoring, error handling, runtime config.

**Evidence hierarchy** when sources conflict (strongest first):
1. executable configuration
2. CI configuration
3. build/package manifests
4. test/static-analysis configuration
5. source code
6. architecture docs
7. contributor docs
8. README
9. repeated repository convention
10. inference

Surface material conflicts in the report; do not silently resolve them.

## Phase C and D details

### Phase C: Canonical commands

Discover the repository-supported command for each task that applies: bootstrap/install, build, focused test (single file/test), broader test, lint, format, typecheck, static analysis, dev runtime, code generation.

- Prefer commands CI runs or repository scripts define (`package.json` scripts, `Makefile`, `justfile`, `Taskfile`, `pyproject` tool config, `tox`/`nox`, `Cargo`, `go`, etc.).
- Confirm each command exists: the script/target is defined, and the tool is a declared dependency or used by CI.
- You MAY run cheap, read-only, side-effect-free commands to verify (e.g. `--help`, `--version`, listing targets, a dry run). Do NOT run installs, builds, migrations, deploys, or anything that mutates state, network resources, or databases without asking.
- Never put an unverified command in CLAUDE.md. If the focused-test syntax can't be established, say UNKNOWN rather than guessing.

### Phase D: Risk analysis

Evaluate only risks actually relevant to this repo, with evidence:

- **Correctness:** regressions, stale callers, API contract changes, compatibility, error handling, partial state.
- **Inputs/injection:** validation, normalization, malformed input, SQL/query injection, shell/command injection, path traversal, unsafe deserialization, other trust boundaries.
- **AuthN / AuthZ (separately):** where identity is established; where permissions are enforced; ownership/resource-level checks; privilege boundaries.
- **Data integrity:** migrations, destructive ops, transactions, partial writes, retry safety, duplicate processing, idempotency.
- **Concurrency:** races, atomicity, locking, check-then-act, ordering assumptions, concurrent updates.
- **Performance (only where relevant):** Big-O, hot loops, N+1 access, repeated I/O or network calls, blocking work, memory-heavy ops, unbounded collections. Do not invent performance requirements. Turn found budgets, benchmarks, and SLOs into rules; without such evidence, limit performance rules to the verified hot paths and data-access layers.
- **Architecture erosion:** boundary violations that already exist, circular dependencies, god modules, and layers the code bypasses. Rules must say how to treat existing violations: don't copy them, don't fix them unasked.
- **Reliability:** dependency failures, timeouts, retries, cleanup, partial availability, resource leaks.
- **Observability:** meaningful logging, sensitive-data leakage in logs, the monitoring/tracing the project already uses, useful error context. Do not impose a stack the project doesn't use.
- **Generated files:** identify generated artifacts and their source of truth and generator command (see the generated-files rule in `rule-catalog.md`).
- **Secrets:** where secrets enter (env files, secret managers, CI secrets). Never read out, copy, or quote secret values; note only the mechanism and file paths.
