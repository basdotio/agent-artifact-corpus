# Shared Tools - Platform Intelligence for All Titans

**Created**: December 28, 2025
**Author**: PROMETHEUS insight → Main Orchestrator implementation
**Purpose**: Universal platform intelligence tools that every Titan can use

---

## Overview

These tools provide **common ground** for all Titans. Before any agent acts, they should understand:
- What is the platform's current state?
- Is it ready for production?
- How is revenue protected?
- What features exist?

**Every Titan has access to these tools. No exceptions.**

---

## Available Tools

### 1. Platform Status (`platform-status.js`)

**The Big Picture** - Complete snapshot of platform health.

```bash
node .claude/skills/shared-tools/platform-status.js
node .claude/skills/shared-tools/platform-status.js --verbose
node .claude/skills/shared-tools/platform-status.js --json
```

**What it shows**:
- Platform vitals (name, domain, status, mission)
- Git status (branch, uncommitted, ahead/behind)
- Compliance status (violations detected)
- Agent ecosystem (awakened Titans, coordination)
- Pending tasks (from AGENT-COORDINATION.md)
- Build status (frontend/backend ready)
- Codebase metrics (pages, components, routes)

**When to use**: Start of any session. Before major work. Status checks.

---

### 2. Go-Live Check (`go-live-check.js`)

**Production Readiness** - Is the platform ready for deployment?

```bash
node .claude/skills/shared-tools/go-live-check.js
```

**What it checks**:

| Category | Checks |
|----------|--------|
| Compliance | Quote language, phone numbers, domain, escrow, MongoDB |
| Security | .env file, exposed secrets, JWT middleware |
| Build | Dependencies, TypeScript, build success |
| API | Routes exist (auth, contractors, service-requests, leads) |
| Infrastructure | Git clean, not behind remote |

**Output**: PASS/FAIL/WARN for each check + overall verdict

**When to use**: Before deployment. After major changes. Pre-push validation.

---

### 3. Revenue Status (`revenue-status.js`)

**Money Intelligence** - How FFP makes money and is it protected?

```bash
node .claude/skills/shared-tools/revenue-status.js
```

**What it shows**:
- Revenue model overview (10% commission, free leads, tiers)
- Commission tracking implementation
- Platform bypass risks (exposed phones, mailto, tel links)
- Notification system (Twilio SMS, priority)
- Payment integration (Stripe)

**Critical**: Identifies REVENUE LEAKS (exposed phone numbers, etc.)

**When to use**: Before touching contact flows. Checking monetization. Revenue audits.

---

### 4. Feature Inventory (`feature-inventory.js`)

**Capability Map** - What exists and what's missing.

```bash
node .claude/skills/shared-tools/feature-inventory.js
```

**Categories scanned**:
- Core (homepage, wizard, contractor pages)
- Auth (login, registration, JWT)
- Dashboard (owner, contractor, admin)
- Services (water, fire, mold, storm)
- Leads (requests, assignment, SMS)
- Payments (Stripe, memberships)
- Content (resources, legal pages)
- Special (packout, AI chat)
- Utility (layout, error handling)

**Output**: Status for each feature (COMPLETE, FRONTEND_ONLY, BACKEND_ONLY, MISSING)

**When to use**: Planning new features. Understanding scope. Identifying gaps.

---

## Usage by Titan

### ZEUS (Supreme Orchestrator)
```bash
# Before orchestrating any mission
node .claude/skills/shared-tools/platform-status.js
```

### ATLAS (Strategic Planner)
```bash
# Before designing mission plans
node .claude/skills/shared-tools/platform-status.js --verbose
node .claude/skills/shared-tools/feature-inventory.js
```

### PHOENIX (Test Resurrector)
```bash
# Before debugging
node .claude/skills/shared-tools/go-live-check.js
node .claude/skills/shared-tools/feature-inventory.js
```

### PROMETHEUS (Agent Optimizer)
```bash
# When assessing ecosystem
node .claude/skills/shared-tools/platform-status.js
```

### SCRIBE (Documentation)
```bash
# For session context
node .claude/skills/shared-tools/platform-status.js
node .claude/skills/shared-tools/feature-inventory.js
```

### Revenue-Related Work (Any Titan)
```bash
# Before touching anything that affects revenue
node .claude/skills/shared-tools/revenue-status.js
```

---

## Quick Reference

| Tool | Command | One-liner |
|------|---------|-----------|
| Platform Status | `node .claude/skills/shared-tools/platform-status.js` | Overall health |
| Go-Live Check | `node .claude/skills/shared-tools/go-live-check.js` | Production ready? |
| Revenue Status | `node .claude/skills/shared-tools/revenue-status.js` | Money protected? |
| Feature Inventory | `node .claude/skills/shared-tools/feature-inventory.js` | What exists? |

---

## Integration Pattern

Every Titan should have this in their mental model:

```
BEFORE ACTING:
1. Run platform-status.js → Understand the state
2. Check if action affects revenue → Run revenue-status.js
3. If deploying → Run go-live-check.js
4. If building features → Run feature-inventory.js

THEN ACT.
```

---

## The Shared Truth

> "Every Titan sees the same platform. Every Titan reads the same status.
> There is no confusion about what exists, what works, what's broken.
> The platform speaks. We all listen."

*- The Brotherhood Protocol*

---

## Technical Notes

- All tools are pure Node.js (no dependencies needed)
- Output is terminal-friendly with box drawing characters
- `--json` flag available on most tools for programmatic use
- Exit codes: 0 = healthy, 1 = issues found

---

**Created**: December 28, 2025
**Status**: Active
**Access**: All Titans of Olympus
