# Publishing to MCP Registry

This document explains how to publish the lit-mcp server to the MCP Registry using automated GitHub Actions.

## Overview

The project is set up for automated publishing to both PyPI and the MCP Registry when version tags are pushed.

## Files Added/Modified

- `server.json` - MCP server configuration for the registry
- `.github/workflows/publish.yml` - Updated existing GitHub Actions workflow for automated publishing
- `scripts/validate-server.py` - Script to validate server.json against MCP schema
- `README.md` - Updated with MCP name format for PyPI validation

## Publishing Process

### Automatic Publishing (Recommended)

1. **Create a version tag:**

   ```bash
   git tag v0.1.4
   git push origin v0.1.4
   ```

2. **The GitHub Actions workflow will:**
   - Run tests
   - Build the package
   - Publish to PyPI (requires `PYPI_TOKEN` secret)
   - Update server.json version automatically
   - Publish to MCP Registry using GitHub OIDC

### Manual Publishing

If you need to publish manually:

1. **Install MCP Publisher:**

   ```bash
   curl -L "https://github.com/modelcontextprotocol/registry/releases/download/latest/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
   sudo mv mcp-publisher /usr/local/bin/
   ```

2. **Login to MCP Registry:**

   ```bash
   mcp-publisher login github
   ```

3. **Publish:**

   ```bash
   mcp-publisher publish
   ```

## Required Secrets

Add these secrets in GitHub repository settings (Settings → Secrets and variables → Actions):

- `PYPI_TOKEN` - PyPI API token for publishing packages

## Validation

You can validate the server.json locally:

```bash
uv run python scripts/validate-server.py
```

## Server Configuration

The `server.json` file contains:

- **Name**: `io.github.gauravfs-14/lit-mcp` (GitHub namespace)
- **Package**: PyPI package `lit-mcp`
- **Transport**: stdio (standard for MCP servers)
- **Version**: Automatically updated during publishing

## Verification

After publishing, verify your server appears in the registry:

```bash
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.gauravfs-14/lit-mcp"
```

## Troubleshooting

- **Package validation failed**: Ensure the README.md contains the MCP name format comment
- **Authentication failed**: Check GitHub OIDC permissions in the workflow
- **Version mismatch**: The workflow automatically updates versions in server.json

## Next Steps

1. Add `PYPI_TOKEN` secret to your GitHub repository
2. Create and push a version tag to trigger the first automated publish
3. Verify the server appears in the MCP Registry
4. Test installation with MCP clients
