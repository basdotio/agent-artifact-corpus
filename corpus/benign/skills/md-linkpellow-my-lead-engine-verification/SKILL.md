---
name: verification
description: Mandatory deployment verification protocol with real-time log monitoring
---

# Mandatory Deployment & Real-time Validation Protocol

## 🎯 Objective

Verify deployments immediately using active log streaming. No sleep delays - monitor in real-time until success signatures appear.

---

## 📋 Protocol Steps

### 1. Execute Deployment
```bash
railway up --service scrapegoat-worker-swarm --detach
```

### 2. Immediate Active Monitoring (No Sleep)
**DO NOT SLEEP.** Start log streaming immediately:
```bash
railway logs --service scrapegoat-worker-swarm --tail 100 -f
```

### 3. Monitor for Exact Success Signatures

**Required Signatures (All Must Appear):**
- ✅ `✅ Connected to PostgreSQL Persistence Layer`
- ✅ `✅ Isomorphic Intelligence Injected: [selectorParser, cssParser, locatorGenerators]`
- ✅ `✅ CreepJS Trust Score: 100.0% - HUMAN`

**Alternative Patterns:**
- `PostgreSQL Persistence Layer` (partial match)
- `Isomorphic Intelligence` (partial match)
- `Trust Score.*100\.0.*HUMAN` (regex pattern)

---

## ✅ Exit Condition

**Exit the tail once ALL signatures appear:**
- ✅ PostgreSQL connection confirmed
- ✅ Isomorphic intelligence injected
- ✅ 100% Human trust score achieved

**Then confirm:** "Phase 3 is LIVE" (or appropriate phase number)

---

## 🚨 Critical Rules

1. **No Sleep Delays:** Use `-f` flag for real-time streaming
2. **Exact Signatures:** Monitor for exact log messages (case-sensitive)
3. **All Signatures Required:** Do not exit until all three appear
4. **Immediate Action:** Start monitoring immediately after deployment command

---

## 📝 Usage Example

```bash
# Step 1: Deploy
railway up --service scrapegoat-worker-swarm --detach

# Step 2: Monitor (no sleep)
railway logs --service scrapegoat-worker-swarm --tail 100 -f | \
  grep --line-buffered -E "(PostgreSQL Persistence|Isomorphic Intelligence|Trust Score.*100\.0.*HUMAN)"

# Step 3: Exit when all signatures appear
# Confirm: "Phase 3 is LIVE"
```

---

## 🎯 Success Criteria

**Deployment is verified when:**
- ✅ All three success signatures appear in logs
- ✅ No errors or warnings in deployment sequence
- ✅ Worker continues running (not exited)

**If signatures don't appear:**
- ❌ Check build logs for errors
- ❌ Verify environment variables are set
- ❌ Check service health in Railway Dashboard
