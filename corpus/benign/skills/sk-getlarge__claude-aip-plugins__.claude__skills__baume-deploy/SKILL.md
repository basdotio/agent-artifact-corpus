---
name: baume-deploy
description: Deploy the Baume MCP server to Fly.io with correct build context
---

You are a deployment assistant for the Baume MCP server on Fly.io.

## When to use this skill

Use this skill when the user wants to:

- Deploy the Baume MCP server
- Update the Fly.io deployment
- Fix deployment issues
- Check deployment status
- Manage Fly.io resources (postgres, storage, secrets)
- Debug runtime issues

## CRITICAL: Build Context Requirement

The Dockerfile expects the build context to be the **repository root**, not the mcp-server directory.

### Why?

The Dockerfile needs access to files outside `plugins/baume/mcp-server/`:

- `package.json` and `package-lock.json` at repo root (npm workspace)
- `patches/` directory for patch-package
- `plugins/baume/openapi-reviewer/` (peer dependency that gets built first)

### Correct Command

**Always run from the repository root:**

```bash
fly deploy -c plugins/baume/mcp-server/fly.toml -a baume-mcp
```

### Wrong Commands (DO NOT USE)

```bash
# WRONG - breaks Docker context
cd plugins/baume/mcp-server && fly deploy

# WRONG - passing directory instead of config
fly deploy plugins/baume/mcp-server -a baume-mcp

# WRONG - from wrong directory
fly deploy plugins/baume/mcp-server/fly.toml
```

## Common Operations

### Deploy

```bash
# Standard deploy from repo root
fly deploy -c plugins/baume/mcp-server/fly.toml -a baume-mcp

# With extended timeout for slow builds
fly deploy -c plugins/baume/mcp-server/fly.toml -a baume-mcp --wait-timeout 300

# Deploy without starting (useful for config changes)
fly deploy -c plugins/baume/mcp-server/fly.toml -a baume-mcp --strategy immediate
```

### Check Status

```bash
# App status
fly status -a baume-mcp

# Recent logs (last 100 lines)
fly logs -a baume-mcp

# Stream logs in real-time
fly logs -a baume-mcp -f

# Health check
curl https://baume-mcp.getlarge.eu/health

# View app info (regions, IPs, etc.)
fly info -a baume-mcp
```

### Manage Secrets

```bash
# List secrets (names only, values hidden)
fly secrets list -a baume-mcp

# Set a secret (triggers deploy immediately)
fly secrets set KEY=value -a baume-mcp

# Set a secret (staged, needs manual deploy)
fly secrets set KEY=value -a baume-mcp --stage

# Set multiple secrets at once
fly secrets set KEY1=value1 KEY2=value2 -a baume-mcp

# Unset a secret
fly secrets unset KEY -a baume-mcp
```

### Environment Variables

Key environment variables for the MCP server:

| Variable              | Description                                   | Required        |
| --------------------- | --------------------------------------------- | --------------- |
| `AUTH_ENABLED`        | Enable OAuth2 authentication (`true`/`false`) | No              |
| `ORY_PROJECT_URL`     | Ory Network project URL                       | If AUTH_ENABLED |
| `ORY_PROJECT_API_KEY` | Ory admin API key for introspection           | No              |
| `MCP_RESOURCE_URI`    | Public URL for audience validation            | If AUTH_ENABLED |
| `VALIDATE_AUDIENCE`   | JWT audience validation (`true`/`false`)      | No              |
| `TOKEN_DEBUG`         | Token validation debug logging                | No              |
| `LOG_LEVEL`           | Logging level (info, debug, warn, error)      | No              |
| `ANTHROPIC_API_KEY`   | For baume-correlate tool                      | No              |

## Debugging

### SSH into Running Machine

```bash
# Interactive shell
fly ssh console -a baume-mcp

# Run a command
fly ssh console -a baume-mcp -C "ls -la /app"

# Check Node.js process
fly ssh console -a baume-mcp -C "ps aux | grep node"
```

### View Machine Details

```bash
# List machines
fly machines list -a baume-mcp

# Machine status
fly machines status <machine-id> -a baume-mcp

# View machine logs
fly logs -a baume-mcp --instance <instance-id>
```

### Debug Build Issues

If the build fails with "not found" errors for files like:

- `package-lock.json`
- `patches/`
- `plugins/baume/openapi-reviewer`
- `.npmrc`

**You're using the wrong build context.** Use the correct command above.

### Debug Runtime Issues

```bash
# Check recent crashes
fly logs -a baume-mcp | grep -i "error\|crash\|exit"

# Check memory usage
fly status -a baume-mcp

# Check health endpoint response
curl -v https://baume-mcp.getlarge.eu/health

# Check OAuth metadata
curl https://baume-mcp.getlarge.eu/.well-known/oauth-protected-resource
```

### Local Docker Build Test

```bash
# From repo root
docker build -f plugins/baume/mcp-server/Dockerfile -t baume-mcp .

# Run locally
docker run -p 4000:4000 -e LOG_LEVEL=debug baume-mcp
```

## Resource Management

### Postgres Database

```bash
# Create postgres cluster (if needed)
fly postgres create --name baume-mcp-db --region cdg

# Attach to app (sets DATABASE_URL secret)
fly postgres attach baume-mcp-db -a baume-mcp

# Connect to postgres
fly postgres connect -a baume-mcp-db

# List postgres clusters
fly postgres list
```

### Tigris Object Storage (S3-compatible)

```bash
# Create storage bucket (sets AWS_* secrets automatically)
fly storage create -a baume-mcp -n baume-storage

# List buckets
fly storage list -a baume-mcp

# Dashboard (opens browser)
fly storage dashboard -a baume-mcp
```

### Scaling

```bash
# Scale to 2 machines
fly scale count 2 -a baume-mcp

# Scale memory
fly scale memory 512 -a baume-mcp

# Scale to different regions
fly scale count 1 --region cdg -a baume-mcp
fly scale count 1 --region iad -a baume-mcp
```

### Restart & Destroy

```bash
# Restart all machines
fly apps restart baume-mcp

# Stop all machines (saves money)
fly scale count 0 -a baume-mcp

# Destroy app (DANGEROUS)
fly apps destroy baume-mcp
```

## Deployment Checklist

1. Ensure you're at the repository root
2. Verify secrets are set: `fly secrets list -a baume-mcp`
3. Run: `fly deploy -c plugins/baume/mcp-server/fly.toml -a baume-mcp`
4. Check logs: `fly logs -a baume-mcp`
5. Verify health: `curl https://baume-mcp.getlarge.eu/health`
6. Test MCP endpoint: `curl https://baume-mcp.getlarge.eu/mcp`

## URLs

| Endpoint       | URL                                                                |
| -------------- | ------------------------------------------------------------------ |
| Health         | https://baume-mcp.getlarge.eu/health                               |
| MCP            | https://baume-mcp.getlarge.eu/mcp                                  |
| OAuth Metadata | https://baume-mcp.getlarge.eu/.well-known/oauth-protected-resource |
| DCR Proxy      | https://baume-mcp.getlarge.eu/oauth2/register                      |
