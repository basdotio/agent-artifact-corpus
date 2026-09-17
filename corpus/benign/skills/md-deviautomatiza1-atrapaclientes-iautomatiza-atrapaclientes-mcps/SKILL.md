---
name: atrapaclientes-mcps
description: MCPs configured for Atrapaclientes development - SSH, PostgreSQL Production DB, gh_grep
license: MIT
compatibility: opencode
metadata:
  audience: developers
  project: atrapaclientes
  mcp-version: "1.0"
  production-db: "true"
---

## ✅ Available MCPs for Atrapaclientes

### 🟢 ENABLED (Always Available)

#### **1. SSH MCP** ⭐⭐⭐⭐⭐
- **Purpose:** Direct access to production VPS (195.78.230.159)
- **SSH Key:** `~/.ssh/atrapaclientes`
- **User:** fansmar

**Common tasks:**
```bash
# Check API logs
docker logs -f --tail 200 atrapaclientes-api-1

# Health check
curl https://api.atrapaclientes.es/api/health

# Check migrations ran
SELECT * FROM migrations ORDER BY id DESC LIMIT 5;

# Restart API
docker restart atrapaclientes-api-1

# Update repository and redeploy
cd ~/atrapaclientes && git pull origin main && \
docker compose -f docker-compose.prod.yml down && \
docker compose -f docker-compose.prod.yml build --no-cache && \
docker compose -f docker-compose.prod.yml up -d
```

#### **2. PostgreSQL MCP** ⭐⭐⭐⭐⭐
- **Purpose:** Query production database directly via SSH tunnel
- **Host:** 195.78.230.159 (via SSH)
- **Database:** atrapaclientes
- **User:** postgres

**⚠️ IMPORTANT - Setup SSH Tunnel First!**

Before using PostgreSQL MCP, create an SSH tunnel in PowerShell:
```powershell
ssh -i $env:USERPROFILE\.ssh\atrapaclientes -L 5432:localhost:5432 fansmar@195.78.230.159
```

This forwards port 5432 through SSH, then PostgreSQL MCP can connect locally.

**Common queries:**
```sql
-- Check multi-tenant isolation
SELECT DISTINCT tenant_id, COUNT(*) FROM participantes GROUP BY tenant_id;

-- View recent participations
SELECT id, email, created_at FROM participantes ORDER BY created_at DESC LIMIT 10;

-- Check premio stock
SELECT nombre, stock, entregados FROM premios WHERE stock > 0;

-- Verify migrations
SELECT id, migration, timestamp FROM migrations ORDER BY id DESC;

-- Check campaign status
SELECT id, nombre, estado, fecha_inicio, fecha_fin FROM campanas;

-- Audit log search
SELECT user_id, action, entity_type, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 20;
```

#### **3. Grep by Vercel (GitHub Code Search)** ⭐⭐⭐⭐
- **Purpose:** Find code patterns in GitHub repositories
- **Use case:** Learn from other implementations, find examples

**Example prompts:**
```
Find examples of multi-tenant architecture in NestJS using gh_grep

Show me how to implement JWT refresh tokens with Axios interceptors use gh_grep

Find React Query examples for form submission with optimistic updates
```

---

### 🟡 DISABLED (Available but disabled)

#### **4. Docker MCP** (Currently disabled)
```json
"docker": {
  "enabled": false  // Change to true to enable
}
```

**When to enable:**
- Debugging container issues
- Inspecting volumes, networks
- Health checks

---

## 🚀 Quick Start Guide

### Step 1: Create SSH Tunnel (in PowerShell)
```powershell
ssh -i $env:USERPROFILE\.ssh\atrapaclientes -L 5432:localhost:5432 fansmar@195.78.230.159
```

**Keep this running while using PostgreSQL MCP!**

### Step 2: Query Production Database
```
Show me the last 10 participantes in the database

How many campaigns are currently active?

Query the audit log for recent changes

Check the migrations table
```

### Step 3: Debug Production Issues
```
Use SSH to check if API is healthy

Show recent container logs from production

Can you restart the API container?
```

---

## 📊 Database Connection Info

```
Host:       195.78.230.159
Port:       5432
User:       postgres
Password:   YG5uVh3mK9pQwX2jL8sRtZ6b
Database:   atrapaclientes
SSH User:   fansmar
SSH Host:   195.78.230.159
SSH Key:    ~/.ssh/atrapaclientes
```

---

## 🔧 MCP Configuration Reference

| MCP | Status | Type | Purpose |
|-----|--------|------|---------|
| SSH | ✅ Enabled | Local | Production VPS access |
| PostgreSQL | ✅ Enabled | Local | Production DB queries (via SSH tunnel) |
| gh_grep | ✅ Enabled | Remote | GitHub code search |
| Docker | 🟡 Disabled | Local | Container management |

---

## ⚠️ Important Notes

1. **SSH Tunnel Required:** PostgreSQL MCP needs an active SSH tunnel on port 5432
2. **Keep it Running:** The tunnel must stay open while querying the database
3. **Security:** Credentials are stored securely; SSH key is password-protected
4. **Read/Write Access:** You have full access to the production database
5. **Audit Log:** All changes to production are logged in `audit_logs` table

---

## 💡 Common Use Cases

**Debugging participations issue:**
```
Query the database: SELECT * FROM participaciones WHERE tenant_id = 'xxx' ORDER BY created_at DESC LIMIT 10

Check if a participant exists: SELECT * FROM participantes WHERE email = 'user@example.com'
```

**Verify deployment:**
```
Check migrations: SELECT * FROM migrations ORDER BY id DESC LIMIT 5

Verify campaign is published: SELECT * FROM campanas WHERE id = 'campaign-id'
```

**Production debugging:**
```
SSH into server and check API health

View error logs: docker logs -f --tail 500 atrapaclientes-api-1

Check database connections: SELECT * FROM pg_stat_activity;
```

---

## 🛠️ Troubleshooting

**PostgreSQL MCP says "Connection refused"?**
- Verify SSH tunnel is running: `ssh -i ... -L 5432:localhost:5432 fansmar@195.78.230.159`
- Keep the tunnel open in a separate PowerShell window

**SSH MCP not connecting?**
- Verify SSH key exists: `Test-Path ~\.ssh\atrapaclientes`
- Verify permissions: `ls -la ~/.ssh/atrapaclientes`
- Test connection: `ssh -i ~/.ssh/atrapaclientes fansmar@195.78.230.159 "echo OK"`

**Can't query specific table?**
- Verify table exists: `SELECT * FROM information_schema.tables WHERE table_schema='public';`
- Check permissions: `SELECT * FROM pg_roles WHERE rolname='postgres';`

---

## 🚀 Next Steps

1. **Setup SSH tunnel:**
   ```powershell
   ssh -i $env:USERPROFILE\.ssh\atrapaclientes -L 5432:localhost:5432 fansmar@195.78.230.159
   ```

2. **Test connection:**
   ```
   Query the production database: SELECT COUNT(*) FROM participantes;
   ```

3. **Monitor production:**
   ```
   Check API logs: docker logs -f --tail 200 atrapaclientes-api-1
   ```

4. **Search code patterns:**
   ```
   Use gh_grep to find NestJS multi-tenant examples
   ```

