---
name: "flask-development"
description: "Guardrails for building, changing, fixing or reviewing Flask applications - application factory, thin Blueprints, service layer, Jinja + HTMX + Tailwind, security, tests and minimal diffs. Use whenever the work touches Flask code, routes, Blueprints, Jinja templates, HTMX partials, services or models of a Flask app, or a review of such code, even if Flask is not named explicitly."
---

# Flask development

Work the way a senior Flask engineer works in a production codebase that other people maintain: understand first, change little, and say plainly what you traded off.

Where the repository already does something differently, the repository wins: consistency with what exists is worth more than a textbook pattern. For a new application, the structure below is the starting point.

## Working method

1. **Read before writing.** Find out how the current code handles the thing you are about to touch: which Blueprint, which service, which template, which naming.
2. **Propose the smallest effective change.** A focused patch is reviewable and reversible; a rewrite is neither. No speculative refactors, no abstraction the task does not need.
3. **Name tradeoffs, assumptions and risks.** Flag uncertainty instead of guessing.
4. **Give one strong recommendation** rather than a menu of alternatives.

Code you hand over is ready to paste into the repository: imports included, real code rather than pseudo-code or placeholders, type hints on new or changed Python, and backwards compatible with public interfaces preserved unless a breaking change was requested.

## Architecture

```
app/
  blueprints/       HTTP endpoints, kept thin
    <blueprint>/    one package per feature
  models/           persistence
  service/          business logic
  cli/              command line commands
  utils/            generic, domain-free helpers
  static/
  templates/        shared base template
    <blueprint>/    one subfolder per Blueprint
migrations/         database migrations
workers/            background jobs, only once Celery is approved
tests/
docs/
```

- Use the application factory pattern. Organize features into Blueprints and register them in the factory.
- Initialize extensions with `ext.init_app(app)` inside the factory, not at module level.
- Keep configuration in `config.py` with classes such as `DevelopmentConfig` and `ProductionConfig`. Read values from `.env` and validate their format and value on load, so a bad setting fails at startup instead of in the middle of a request.

| Concern | Belongs in | Does not belong in |
|---|---|---|
| Request parsing, status codes, redirects, choosing the template | Route function | Services |
| Business rules and decisions | Service modules | Routes, templates, utils |
| Database access, queries, transactions | Models, repositories or data-access helpers | Templates, routes, utils |
| Presentation | Jinja templates, macros, partials | Services |
| Command line entry points | `app/cli/` | Services, utils |
| Background job entry points | `workers/` | Services, utils |
| Generic, domain-free helpers | `utils/` | - |

Routes, CLI commands and workers are all entry points: they parse their input, call a service and report the result. That keeps services free of HTTP and reusable from all three, and testable without a request context.

- Avoid circular imports and hidden coupling between Blueprints. If one Blueprint needs another's behaviour, that behaviour belongs in a service both can call.
- Once a helper knows about the domain it is a service; leaving it in `utils/` turns that folder into a dumping ground.
- Prefer localized refactors and do not introduce a new architectural style unless requested. If a larger refactor is really needed, explain why the current design is insufficient and propose an incremental path.

## Services and data

- One responsibility per service, explicit inputs and outputs, no hidden side effects, no dependency on `request` or `session`.
- Make transactions explicit, so it is visible where a unit of work begins and ends.
- Keep each mapping or normalization in one deterministic function. The same transformation scattered across a route, a template and a service will drift apart.
- No mutable global state and no important behaviour in import-time side effects. Both break under multiple workers and make tests order-dependent.

## UI and templates

Server-rendered Jinja, HTMX for partial updates, Tailwind CSS for styling, and as little JavaScript as the job needs. No SPA patterns or heavy frontend frameworks: the server already holds the state, and a second copy on the client is a second source of bugs.

- Extend the shared base template and respect its existing blocks, such as `header` and `content`.
- Domain decisions stay out of Jinja. The service or route decides and passes the result in, so an `{% if %}` displays a decision rather than making one.
- Use macros or partials for repeated UI patterns.
- **HTMX:** use it for inline updates, form submissions and partial refreshes. Endpoints return only the HTML snippet that is needed, validate on the server before processing, and stay small. No client-side state where server-rendered state is sufficient.
- **Styling:** follow Tailwind v4 conventions and take components from Flowbite or DaisyUI instead of hand-building them. In an existing project, use the library and patterns already in place.
- Keep semantic HTML and proper labels on forms, buttons and navigation.

## Security

- Respect authentication and authorization boundaries. Prefer an explicit permission check over an implicit assumption such as "this route is only linked from the admin page".
- Preserve CSRF protection, including on HTMX requests.
- Rely on Jinja autoescaping. Avoid `|safe` and `Markup` unless explicitly required.
- Take care with redirects (open redirects), file handling (paths, uploads) and serialization.
- No secrets, tokens or credentials in code; use environment variables or the project's secret management.
- No secrets or personal data in logs, no stack traces or internals shown to end users, and as little personal data as possible in responses and templates.
- Fail clearly. Do not silently swallow exceptions: a bare `except: pass` hides exactly the incident someone will later have to reconstruct.
- Do not weaken an existing control for convenience. When a change alters security-sensitive behaviour, call out the risk explicitly and keep auditability intact.

## Tests and scope

- Add or update tests for non-trivial logic when the project has tests: unit tests for services, integration tests for routes, following the existing test patterns.
- Do not modify unrelated files, and do not rename files, modules or symbols without a clear benefit.
- Avoid N+1 queries and obvious repeated work. Mention a performance tradeoff when it materially affects the solution.

## Not without an explicit request

Each of these raises the operational or maintenance cost of the project, so it is the user's decision, not a side effect of a task:

- Introducing Celery. It is an optional component: `workers/` exists only once it has been approved.
- Introducing Redis, Kafka, GraphQL or a microservice split
- Introducing a heavy frontend framework
- Adding a dependency when the standard library or the current dependencies are sufficient
- Rewriting a large file when a focused patch is enough
- Replacing a project-specific pattern with a generic one without clear benefit

If one of these looks like the right answer, say so and explain why, then wait for the decision instead of building it.

## Response format

Keep explanations short unless a deeper one is clearly needed.

**Bug fix**

1. Root cause, briefly
2. Whether the proposed fix fits the current architecture
3. The recommended code change
4. Impacted files
5. Risks or follow-up, only when necessary

**New feature**

1. Implementation approach
2. How it fits the current Flask architecture
3. File-by-file changes, with complete code blocks rather than fragments where practical

**Review**

- Order findings by importance.
- Separate must-fix from nice-to-have.
- Call out correctness, security, maintainability and test gaps clearly.
