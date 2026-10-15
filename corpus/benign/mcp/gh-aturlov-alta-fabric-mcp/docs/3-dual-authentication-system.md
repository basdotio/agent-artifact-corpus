# Dual Authentication System for Fabric MCP Server

## Overview

The Fabric MCP Server implements a flexible dual authentication system that supports both **interactive user authentication** (via device code flow) and **service principal authentication** (for automation). The authentication mode is automatically selected based on environment configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              main.py (MCP Tools)                        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│         FabricMCPService (Business Logic)               │
│  - REST API operations (workspaces, lakehouses)         │
│  - SQL operations (schema discovery, data queries)      │
│  - Authentication management (sign out)                 │
└──────┬──────────────────────────────┬───────────────────┘
       │                              │
       ▼                              ▼
┌─────────────────┐      ┌──────────────────────┐
│ FabricAPIClient │      │ FabricSQLClient      │
│ (REST APIs)     │      │ (SQL Endpoints)      │
└────────┬────────┘      └──────────┬───────────┘
         │                          │
         └──────────────┬───────────┘
                        │
         ┌──────────────▼──────────────┐
         │  create_auth_provider_      │
         │  from_env() (Factory)       │
         └──────────────┬──────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐        ┌──────────────────────┐
│ Interactive      │        │ Service Principal    │
│ AuthProvider     │        │ AuthProvider         │
│                  │        │                      │
│ Device Code Flow │        │ Client Credentials   │
│ Token Caching    │        │ No Caching           │
└──────────────────┘        └──────────────────────┘
        │                               │
        └───────────────┬───────────────┘
                        │
                        ▼
              ┌───────────────────┐
              │  MSAL Library     │
              │(Token Acquisition)│
              └───────────────────┘
```

## Authentication Modes

### 1. Interactive Authentication (Default)

**Use Case**: Individual users, development environments, ad-hoc analysis

**How It Works**:
1. Server starts without a `FABRIC_CLIENT_SECRET` environment variable
2. MCP server output shows device code authentication prompt:
   ```
   Please visit https://microsoft.com/devicelogin and enter code: XXXXXX
   ```
3. User opens browser, enters code, and signs in with their Microsoft account
4. Access token is acquired and cached locally
5. Subsequent requests use cached token (refreshed automatically when expired)

**Token Storage**:
- **Location**: `~/.fabric_mcp_token_cache.json`
- **Format**: MSAL token cache with encrypted credentials
- **Lifetime**: Typically 60 minutes for access tokens, refresh tokens for up to 90 days
- **Automatic Refresh**: MSAL handles silent refresh using cached refresh tokens

**Configuration**:
```bash
# Leave these unset or commented in .env
# FABRIC_CLIENT_ID will default to Power BI client ID
# FABRIC_TENANT_ID will default to 'common'
```

**Scope Behavior**:
- Uses `.default` scope which maps to delegated permissions
- Works with any Microsoft account in your tenant
- Automatically consents to required permissions on first authentication

**Advantages**:
- ✅ No service account credentials to manage
- ✅ Uses real user identity for audit trails
- ✅ Automatic token refresh
- ✅ Zero configuration needed
- ✅ Works with conditional access and multi-factor authentication

**Limitations**:
- ❌ Cannot be used in unattended CI/CD pipelines
- ❌ Token cache is tied to a specific user

### 2. Service Principal Authentication

**Use Case**: Automation, CI/CD pipelines, scheduled jobs, service integrations

**How It Works**:
1. Administrator creates Azure AD service principal with Fabric permissions
2. Environment variables are set with service principal credentials
3. On first request, MSAL acquires token using client credentials flow
4. Token is used for all subsequent requests (no caching)
5. When expired, new token is acquired on next request

**Configuration**:
Create `.env` file with:
```bash
FABRIC_CLIENT_ID=your_application_id
FABRIC_CLIENT_SECRET=your_client_secret
FABRIC_TENANT_ID=your_tenant_id
```

**Setup Steps**:
1. Register Azure AD application in your tenant
2. Create client secret (note: expires after configured period)
3. Grant application appropriate Fabric/Power BI permissions
4. Copy credentials to `.env` file
5. Redeploy when credentials are about to expire

**Scope Behavior**:
- Uses `.default` scope which maps to app-level permissions
- No user context (service principal identity)
- Permissions are granted through Azure AD application configuration

**Advantages**:
- ✅ Unattended operation in CI/CD pipelines
- ✅ No user token refresh needed
- ✅ Service account can be shared across multiple deployments
- ✅ Predictable permission model (app permissions)

**Limitations**:
- ❌ Credentials must be securely managed and rotated
- ❌ Audit logs show service principal, not user identity
- ❌ Requires Azure AD administrator intervention for setup

## Implementation Details

### Factory Pattern: `create_auth_provider_from_env()`

Located in `fabric_auth.py`, this factory function automatically selects the appropriate authentication provider:

```python
def create_auth_provider_from_env() -> BaseAuthProvider:
    """Create auth provider based on environment variables.
    
    Logic:
    - If FABRIC_CLIENT_SECRET exists → ServicePrincipalAuthProvider
    - Otherwise → InteractiveAuthProvider
    """
```

**Decision Logic**:
```
┌─ Check environment variables ─┐
│                               │
├─ FABRIC_CLIENT_SECRET set? ───┐
│  ├─ YES: Service Principal    │
│  ├─ NO:  Interactive          │
│  └─ Done!                     │
│                               │
└───────────────────────────────┘
```

### Token Acquisition

Both providers implement the same interface (`BaseAuthProvider.get_access_token()`):

**InteractiveAuthProvider**:
```
1. Check token cache
   └─ Valid token? Return it
   └─ Expired? Refresh using refresh token
   └─ Missing? Initiate device code flow
2. Prompt user in MCP output
3. User visits browser and enters code
4. Acquire token, cache, return
```

**ServicePrincipalAuthProvider**:
```
1. Call MSAL app.acquire_token_for_client()
2. MSAL caches token in memory
3. On expiration, automatically re-acquire
4. Return token
```

### Scope Configuration

**Current Scope**: `https://analysis.windows.net/powerbi/api/.default`

This scope works for:
- ✅ Workspace discovery
- ✅ Lakehouse discovery
- ✅ SQL endpoint connections
- ✅ All current MCP tools

**Why `.default` works**:
- For service principals: Maps to all app permissions configured in Azure AD
- For interactive users: Provides necessary delegated permissions for Fabric operations
- For both: Sufficient for REST APIs and SQL connections

### Client ID Strategy

**Interactive Mode**:
- **Default**: Power BI well-known app ID: `ea0616ba-638b-4df5-95b9-636659ae5121`
- **Override**: Set `FABRIC_CLIENT_ID` env var to use custom Azure AD app

**Service Principal Mode**:
- **Required**: Must set `FABRIC_CLIENT_ID` env var
- **No Default**: Service principals always need explicit configuration

## Usage Patterns

### Starting Fresh (Interactive)

```bash
# 1. Clone repo and install dependencies
git clone <repo>
cd fabric-mcp
conda create -p ./env python=3.12 -y
conda activate ./env
pip install -r requirements.txt

# 2. No .env needed! Just run:
python main.py

# 3. You'll see in output:
# "Please visit https://microsoft.com/devicelogin and enter code: ABC123"
```

### Setting Up Service Principal

```bash
# 1. Create Azure AD app (via Azure Portal)
# 2. Create client secret
# 3. Grant Fabric permissions

# 4. Configure .env
cp .env.example .env
# Edit .env with your credentials:
# FABRIC_CLIENT_ID=your_app_id
# FABRIC_CLIENT_SECRET=your_secret
# FABRIC_TENANT_ID=your_tenant

# 5. No user prompt - automatic token acquisition
python main.py
```

### Switching Authentication Modes

```bash
# Currently using interactive, want to switch to service principal:
# Just set FABRIC_CLIENT_SECRET in .env

# Currently using service principal, want to switch to interactive:
# Comment out FABRIC_CLIENT_SECRET in .env (or delete it)
```

### Clearing Authentication (Interactive Only)

```python
# In MCP server context, use the sign_out() tool:
# This clears the token cache, forcing re-authentication on next request
```

## Integration with MCP Tools

### Service Layer Initialization

`FabricMCPService.__init__()` handles all authentication setup:

```python
def __init__(self):
    load_dotenv()
    # Factory automatically selects correct provider
    self.auth_provider = create_auth_provider_from_env()
    # Pass provider to clients
    self.fabric_api = FabricAPIClient(self.auth_provider)
    self.fabric_sql = FabricSQLClient(self.auth_provider, self.fabric_api)
```

**Flow**:
1. MCP tool calls service method
2. Service needs to call REST API or SQL
3. Client calls `auth_provider.get_access_token()`
4. Token is automatically acquired (or refreshed) by appropriate provider
5. API/SQL call completes successfully

### Transparent Token Management

Copilot and other MCP clients don't need to worry about authentication:
- ✅ Token acquisition is automatic
- ✅ Token refresh happens silently
- ✅ Errors are caught and returned cleanly
- ✅ User sees consistent MCP tool interface regardless of auth mode

## Security Considerations

### Interactive Mode

- **Token Storage**: Credentials stored in local JSON file (encrypted at OS level on Windows/macOS)
- **Credentials Not in Git**: `.fabric_mcp_token_cache.json` is `.gitignore`'d
- **Token Validity**: Access tokens expire after 1 hour, refresh tokens valid up to 90 days
- **Browser-Based Auth**: User performs authentication in browser (not in MCP server)
- **Token Leakage Risk**: If cache file is compromised, attackers can access user's Fabric resources

**Risk Mitigation**:
- ✅ Run MCP server on secure machine
- ✅ Restrict file permissions on token cache
- ✅ Use `sign_out()` tool when switching users
- ✅ Don't share VS Code workspace with untrusted users

### Service Principal Mode

- **Credentials in .env**: Secret must be securely stored (never commit to Git)
- **`.env` in .gitignore**: Prevents accidental credential leakage
- **Credential Rotation**: Must rotate client secret periodically
- **Token Not Cached**: No persistent token storage (acquired on-demand)
- **Service Account Risk**: If `.env` file is compromised, entire service is compromised

**Risk Mitigation**:
- ✅ Store `.env` in secure location (CI/CD secrets manager preferred)
- ✅ Use different service principals for different environments (dev, staging, prod)
- ✅ Set Azure AD app permissions to minimum required (least privilege)
- ✅ Monitor audit logs for service principal activities
- ✅ Rotate credentials on a regular schedule (e.g., quarterly)
- ✅ Use Azure Key Vault for production deployments

## Troubleshooting

### Interactive Mode Issues

**Problem**: "Device code flow timeout"
```
Solution: Visit https://microsoft.com/devicelogin within 5 minutes and enter the displayed code
```

**Problem**: "Permission denied" errors
```
Solution: You may not have Fabric permissions. Ask your admin to grant you access to Fabric workspaces.
```

**Problem**: "Token cache corrupted"
```
Solution: Delete ~/.fabric_mcp_token_cache.json and authenticate again
rm ~/.fabric_mcp_token_cache.json
```

### Service Principal Mode Issues

**Problem**: "Invalid client secret"
```
Solution: Check that FABRIC_CLIENT_SECRET in .env is correct (no extra spaces)
```

**Problem**: "Invalid tenant ID"
```
Solution: Verify FABRIC_TENANT_ID matches your Azure AD tenant (format: UUID or domain name)
```

**Problem**: "Insufficient permissions"
```
Solution: Azure AD app needs Fabric/Power BI permissions. Ask your admin to grant:
- Fabric.Read.All or Power BI API permissions
```

### Switching Between Modes

**Interactive → Service Principal**:
1. Create service principal in Azure AD
2. Edit `.env` and set `FABRIC_CLIENT_SECRET`
3. Restart MCP server
4. Old token cache is ignored

**Service Principal → Interactive**:
1. Edit `.env` and comment out `FABRIC_CLIENT_SECRET`
2. Restart MCP server
3. Device code flow prompt appears on first request

## Future Enhancements

### Scope Refinement

Current implementation uses `.default` scope for simplicity. Future versions could:
- Request specific scopes (e.g., `Workspace.Read.All`, `Item.Read.All`) for better security
- Implement scope negotiation for different operation types
- Support custom scope configuration

### Token Caching for Service Principals

Current implementation acquires new token on every request. Future versions could:
- Implement optional token caching for service principals (with TTL)
- Reduce Azure AD API calls and improve performance
- Add cache expiration and refresh logic

### Managed Identity Support

For Azure-hosted deployments:
- Support Azure Managed Identity authentication
- Eliminate need to store credentials
- Better integration with Azure Key Vault and other Azure services

## References

- [Microsoft Fabric REST API Documentation](https://learn.microsoft.com/en-us/fabric/api/)
- [Azure AD Device Code Flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)
- [MSAL for Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Power BI API Scopes](https://learn.microsoft.com/en-us/power-bi/developer/embedded/power-bi-embedded-rbac)
