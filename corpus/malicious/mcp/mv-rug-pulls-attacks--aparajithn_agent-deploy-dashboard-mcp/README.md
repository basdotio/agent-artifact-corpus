# Agent Deploy Dashboard MCP Server

**Unified deployment management** for AI agents — manage Vercel, Render, Railway, and Fly.io services from a single MCP + REST API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

🚀 **Multi-Platform Support** — Manage Vercel, Render, Railway, and Fly.io from one interface  
📊 **Deployment Status** — Check deploy status and health across all platforms  
📝 **Unified Logging** — Tail logs and view build logs  
⚙️ **Environment Management** — List, update, and manage env vars  
🔄 **Redeploy Operations** — Trigger redeployments and rollbacks  
💰 **x402 Micropayments** — Built-in payment middleware for API monetization  
🔒 **Rate Limiting** — 50 free requests/IP/day with paid tier support

## Quick Start

### MCP Configuration

Add to your MCP settings file (`cline_mcp_settings.json` or similar):

```json
{
  "mcpServers": {
    "agent-deploy-dashboard": {
      "url": "https://agent-deploy-dashboard-mcp.onrender.com/mcp"
    }
  }
}
```

### REST API

Base URL: `https://agent-deploy-dashboard-mcp.onrender.com`

#### List All Services

```bash
curl -X GET https://agent-deploy-dashboard-mcp.onrender.com/api/v1/list_all_services
```

Response:
```json
{
  "success": true,
  "services": [
    {
      "id": "prj_abc123",
      "name": "my-app",
      "platform": "vercel",
      "url": "https://my-app.vercel.app",
      "framework": "nextjs"
    },
    {
      "id": "srv_xyz789",
      "name": "api-service",
      "platform": "render",
      "type": "web_service",
      "region": "oregon"
    }
  ],
  "count": 2
}
```

#### Get Deploy Status

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/get_deploy_status \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "vercel",
    "service_id": "prj_abc123"
  }'
```

Response:
```json
{
  "success": true,
  "platform": "vercel",
  "service_id": "prj_abc123",
  "deployment_id": "dpl_xyz",
  "status": "READY",
  "url": "https://my-app.vercel.app",
  "created_at": 1709823600000
}
```

#### Tail Logs

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/tail_logs \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "render",
    "service_id": "srv_xyz789",
    "lines": 50
  }'
```

#### Get Environment Variables

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/get_env_vars \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "vercel",
    "service_id": "prj_abc123"
  }'
```

Response:
```json
{
  "success": true,
  "platform": "vercel",
  "service_id": "prj_abc123",
  "env_vars": {
    "DATABASE_URL": {
      "value": "[ENCRYPTED]",
      "target": ["production"],
      "type": "encrypted"
    },
    "API_KEY": {
      "value": "abc123",
      "target": ["production", "preview"],
      "type": "plain"
    }
  },
  "count": 2
}
```

#### Set Environment Variable

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/set_env_var \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "render",
    "service_id": "srv_xyz789",
    "key": "NEW_FEATURE_FLAG",
    "value": "true"
  }'
```

#### Trigger Redeploy

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/trigger_redeploy \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "vercel",
    "service_id": "prj_abc123"
  }'
```

#### Get Build Logs

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/get_build_logs \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "vercel",
    "deploy_id": "dpl_xyz"
  }'
```

#### Check Health

```bash
curl -X POST https://agent-deploy-dashboard-mcp.onrender.com/api/v1/check_health \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://my-app.vercel.app/health"
  }'
```

Response:
```json
{
  "success": true,
  "url": "https://my-app.vercel.app/health",
  "status_code": 200,
  "healthy": true,
  "response_time_ms": 142,
  "headers": {
    "content-type": "application/json",
    "x-vercel-id": "sfo1::abc123"
  }
}
```

## Pricing

### Free Tier
- **50 requests per IP per day**
- All tools included
- All platforms supported
- No credit card required

### Paid Tier (HTTP 402 Payment)
After free tier exhausted:
- **$0.01 per request**
- Payment via HTTP 402 with crypto wallet
- Wallet address: `0x8E844a7De89d7CfBFe9B4453E65935A22F146aBB`
- Include `X-Payment` header with payment proof

## Platform Support

| Platform | List Services | Deploy Status | Logs | Env Vars | Redeploy | Build Logs |
|----------|--------------|---------------|------|----------|----------|------------|
| **Vercel** | ✅ Full | ✅ Full | ⚠️ Build only | ✅ Full | ✅ Full | ✅ Full |
| **Render** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Railway** | ✅ Basic | ⏳ Planned | ⏳ Planned | ⏳ Planned | ⏳ Planned | ⏳ Planned |
| **Fly.io** | ✅ Basic | ⏳ Planned | ⏳ Planned | ⏳ Planned | ⏳ Planned | ⏳ Planned |

✅ = Fully implemented  
⚠️ = Partial implementation  
⏳ = Planned/stub implementation  

## Tools Reference

### 1. `list_all_services()`
List all services across all platforms.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "services": [...],
  "count": 10,
  "errors": null
}
```

---

### 2. `get_deploy_status(platform, service_id)`
Check deployment status for a specific service.

**Parameters:**
- `platform` (string): Platform name — `vercel`, `render`, `railway`, or `fly`
- `service_id` (string): Service/project ID

**Returns:**
```json
{
  "success": true,
  "platform": "vercel",
  "service_id": "prj_abc",
  "deployment_id": "dpl_xyz",
  "status": "READY",
  "url": "https://...",
  "created_at": 1709823600000
}
```

---

### 3. `tail_logs(platform, service_id, lines=100)`
Stream recent logs from a service.

**Parameters:**
- `platform` (string): Platform name
- `service_id` (string): Service/project ID
- `lines` (integer, optional): Number of log lines (default: 100)

**Returns:**
```json
{
  "success": true,
  "platform": "render",
  "service_id": "srv_xyz",
  "logs": [...],
  "count": 100
}
```

---

### 4. `get_env_vars(platform, service_id)`
List environment variables for a service.

**Parameters:**
- `platform` (string): Platform name
- `service_id` (string): Service/project ID

**Returns:**
```json
{
  "success": true,
  "platform": "vercel",
  "env_vars": {"KEY": "value"},
  "count": 5
}
```

---

### 5. `set_env_var(platform, service_id, key, value)`
Update an environment variable.

**Parameters:**
- `platform` (string): Platform name
- `service_id` (string): Service/project ID
- `key` (string): Environment variable name
- `value` (string): Environment variable value

**Returns:**
```json
{
  "success": true,
  "message": "Environment variable set successfully"
}
```

---

### 6. `trigger_redeploy(platform, service_id)`
Force redeploy a service.

**Parameters:**
- `platform` (string): Platform name
- `service_id` (string): Service/project ID

**Returns:**
```json
{
  "success": true,
  "deployment_id": "dpl_new",
  "message": "Redeploy triggered successfully"
}
```

---

### 7. `get_build_logs(platform, deploy_id)`
Fetch build logs for a deployment.

**Parameters:**
- `platform` (string): Platform name
- `deploy_id` (string): Deployment ID

**Returns:**
```json
{
  "success": true,
  "logs": [...],
  "count": 50
}
```

---

### 8. `check_health(url)`
Ping a health endpoint.

**Parameters:**
- `url` (string): URL to check

**Returns:**
```json
{
  "success": true,
  "status_code": 200,
  "healthy": true,
  "response_time_ms": 142
}
```

---

### 9. `rollback_deploy(platform, service_id, version)`
Rollback to a previous deployment version.

**Parameters:**
- `platform` (string): Platform name
- `service_id` (string): Service/project ID
- `version` (string): Version/deployment ID to rollback to

**Returns:**
```json
{
  "success": false,
  "error": "Rollback not yet implemented for this platform"
}
```

---

## Environment Variables

Configure platform API access via environment variables:

```bash
# Vercel
VERCEL_TOKEN=your_vercel_token

# Render
RENDER_API_KEY=your_render_api_key

# Railway
RAILWAY_TOKEN=your_railway_token

# Fly.io
FLY_API_TOKEN=your_fly_api_token

# Payment (optional)
X402_WALLET_ADDRESS=0x8E844a7De89d7CfBFe9B4453E65935A22F146aBB
```

Get your API tokens:
- **Vercel**: https://vercel.com/account/tokens
- **Render**: https://dashboard.render.com/u/settings#api-keys
- **Railway**: https://railway.app/account/tokens
- **Fly.io**: Run `flyctl auth token`

## Development

### Local Setup

```bash
# Clone repo
git clone https://github.com/aparajithn/agent-deploy-dashboard-mcp.git
cd agent-deploy-dashboard-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export VERCEL_TOKEN=your_token
export RENDER_API_KEY=your_key

# Run server
uvicorn src.main:app --reload --port 8080
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8080/health

# List services (requires platform tokens)
curl http://localhost:8080/api/v1/list_all_services

# Test MCP protocol
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'

# List MCP tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

### Docker

```bash
# Build
docker build -t agent-deploy-dashboard-mcp .

# Run
docker run -p 8080:8080 \
  -e VERCEL_TOKEN=your_token \
  -e RENDER_API_KEY=your_key \
  -e PUBLIC_HOST=localhost \
  agent-deploy-dashboard-mcp
```

## Deployment on Render

### Via Web UI

1. Fork this repo to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Web Service**
4. Connect your GitHub repo: `aparajithn/agent-deploy-dashboard-mcp`
5. Configure:
   - **Name**: `agent-deploy-dashboard-mcp`
   - **Runtime**: Docker
   - **Region**: Oregon (or closest)
   - **Instance Type**: Free
6. Add environment variables:
   - `VERCEL_TOKEN`
   - `RENDER_API_KEY`
   - `RAILWAY_TOKEN` (optional)
   - `FLY_API_TOKEN` (optional)
   - `X402_WALLET_ADDRESS` (optional)
   - `PUBLIC_HOST` = `agent-deploy-dashboard-mcp.onrender.com`
7. Click **Create Web Service**

### Via Render API

```bash
curl -X POST https://api.render.com/v1/services \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "web_service",
    "name": "agent-deploy-dashboard-mcp",
    "repo": "https://github.com/aparajithn/agent-deploy-dashboard-mcp",
    "branch": "main",
    "runtime": "docker",
    "plan": "free",
    "region": "oregon",
    "envVars": [
      {"key": "VERCEL_TOKEN", "value": "your_token"},
      {"key": "RENDER_API_KEY", "value": "your_key"},
      {"key": "PUBLIC_HOST", "value": "agent-deploy-dashboard-mcp.onrender.com"}
    ]
  }'
```

## Architecture

```
agent-deploy-dashboard-mcp/
├── src/
│   ├── main.py              # FastMCP server + REST API
│   ├── tools/
│   │   ├── platforms.py     # Platform API clients (Vercel, Render, etc)
│   │   └── deploy_tools.py  # Tool implementations
│   └── middleware/
│       ├── rate_limit.py    # Rate limiting
│       └── x402.py          # Payment middleware
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Tech Stack

- **Python 3.11** — Modern async/await
- **FastAPI** — REST API framework
- **FastMCP** — MCP protocol implementation (Streamable HTTP)
- **httpx** — Fast async HTTP client
- **Pydantic** — Data validation

## API Reference Docs

Once deployed, view interactive API docs at:
- Swagger UI: `https://agent-deploy-dashboard-mcp.onrender.com/docs`
- OpenAPI JSON: `https://agent-deploy-dashboard-mcp.onrender.com/openapi.json`

## License

MIT License — see [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/aparajithn/agent-deploy-dashboard-mcp/issues)
- Email: aparajith@dabaracoffee.com

---

**Built for AI agents by Forge (Aparajith's coding agent)** 🤖
