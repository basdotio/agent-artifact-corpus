# Python stack guide: FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, Redis

Follow the repository first. Use this guide for new code and where the repository has no established pattern. Check current versions in PyPI before pinning anything new.

## Project basics
- Use the supported Python version the repository pins (pyproject `requires-python`). For new projects, use a current supported release.
- One package manager per repository, chosen by its lockfile (uv.lock, poetry.lock, or requirements files).
- Tooling: `ruff check .`, `ruff format .`, `mypy src` or `pyright`, `pytest -q`. Run the same commands CI runs.
- Use pathlib for paths so code works on Windows and Linux.

## FastAPI
- Routers are thin: parse the request, call one service function, return a response model. No business logic or SQL in routes.
- Use `Depends` for the database session, the current user, and services. This is the dependency injection point.
- Declare `response_model` and explicit status codes. Version public APIs under a prefix such as /api/v1.
- Raise domain exceptions in services and translate them to HTTP errors in exception handlers registered in the app factory. Do not raise HTTPException from services.
- Use the lifespan handler for startup and shutdown (connection pools, clients).
- `async def` only when the endpoint awaits async I/O. A sync endpoint runs in a thread pool; an async endpoint that calls blocking code stalls the event loop for every request.
- Use FastAPI BackgroundTasks only for work that may be lost safely. Anything important goes to the task queue.
- Paginate list endpoints (limit plus cursor or offset), with a maximum page size.

## Pydantic v2
- Separate schemas for create, update, and read (`OrderCreate`, `OrderUpdate`, `OrderRead`). Never return ORM objects directly.
- `model_config = ConfigDict(from_attributes=True)` on read schemas built from ORM rows.
- Put constraints in the schema (`Field(max_length=200)`, `ge=0`) instead of validating by hand in routes.
- Settings: `pydantic-settings` BaseSettings with an env prefix, `SecretStr` for secrets, and one cached settings instance.

## SQLAlchemy 2.x
- Use the 2.0 style: `select(Model).where(...)`, `session.scalars(...)`.
- One session per request, created and closed by a dependency. Commit in the service layer at the end of a unit of work.
- In async apps, use the async engine and driver (for example asyncpg), and load relationships explicitly with `selectinload` or `joinedload`; lazy loading fails under async.
- Repositories own queries. Services never build queries themselves.
- Add indexes for new filters and sorts, and constraints (unique, foreign key, check) for invariants.

## Alembic
- Generate with `alembic revision --autogenerate -m "<what>"`, then read and fix the generated file. Autogenerate misses renames and some type changes.
- One migration per slice, with a working `downgrade()`.
- Name constraints through a naming convention on the metadata so migrations are stable.
- Follow the expand and contract pattern for zero-downtime changes (deployment skill, migrations reference). Running `alembic upgrade` needs the user's approval; the shell guard asks.

## Celery
- Tasks take IDs and small values, never ORM objects or large payloads, and load fresh data themselves.
- Make every task idempotent: safe to run twice. Use a unique key or a status check before side effects.
- Retries: `autoretry_for=(TransientError,)`, `retry_backoff=True`, `retry_backoff_max`, `retry_jitter=True`, and a `max_retries` limit. Never retry validation errors.
- Set `soft_time_limit` and `time_limit` on long tasks. Use `acks_late=True` with `task_reject_on_worker_lost=True` only for idempotent tasks that must not be lost.
- Route slow tasks to their own queue so they cannot starve fast ones.
- Never call `.get()` on another task's result inside a task. Use chains or callbacks.
- With a Redis broker, set `visibility_timeout` longer than the longest ETA or countdown you use, or tasks get redelivered.
- Test with eager mode only for unit tests, and run at least one integration test against a real worker setup.

## Redis
- Key names follow `app:entity:id[:field]`, for example `shop:user:42:profile`.
- Every cache key has a TTL. Decide the invalidation rule when you add the cache.
- Never use KEYS in production code; use SCAN. Use pipelines for batches.
- Distributed locks: redis-py `Lock` with a timeout and a blocking timeout, released in finally.
- Serialize as JSON (or msgpack). Never pickle data that could come from users.

## HTTP clients
- httpx with explicit timeouts, connection limits, and retries for idempotent requests only. One client per app, created in the lifespan handler.

## Logging
- stdlib logging with a JSON formatter, or structlog, configured once at startup. Include the request ID, from a middleware, in every log line.
