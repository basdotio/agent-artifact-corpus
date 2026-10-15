# New project setup

## Settle the basics first
Ask, with proposed defaults: what the product does and for whom, expected scale in the first year, team size and experience, hosting and budget limits, deadlines, and compliance needs. These answers decide the architecture more than any pattern does.

## Architecture defaults to propose
Put these in a decision brief with their alternatives; do not apply them silently.

- Backend: a modular monolith with layered architecture (API, services, repositories, models), split into services only when a part needs independent scaling, deployment, or ownership. Clean or hexagonal architecture when the domain logic is rich and long-lived.
- Background work: a task queue (Celery with Redis, or Cloud Tasks or Pub/Sub on GCP) instead of in-process background tasks for anything that must not be lost.
- Android: MVVM with unidirectional data flow, a repository layer, and Hilt for dependency injection. Add use cases only when logic is shared or complex.
- Web: feature folders, component-driven UI, a typed API client, and server state in a query library.

## Folder skeletons

FastAPI service:
```
service-name/
  pyproject.toml
  src/service_name/
    main.py              app factory; registers routers and exception handlers
    config.py            Settings (pydantic-settings)
    api/
      deps.py            dependencies: database session, current user
      routes/orders.py   thin HTTP layer: parse, call a service, map errors
    schemas/orders.py    request and response models (Pydantic)
    services/orders.py   business logic; no HTTP or SQL details
    repositories/orders.py  data access (SQLAlchemy)
    models/orders.py     ORM models
    workers/             Celery app and tasks, if needed
    core/                logging, error types, security helpers
  migrations/            Alembic
  tests/
    unit/
    integration/
    conftest.py
  .env.example
  README.md
```

Android app:
```
app/src/main/java/com/example/app/
  ui/<feature>/        screen composables or fragments, <Feature>ViewModel, <Feature>UiState
  domain/              models and use cases (only when needed)
  data/
    repository/        <Feature>Repository interface and implementation
    remote/            Retrofit services and DTOs
    local/             Room DAOs and entities
  di/                  Hilt modules
```

Web frontend (React, TypeScript, Vite):
```
src/
  app/                 routing and providers
  features/<feature>/  components, hooks, api, types, tests
  components/          shared UI components
  lib/                 api client and utilities
  styles/              design tokens and global styles
```

## Tooling baseline
- Python: the team's package manager (uv or poetry), ruff for linting and formatting, mypy or pyright in strict mode for new code, pytest with pytest-cov, and pre-commit.
- Android: Kotlin with the Gradle Kotlin DSL and a version catalog, ktlint or detekt, Android Lint, JUnit with MockK and Turbine, and Compose for new screens.
- Web: TypeScript in strict mode, ESLint and Prettier, Vitest with Testing Library, and Playwright for end-to-end tests.
- Every repository: .editorconfig, .gitignore, .env.example, a README with a five-minute quick start, and a CI workflow that runs lint, type checks, tests, and the build on every pull request.

Check current stable versions in each registry at setup time and pin them.

## First slices
1. Scaffold, tooling, CI, and one passing placeholder test.
2. Configuration, logging, error handling, and a health endpoint or app shell.
3. The first vertical feature slice, end to end, with tests.
4. Deployment to a staging environment (deployment skill).
