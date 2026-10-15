# garage61-race-engineer-mcp

An MCP server built with [FastMCP](https://gofastmcp.com) that acts as a telemetry analysis engine for the [Garage61](https://garage61.net) platform.

## Requirements

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A Garage61 API key

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```sh
cp .env.example .env
```

```
GARAGE61_API_KEY=your_api_key_here
```

## Running with Docker Compose

```sh
docker compose up
```

The MCP server will be available at `http://localhost:8000/mcp` using the `streamable-http` transport.

## Running with Docker directly

```sh
docker build -t garage61-race-engineer-mcp .
docker run -p 8000:8000 --env-file .env garage61-race-engineer-mcp
```

## Development with Dev Container

This project includes a [Dev Container](https://containers.dev) configuration that provides a fully configured development environment with all dependencies pre-installed.

**VS Code:** Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers), then open the command palette and run `Dev Containers: Reopen in Container`.

The dev container uses `docker-compose.yml` as its base and includes:

- Python 3.13 with the project's virtualenv at `.venv`
- Docker-in-Docker for building and running containers from within the dev container
- VS Code extensions: Pylance, Ruff, Debugpy, GitLens, Docker

Dependencies are installed automatically on container creation via `uv sync`.
