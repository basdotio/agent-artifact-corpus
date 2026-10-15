# Platform Pack: Backend / API

Loaded when the repo root shows a server framework and no frontend framework: a
Node.js server framework (express, fastify, koa, nestjs) in `package.json`,
`requirements.txt`/`pyproject.toml` with fastapi/django/flask, `go.mod`, a `Gemfile`
with rails/sinatra, `pom.xml`/`build.gradle` with spring-boot, or the presence of an
OpenAPI/Swagger spec file (`openapi.yaml`, `swagger.json`).

This pack is structurally different from the iOS/Android/Web packs: several core
categories don't apply at all here, and `Level test` needs one extra value. Read
both sections below before generating test cases for a backend feature.

## Core categories that do NOT apply here

Don't generate test cases for these on a backend feature - they assume a client UI:

- Background / foreground transition
- Rotation
- Accessibility baseline
- App killed & relaunch (as written - see the reinterpretation below instead)

## Core categories, reinterpreted for backend

| Core category | Backend-specific signal / phrasing |
|---|---|
| Permission denied | Reinterpret as **authorization** (403): the endpoint requires a role or scope the caller doesn't have. Keep this distinct from `Session/auth expiry` (401: caller isn't authenticated at all). |
| App killed & relaunch | Reinterpret as **process restart / deployment**: does in-flight work (a queued job, a multi-step transaction) resume or fail cleanly if the process restarts mid-request? |
| Empty / loading state | Reinterpret as an **empty result set**: does the endpoint return the correct status and shape (e.g. `[]` with 200, not a 404 or a 500) when there's nothing to return? |
| Concurrency | Reinterpret as **concurrent requests to the same resource** from different callers, not a double-tap in a UI. Pair this with the backend-exclusive "database transaction / race condition" category below when the resource is persisted. |
| Large dataset / pagination | Directly applicable: check page-size limits, cursor/offset correctness at boundaries, and behavior when a client requests beyond the last page. |
| Data migration | Directly applicable: schema migrations, and whether old and new API versions can both run against the migrated schema during a rollout. |
| Multi-device / concurrent session | Directly applicable: the same account calling the API from more than one client at once. |

## Backend-exclusive categories

| Category | Trigger condition |
|---|---|
| Rate limiting | Endpoint could plausibly be called at high frequency, by one caller or many |
| Idempotency of retried requests | Endpoint is a POST/PUT/PATCH a client could retry after a timeout without knowing if the first attempt succeeded |
| Request validation / malformed payload | Endpoint accepts a request body or query parameters |
| Database transaction / race condition | Endpoint writes to a resource that more than one request could write to concurrently |
| Webhook delivery & retry | Feature sends a webhook or callback to an external system |
| API versioning / backward compatibility | Endpoint is part of a versioned API contract that existing clients depend on |
| Timeout & retry with downstream dependencies | Endpoint calls another internal or external service |

Mark test cases from this section the same way as core checklist items:
`Source: inferred (checklist: <category name>)`.

## Level test on this platform

Only three of the five core `Level test` values are normally used here:
`unit`, `integration`, and `contract` (new - see below). `ui-single-screen` and
`e2e-multi-screen` don't apply; a backend feature has no screens.

- **`contract`**: the Steps validate a request or response against the API's own
  published schema (OpenAPI/Swagger, a GraphQL schema, or a protobuf definition) -
  distinct from `integration`, which validates behavior, not shape. Use `contract`
  when the point of the test case is "does this match what we promised callers",
  not "does this do the right thing".
