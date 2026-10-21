# spond-no-match-mcp

An [MCP](https://modelcontextprotocol.io/) server for managing kids' sports activities on [Spond](https://spond.com/). Built for parents who want to give AI assistants access to upcoming matches, training schedules, and attendance — so you can ask "what's on this week?" or "sign Oliver up for Saturday's match" from any MCP-capable client.

## Features

- **Six tools** — list groups, upcoming events, event details, attendance status, RSVP, and search
- **Family member mapping** — configure which kids belong to which groups
- **Norwegian output** — responses formatted in Norwegian (dates, weekdays, status labels)
- **TTL caching** — groups cached 1h, events 5min to minimize API calls
- **Bearer token auth** — optional authentication for protecting sensitive family data
- **Scale-to-zero ready** — lightweight Python server, works great on Knative

## Tools

| Tool                  | Description                                                     |
| --------------------- | --------------------------------------------------------------- |
| `list_groups`         | List all Spond groups with member counts                        |
| `get_upcoming_events` | Get upcoming events, filterable by kid or group                 |
| `get_event_details`   | Full details for a specific event (location, description, RSVP) |
| `get_attendance`      | Show which events are missing responses for your kids           |
| `respond_to_event`    | Accept or decline an event for a family member                  |
| `search_events`       | Search upcoming events by text in title or description          |

## Quick Start

### Prerequisites

- Python 3.11+
- A [Spond](https://spond.com/) account with active group memberships

### Run locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
SPOND_USERNAME=you@example.com \
SPOND_PASSWORD=your-password \
KIDS_CONFIG='[{"name":"Oliver","groups":["Team 2013"]},{"name":"Emma","groups":["Team 2017"]}]' \
python main.py
```

The server starts on port 8080:

- Health check: `http://localhost:8080/health`
- MCP SSE endpoint: `http://localhost:8080/sse`

### Docker

```bash
docker build -t spond-mcp .
docker run -p 8080:8080 \
  -e SPOND_USERNAME=you@example.com \
  -e SPOND_PASSWORD=your-password \
  -e 'KIDS_CONFIG=[{"name":"Oliver","groups":["Team 2013"]}]' \
  spond-mcp
```

### Environment Variables

| Variable         | Required | Default                 | Description                                       |
| ---------------- | -------- | ----------------------- | ------------------------------------------------- |
| `SPOND_USERNAME` | Yes      |                         | Spond account email                               |
| `SPOND_PASSWORD` | Yes      |                         | Spond account password                            |
| `KIDS_CONFIG`    | No       | `[]`                    | JSON array mapping kid names to Spond group names |
| `MCP_AUTH_TOKEN` | No       |                         | Bearer token for authentication (see below)       |
| `PORT`           | No       | `8080`                  | Server port                                       |
| `BASE_URL`       | No       | `http://localhost:8080` | Public URL for SSE endpoint construction          |

### `KIDS_CONFIG` Format

Maps your children's first names to their Spond group names. Group matching is fuzzy — partial matches work (e.g. `"Team 2013"` matches `"Fjordvik Team 2013"`).

```json
[
  {"name": "Oliver", "groups": ["Team 2013", "School 2014"]},
  {"name": "Emma", "groups": ["Team 2017"]}
]
```

Without `KIDS_CONFIG`, the server still works but can't filter by kid or show per-kid attendance.

## Authentication

This server handles sensitive family data and supports optional bearer token authentication. When `MCP_AUTH_TOKEN` is set, all requests (except `/health`) must include an `Authorization: Bearer <token>` header.

- `/health` is always exempt (required for Knative/K8s health probes)
- When `MCP_AUTH_TOKEN` is empty or unset, auth is disabled (backward compatible)
- Uses constant-time comparison (`hmac.compare_digest`) to prevent timing attacks

```bash
# Run with auth enabled
MCP_AUTH_TOKEN=my-secret-token \
SPOND_USERNAME=you@example.com \
SPOND_PASSWORD=your-password \
python main.py

# Test with auth
curl -H "Authorization: Bearer my-secret-token" http://localhost:8080/sse
```

For Kubernetes deployments, store the token as a Secret and reference it in your service manifest:

```yaml
env:
- name: MCP_AUTH_TOKEN
  valueFrom:
    secretKeyRef:
      name: mcp-auth-token
      key: token
```

## Usage with mcporter

[mcporter](https://github.com/steipete/mcporter) can connect to this server as a remote MCP tool:

```bash
# List all groups
mcporter call spond.list_groups

# Get this week's events for a specific kid
mcporter call spond.get_upcoming_events kid_name=Oliver days=7

# Check what needs a response
mcporter call spond.get_attendance kid_name=Oliver

# Accept a match
mcporter call spond.respond_to_event event_id=ABC123 kid_name=Oliver accept=true

# Search for upcoming matches
mcporter call spond.search_events query=kamp days=30
```

For authenticated servers, configure mcporter with the Authorization header in `~/.mcporter/mcporter.json`:

```json
{
  "mcpServers": {
    "spond": {
      "url": "https://your-spond-mcp.example.com/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

## Architecture

```text
MCP Client (mcporter, Claude, etc.)
    │ HTTP/SSE (JSON-RPC)
    ▼
spond-mcp (:8080)
    │
    └── api.spond.com (Spond API)
```

- Implements the [Model Context Protocol](https://modelcontextprotocol.io/) over HTTP+SSE
- Uses [mcp](https://pypi.org/project/mcp/) SDK with Starlette SSE transport
- Uses [spond](https://github.com/Olen/Spond) library for API access
- Stateless — all caching is in-memory with configurable TTLs

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests (87 tests, including auth middleware tests)
pytest -v

# Lint
ruff check .
```

## Homelab Deployment

This server is designed to run on Knative with scale-to-zero. See [knative-service.yaml](config/knative-service.yaml) and [.mise.toml](.mise.toml) for deployment tasks.

Authentication is enabled via `MCP_AUTH_TOKEN` from a K8s Secret (`mcp-auth-token` in `mcp` namespace).

```bash
# Build and deploy (requires mise + Docker + kubectl)
mise run full-deploy

# Integration test against deployed service (auto-fetches auth token from K8s)
mise run test:mcp
```

## Data Source

- **Spond API** via [Olen/Spond](https://github.com/Olen/Spond) — unofficial Python wrapper for the Spond mobile app API

## License

MIT
