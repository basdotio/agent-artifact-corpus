---
name: 1password
description: Manage personal secrets and passwords using 1Password CLI (op). Use when the user asks to query, retrieve, create, or manage secrets in 1Password, 1p, or op. This is for personal secrets only - not for cloud provider secret managers like Azure Key Vault, AWS Secrets Manager, or GCP Secret Manager.
---

# 1Password CLI

Manage personal secrets and passwords using the 1Password CLI (`op`).

## CRITICAL RULES

1. **Tag Filter**: Only read secrets that have the `agents` tag. Use `--tags agents` on `op item list` to filter by tag. Do NOT use `--tags` on `op item get` — it is not a valid flag there and will cause an error.
2. **Confirmation Required**: Always confirm with the user before creating or modifying secrets. No confirmation is needed for reading secrets.

## Prerequisites

Before using any `op` commands, ensure:

1. 1Password CLI is installed (`op --version`)
2. Desktop app integration is enabled (Settings > Developer > Integrate with 1Password CLI)
3. User is signed in — verify with `op whoami` before attempting any operation

## Common Operations

### List Items

List items tagged for agent access:

```bash
op item list --tags agents
```

List items by category:

```bash
op item list --tags agents --categories Login
op item list --tags agents --categories Password
op item list --tags agents --categories "API Credential"
```

List items in a specific vault:

```bash
op item list --tags agents --vault Personal
```

### Get Item Details

Get full details for an item:

```bash
op item get "Item Name"
```

Get specific fields:

```bash
op item get "GitHub Token" --fields label=username,label=password
```

Get in JSON format:

```bash
op item get "API Key" --format json
```

Get one-time password (OTP):

```bash
op item get "Google" --otp
```

### Read Secret Values

Use `op read` with secret references for direct value retrieval:

```bash
op read "op://Personal/GitHub Token/password"
op read "op://Personal/API Key/credential"
```

Secret reference format:

```text
op://vault-name/item-name/[section-name/]field-name
```

### Create Items

**ALWAYS confirm with user before creating items.**

Create a Login item:

```bash
op item create --category=login \
  --title='Service Name' \
  --vault='Personal' \
  --url='https://example.com' \
  --tags='agents' \
  username='user@example.com' \
  password='secure-password'
```

Create an API Credential:

```bash
op item create --category="API Credential" \
  --title='Service API' \
  --vault='Personal' \
  --tags='agents' \
  credential='api-key-value'
```

Create a Password item:

```bash
op item create --category=password \
  --title='Database Password' \
  --vault='Personal' \
  --tags='agents' \
  password='secure-password'
```

Create with auto-generated password:

```bash
op item create --category=login \
  --title='New Service' \
  --vault='Personal' \
  --tags='agents' \
  --url='https://example.com' \
  --generate-password='letters,digits,symbols,32' \
  username='user@example.com'
```

### Edit Items

**ALWAYS confirm with user before editing items.**

Edit a field value:

```bash
op item edit 'Service Name' 'password=new-password'
```

Add or update tags (preserving the `agents` tag):

```bash
op item edit 'Service Name' --tags='agents,production,api'
```

Generate new password:

```bash
op item edit 'Service Name' --generate-password='letters,digits,symbols,32'
```

### Delete Items

**ALWAYS confirm with user before deleting items.**

Delete an item:

```bash
op item delete "Old Service"
```

Archive instead of delete:

```bash
op item delete "Old Service" --archive
```

## Output Formats

Human-readable (default):

```bash
op item get "Service Name"
```

JSON format (for parsing):

```bash
op item get "Service Name" --format json
```

Parse with jq:

```bash
op item get "Service Name" --format json | jq '.fields[] | select(.label=="password") | .value'
```

## Common Patterns

### Find all agent-accessible secrets

```bash
op item list --tags agents --format json | jq -r '.[] | "\(.title) (\(.vault.name))"'
```

### Get password for a service

When `--fields` returns a single field, the result is a plain string object (not an array) — use `.value` directly:

```bash
op item get "Service Name" --fields label=password --format json | jq -r '.value'
```

When requesting multiple fields, the result is an array — use `.fields[]`:

```bash
op item get "Service Name" --fields label=username,label=password --format json | jq -r '.fields[] | select(.label=="password") | .value'
```

### Check if an item exists

```bash
op item get "Service Name" --format json &>/dev/null && echo "exists" || echo "not found"
```

### List all API credentials for agents

```bash
op item list --tags agents --categories "API Credential"
```

## Categories

Available item categories:

- API Credential
- Bank Account
- Credit Card
- Database
- Document
- Driver License
- Email Account
- Identity
- Login
- Membership
- Outdoor License
- Passport
- Password
- Reward Program
- Secure Note
- Server
- Social Security Number
- Software License
- Wireless Router

## Error Handling

### Checking Authentication State

Always verify authentication before attempting operations:

```bash
op whoami
```

If this fails, sign in:

```bash
op signin
```

### WSL2 / Non-TTY Environments

In WSL2, the 1Password CLI integrates with the Windows desktop app. You must enable this in the **Windows** 1Password app:

> Settings → Developer → **Integrate with 1Password CLI** (check the box)

The same setting exists on macOS:

> Settings → Developer → **Integrate with 1Password CLI**

In non-TTY contexts (CI, scripts, subprocesses), `op signin` cannot prompt for a password interactively and will silently fail. Diagnose with:

```bash
# Check if the socket/agent is available
op whoami 2>&1

# If you see: "[ERROR] 2026/... error dialing: no such file or directory"
# the desktop app integration is not running or not enabled.

# If you see: "[ERROR] ... not currently signed in"
# trigger sign-in from an interactive terminal first, then retry.
```

For automated/non-TTY use, prefer a service account token (`OP_SERVICE_ACCOUNT_TOKEN`) or a pre-authenticated session token (`OP_SESSION_<account>`).

### Item Not Found

If an item is not found, verify:

1. Item exists in 1Password
2. Item has the `agents` tag
3. Correct vault is accessible
4. User is properly authenticated (`op whoami`)

## Best Practices

1. **Always use the `agents` tag** for items intended for agent access
2. **Confirm destructive operations** (create, edit, delete) with user
3. **Use secret references** (`op://...`) when injecting secrets into commands
4. **Prefer JSON format** when parsing output programmatically
5. **Use item IDs** instead of names for more reliable references
6. **Specify vault** when dealing with multiple vaults to avoid ambiguity
