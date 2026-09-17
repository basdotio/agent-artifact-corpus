# Project Startup

Commands for running and managing the Commander MTG backend server.

## Commands

### Start Backend Server (Production)

```bash
cd backend && make start
```

Runs: `USE_SQLITE=true uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Start Backend Server (Development with Reload)

```bash
cd backend && make dev
```

Runs: `USE_SQLITE=true uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Stop Backend Server

```bash
cd backend && make stop
```

### Install Dependencies

```bash
cd backend && make install
```

Runs: `uv sync`

### Check Dependency Tree

```bash
cd backend && make check-deps
```

### Open Python Shell with App Context

```bash
cd backend && make shell
```

## Environment

- Server runs on `http://localhost:8000`
- API docs available at `http://localhost:8000/docs`
- Uses SQLite for local development (`USE_SQLITE=true`)

## Common Workflow

```bash
# First time setup
cd backend && make install

# Run migrations
cd backend && make migrate

# Start development server
cd backend && make dev
```

## Port

- Default port: **8000**
- To change, modify the Makefile or run:
  ```bash
  USE_SQLITE=true uv run uvicorn app.main:app --port 3000
  ```
