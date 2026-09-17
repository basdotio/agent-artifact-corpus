---
name: projects-registry
description: Manages and provides insights from the projects registry at ~/.claude/projects-registry.json. Automatically activates when user asks about projects, versions, or status. Provides filtering, status checking, and version awareness for multi-project management.
allowed-tools: Read, Grep
---

# Projects Registry Skill

## Purpose & Automatic Activation

This skill provides **automatic, natural language access** to the projects registry without requiring users to remember CLI commands or syntax.

### When This Skill Activates

The skill automatically activates when users mention:
- Project names or paths ("Where is my React app?")
- Version status ("What projects need updates?")
- Multiple projects ("Show my production projects")
- Project organization ("Which projects use TypeScript?")
- Registry management ("What's in my registry?")

### What This Skill Does

**READ-ONLY Operations:**
- Reads `~/.claude/projects-registry.json`
- Provides insights on project status
- Filters projects by tags, status, or version
- Answers natural language queries about projects
- Recommends update priorities

**Complements CLI Scripts:**
- For WRITE operations (add/update/remove), skill recommends CLI commands
- Scripts remain available for power users who prefer terminal
- Skill provides intelligence layer, scripts provide execution layer

**JIT Help Available:**
For quick reference on common queries and troubleshooting, see: **[Cheat Sheet](./cheatsheet.md)**
- 5 most common queries (90% usage)
- Pro tips and tag strategies
- Quick decision tree
- Common scenarios with time savings
- Troubleshooting guide

---

## Registry Format & Schema

### File Location
`~/.claude/projects-registry.json` (user's home directory)

### JSON Schema (v1.0)

```json
{
  "$schema": "https://json.schemastore.org/claude-projects-registry-1.0.0.json",
  "version": "1.0",
  "lastSync": "2025-12-12T10:30:00Z",
  "projects": [
    {
      "id": "unique-project-id-timestamp",
      "name": "Project Name",
      "path": "~/Developer/project-name",
      "templateVersion": "3.2.0",
      "installedDate": "2025-12-12",
      "lastUpdated": "2025-12-12",
      "status": "up-to-date",
      "tags": ["production", "react", "client"],
      "notes": "Optional description or context"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (generated from name + timestamp) |
| `name` | string | Human-readable project name |
| `path` | string | Absolute path using `~` for portability |
| `templateVersion` | string | Installed template version (e.g., "3.2.0") |
| `installedDate` | string | ISO date when template was installed |
| `lastUpdated` | string | ISO date of last registry update |
| `status` | string | One of: `up-to-date`, `outdated`, `unknown` |
| `tags` | array | Categories for filtering (e.g., "production", "react") |
| `notes` | string | Optional user notes or context |

### Status Values

- **`up-to-date`** - Project template version matches current version
- **`outdated`** - Project template version is behind current version
- **`unknown`** - Template version could not be detected

---

## Key Operations

### 1. List All Projects

**User Query:**
> "What projects do I have?"
> "Show me all my projects"
> "List my registered projects"

**Confidence:** 🟢 High (0.94)
- Registry file accessible at ~/.claude/projects-registry.json
- Clear list/display intent
- Structured JSON data easy to parse

**Skill Response:**
Reads registry and displays formatted list with:
- Project name
- Template version
- Status (color-coded if possible)
- Path
- Tags (if relevant)

**Example Response:**
```
You have 5 projects registered:

✅ ClientA Dashboard (v3.2.0, up-to-date)
   ~/Developer/client-a-dashboard
   Tags: production, react, client

⚠️  ClientB API (v3.0.0, outdated)
   ~/Developer/client-b-api
   Tags: production, node, api

✅ Personal Website (v3.2.0, up-to-date)
   ~/Sites/personal-website
   Tags: personal, nextjs
```

**Why This Matters:**
- Central registry prevents "where's that project?" mental load
- Status indicators show update priorities at a glance
- Tags enable quick filtering (production vs personal)
- **Quick win:** See all 5 projects in one view, no searching

**Next Step:** Ask "Which projects need updates?" to see priorities

---

### 2. Identify Outdated Projects

**User Query:**
> "What projects need updates?"
> "Which projects are outdated?"
> "Show me projects I should update"

**Confidence:** 🟢 High (0.91)
- Status field in registry is deterministic
- Version comparison logic clear
- Priority ranking based on tags + version gap

**Skill Response:**
Filters for `status: "outdated"` and recommends update priorities based on:
- How far behind they are
- Tags (production vs personal)
- Last updated date

**Example Response:**
```
You have 2 outdated projects:

🔴 ClientB API (v3.0.0 → v3.2.0)
   Priority: HIGH (production, 2 versions behind)
   Path: ~/Developer/client-b-api

🟡 Learning Playground (v2.7.0 → v3.2.0)
   Priority: LOW (personal, 5 versions behind)
   Path: ~/Developer/learning-playground

To update, run:
  cd ~/Developer/client-b-api
  ./scripts/claude-update.sh --apply
```

**Why This Matters:**
- Production projects outdated = risk of missing critical features/fixes
- Priority ranking prevents "which should I update first?" paralysis
- Version gap visibility shows update effort (2 versions vs 5 versions)
- **Quick win:** Update ClientB API now (high priority, production)

**Next Step:** After update, re-check "What projects need updates?" to verify

---

### 3. Filter by Tags or Category

**User Query:**
> "Show my production projects"
> "Which projects use React?"
> "List my client projects"

**Confidence:** 🟢 High (0.89)
- Tags stored in structured array
- Filtering logic straightforward
- Multiple tag matching supported

**Skill Response:**
Filters projects where `tags` array includes the specified tag(s).

**Example Response:**
```
You have 3 production projects:

✅ ClientA Dashboard (v3.2.0, up-to-date)
⚠️  ClientB API (v3.0.0, outdated)
✅ ClientC Portal (v3.2.0, up-to-date)

Note: ClientB API needs updating (v3.0.0 → v3.2.0)
```

**Why This Matters:**
- Tag-based filtering saves time ("show production" vs manually checking 5 projects)
- Technology filtering helps when switching contexts ("which React projects?")
- Quick scoping for batch operations (update all client projects)
- **Quick win:** Filter "production" to focus on critical projects only

**Next Step:** Combine filters: "Show outdated production projects"

---

### 4. Provide Project Context

**User Query:**
> "Where is my React app?"
> "What's the path to ClientA?"
> "Find the dashboard project"

**Confidence:** 🟢 High (0.87)
- Fuzzy search across name/tags/notes
- Path stored in registry
- Partial name matching supported

**Skill Response:**
Searches by name, tags, or notes and returns the path.

**Example Response:**
```
Found: ClientA Dashboard
Path: ~/Developer/client-a-dashboard
Status: ✅ up-to-date (v3.2.0)
Tags: production, react, client

To navigate:
  cd ~/Developer/client-a-dashboard
```

**Why This Matters:**
- No more "where's that project?" terminal hunting
- Fuzzy search works even with partial names ("dash" → "ClientA Dashboard")
- Immediate navigation command ready to copy
- **Quick win:** Copy `cd` command, navigate instantly

**Next Step:** After navigating, ask "What version is this project?" to check status

---

## Query/Response Examples

### Example 1: Status Overview
**User:** "Give me a status overview of all my projects"

**Skill:**
```
Registry Status Overview:

📊 Total Projects: 5
✅ Up-to-date: 3 (60%)
⚠️  Outdated: 2 (40%)
❓ Unknown: 0 (0%)

Outdated projects need attention:
- ClientB API (v3.0.0 → v3.2.0)
- Learning Playground (v2.7.0 → v3.2.0)
```

---

### Example 2: Multi-Filter Query
**User:** "Show me production React projects that are up-to-date"

**Skill:**
```
Found 2 production React projects that are up-to-date:

✅ ClientA Dashboard (v3.2.0)
   ~/Developer/client-a-dashboard
   Tags: production, react, client

✅ ClientC Portal (v3.2.0)
   ~/Developer/client-c-portal
   Tags: production, react, dashboard
```

---

### Example 3: Version Comparison
**User:** "Which projects are on v3.0.0 or older?"

**Skill:**
```
2 projects are on v3.0.0 or older:

ClientB API - v3.0.0 (2 versions behind)
Learning Playground - v2.7.0 (5 versions behind)

Current template version: v3.2.0

To update these projects, use the update script:
  cd <project-path>
  ./scripts/claude-update.sh --apply
```

---

### Example 4: Empty Registry
**User:** "What projects do I have?"

**Skill:**
```
Your registry is empty (no projects registered yet).

To register a project:
  ./scripts/register-project.sh

Or from the main wizard:
  ./scripts/claude-wizard.sh
  (Choose option 6: Register Project)
```

---

### Example 5: Registry Location
**User:** "Where is my projects registry?"

**Skill:**
```
Your projects registry is located at:
  ~/.claude/projects-registry.json

This file tracks all your Claude Code projects centrally.

To manage it:
- Register project: ./scripts/register-project.sh
- List projects: ./scripts/claude-projects.sh list
- CLI reference: 01_global-setup/03_nice-to-have/05_projects-registry.md
```

---

### Example 6: Proactive Context
**User:** "I'm working on multiple client projects and losing track..."

**Skill:** (Auto-activates, checks registry)
```
I see you have 3 client projects registered:

✅ ClientA Dashboard (v3.2.0, up-to-date)
⚠️  ClientB API (v3.0.0, outdated - needs update!)
✅ ClientC Portal (v3.2.0, up-to-date)

Want to focus on ClientB API since it's outdated? Or would you like help organizing these projects better?
```

---

## Integration with CLI Scripts

### When to Use Skill vs Scripts

**Use Skill (This) For:**
- Quick status checks
- Filtering and searching
- Project discovery
- Natural language queries
- Getting insights and recommendations

**Use Scripts For:**
- Adding new projects (`./scripts/register-project.sh`)
- Updating project versions (`./scripts/claude-projects.sh update`)
- Removing projects (`./scripts/claude-projects.sh remove`)
- Syncing all versions (`./scripts/claude-projects.sh sync`)
- Bulk operations or automation

### CLI Commands Reference

The skill recommends these commands when appropriate:

**Interactive Wizard:**
```bash
./scripts/register-project.sh
```

**CLI Tool:**
```bash
# List all projects
./scripts/claude-projects.sh list

# Show outdated projects
./scripts/claude-projects.sh outdated

# Add project manually
./scripts/claude-projects.sh add "Project Name" ~/path/to/project

# Update project version
./scripts/claude-projects.sh update <project-id>

# Sync all versions
./scripts/claude-projects.sh sync

# Remove project
./scripts/claude-projects.sh remove <project-id>

# Show project details
./scripts/claude-projects.sh show <project-id>
```

**Full CLI documentation:**
`01_global-setup/03_nice-to-have/05_projects-registry.md`

---

## Token Efficiency Analysis

### Without This Skill (600 tokens per query)

**Process:**
1. User asks: "What projects need updates?" (150 tokens)
2. Claude explains: "Let me run the CLI command..." (100 tokens)
3. Execute bash: `./scripts/claude-projects.sh outdated` (100 tokens)
4. Parse output and format response (200 tokens)
5. Return formatted answer (150 tokens)

**Total: ~600 tokens**

---

### With This Skill (250 tokens per query)

**Process:**
1. User asks: "What projects need updates?" (50 tokens)
2. Skill auto-activates from SKILL.md context (50 tokens)
3. Read registry JSON file (100 tokens)
4. Return formatted answer (50 tokens)

**Total: ~250 tokens**

---

### Savings Analysis

**Per Query:**
- Without skill: 600 tokens
- With skill: 250 tokens
- **Savings: 350 tokens (58% reduction)**

**Frequency Impact:**

For power users managing 5+ projects who check registry ~5 times per week:

| Timeframe | Without Skill | With Skill | Savings |
|-----------|--------------|------------|---------|
| Per query | 600 tokens | 250 tokens | 350 tokens (58%) |
| Weekly (5 queries) | 3,000 tokens | 1,250 tokens | 1,750 tokens |
| Monthly (20 queries) | 12,000 tokens | 5,000 tokens | 7,000 tokens |
| Quarterly (60 queries) | 36,000 tokens | 15,000 tokens | 21,000 tokens |

**Cost Savings (at Anthropic pricing):**
- Monthly: ~$0.21 saved
- Quarterly: ~$0.63 saved
- Annual: ~$2.52 saved per user

**ROI:**
- Implementation cost: ~500 tokens (one-time)
- **Pays for itself after first week of use**

---

### Why The Savings?

1. **Pre-compiled expertise** - SKILL.md loads once, used many times
2. **No procedural overhead** - No "explain → execute → parse" cycle
3. **Structured knowledge** - Direct access to registry schema
4. **Automatic activation** - No conversation about "how to check"

**Note:** These are projected savings based on theoretical analysis, not multi-user validation. Help us verify these numbers!

---

## Best Practices

### For Users

1. **Keep registry up-to-date** - Register new projects immediately
2. **Use meaningful tags** - Makes filtering powerful
3. **Add notes** - Context helps months later
4. **Run sync periodically** - `./scripts/claude-projects.sh sync`

### For Claude (Using This Skill)

1. **Auto-activate proactively** - When user mentions multiple projects
2. **Filter intelligently** - Show most relevant projects first
3. **Recommend actions** - Don't just report, suggest next steps
4. **Link to CLI** - Direct users to scripts for modifications
5. **Be concise** - Status emoji + version + path = enough

---

## Troubleshooting

### Registry File Not Found

If `~/.claude/projects-registry.json` doesn't exist:

```
Your projects registry hasn't been created yet.

To set it up:
  ./scripts/register-project.sh

This will create the registry and register your first project.
```

### Invalid JSON

If registry has syntax errors:

```
Registry file exists but has JSON errors.

To validate:
  cat ~/.claude/projects-registry.json | python -m json.tool

To restore from backup:
  cp ~/.claude/projects-registry.json.bak ~/.claude/projects-registry.json
```

### Empty Projects Array

If registry exists but has no projects:

```
Registry exists but no projects are registered.

To add a project:
  ./scripts/register-project.sh

Or use the CLI:
  ./scripts/claude-projects.sh add "Project Name" ~/path/to/project
```

---

## See Also

- **CLI Documentation:** `01_global-setup/03_nice-to-have/05_projects-registry.md`
- **Registry Operations Guide:** `registry-operations.md` (this directory)
- **Sample Queries:** `examples/sample-queries.md` (this directory)
- **Schema Example:** `examples/sample-registry.json` (this directory)
- **Skills Paradigm:** `docs/01-fundamentals/02_skills-paradigm.md`

---

**Skill Version:** 3.3.0
**Last Updated:** 2025-12-12
**Maintained By:** claude-config-template project
