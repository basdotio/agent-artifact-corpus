---
name: bcc
description: "Bead Codebase Compiler - Constructs a graph-aware bead representation of any codebase for AI agent navigation. Like gcc compiles code, bcc compiles a codebase into a dependency-rich bead graph optimized for bv's 9 graph metrics (PageRank, betweenness, HITS, critical path, eigenvector, degree, density, cycles, topo sort). Triggers on: bcc, compile beads, bead graph, map codebase, /bcc."
---

# BCC - Bead Codebase Compiler

Compile any codebase into a richly-connected bead graph that maximizes the analytical power of `bv` (Beads Viewer). BCC is an autonomous agent skill that explores a repository, discovers its structure, identifies patterns, and progressively builds a bead graph where every node and edge is engineered to produce meaningful signals across all 9 of bv's graph-theoretic metrics.

---

## Empirically Validated (96 experiments on ShipperCRM)

These findings are backed by 96 automated experiments on a real 3,753-file TypeScript monorepo:

| Finding | Evidence |
|---------|----------|
| **Module-level granularity = 100/100** | 15-20 beads with 14-16 edges. File-level scores 70, directory scores 23. |
| **Wire deps is THE critical step** | Without dep wiring, any bead set scores 23/100 (only cycles=0 and topo=valid). |
| **Strict label taxonomy helps** | Strict labels score 100, no labels score 73. Labels help wire_deps find connections. |
| **Bridge beads are optional** | When wire_deps runs well, bridges provide 0 marginal improvement. |
| **Future work beads are safe** | 5-10 feature beads maintain 100. Tech debt beads can slightly reduce density (94.5). |
| **Target density: 0.03-0.07** | A-tier experiments averaged density=0.04 |
| **Target edge-per-node: 0.7-1.4** | A-tier averaged 0.93 edges per node |
| **Critical path sweet spot: 3-10** | A-tier averaged 6.4 |

---

## First Principles

### The Core Insight

The bv viewer computes 9 graph metrics. Each metric reveals something ONLY when the graph has the right structural properties. A flat list of files produces a graph with zero betweenness, zero PageRank differentiation, and no critical path. The art of BCC is constructing a graph whose TOPOLOGY encodes the real semantic structure of the codebase so that bv's algorithms surface genuinely useful intelligence.

### The Compilation Metaphor

| gcc | bcc |
|-----|-----|
| Source code -> AST -> IR -> Machine code | Codebase -> Discovery -> Bead Graph -> bv Intelligence |
| Optimizes for CPU execution | Optimizes for graph metric signal quality |
| Multiple passes (lexer, parser, optimizer) | Multiple phases (scan, analyze, connect, enrich) |
| Handles any language | Handles any codebase |

---

## Phase Architecture

BCC operates in 4 phases, each building on the previous. Phases can be re-entered as the graph grows.

### Phase 1: SCAN (Structural Skeleton)

**Goal:** Establish the hierarchical backbone of the codebase as parent-child beads.

**What to create:**
- One **epic** bead per top-level architectural boundary (e.g., `backend/`, `frontend/`, `packages/core/`)
- One **feature** bead per major module or domain within each boundary
- One **task** bead per significant file cluster (grouped by cohesion, NOT one-per-file)

**Bead creation commands:**
```bash
# Create the root architectural epic
bd create "Architecture: Backend Services" -t epic -p 1 --label architecture --label backend

# Create module-level features under the epic
bd create "Module: Authentication" -t feature -p 1 --label auth --label backend

# Create file-cluster tasks
bd create "Auth Controllers & Routes" -t task -p 2 --label auth --label controllers
```

**Dependency rules for Phase 1:**
- Use `parent-child` deps for containment (epic -> feature -> task)
- Do NOT add blocking deps yet - that comes in Phase 2

**What this enables in bv:**
- Tree View (`E`) becomes immediately useful
- Degree centrality begins to differentiate nodes
- Topo sort produces a valid traversal order

**Performance rule:** For repos with >200 files, group into clusters of 5-15 files per task bead. Never create 1:1 file-to-bead mappings - it destroys graph signal-to-noise ratio.

### Phase 2: ANALYZE (Dependency Wiring)

**Goal:** Add blocking dependencies that encode the REAL dependency flow of the codebase.

**Discovery methods:**
1. **Import analysis:** File A imports from File B -> A's bead `blocks` B's bead (A depends on B, so B blocks A)
2. **Interface/contract boundaries:** API definitions block their consumers
3. **Database schema:** Schema beads block all beads that read/write those tables
4. **Configuration:** Config/env beads block services that consume them
5. **Build dependencies:** Package.json / go.mod / requirements.txt encode real blocking deps

**Dependency creation:**
```bash
# B blocks A (A cannot function without B)
bd dep add <bead-A-id> <bead-B-id>
```

**What this enables in bv:**
- PageRank now differentiates foundational code from leaf code
- Betweenness identifies cross-cutting bridges (API contracts, shared utils)
- Critical path reveals the longest dependency chain
- Cycles detection catches circular import problems
- HITS separates Hubs (features aggregating deps) from Authorities (core libs)

**Key insight for maximizing betweenness:** Ensure the graph has at least 2-3 distinct clusters with bridge nodes between them. A codebase with frontend/backend/shared-libs should have shared-libs beads with high betweenness because they bridge the two clusters.

### Phase 3: CONNECT (Cross-Cutting Concerns)

**Goal:** Add `related` dependencies that encode non-blocking semantic relationships.

**Discovery methods:**
1. **Co-change frequency:** Files that change together in git history are related
2. **Naming conventions:** `UserService` <-> `UserController` <-> `UserModel` are related
3. **Test relationships:** Test files are related to their subjects
4. **Documentation:** Docs/specs are related to what they describe
5. **Error handling chains:** Error types related to their throw sites

**Relationship creation:**
```bash
# Related (non-blocking) dependency
bd dep add <bead-A-id> <bead-B-id> --type related
```

**What this enables in bv:**
- Eigenvector centrality becomes meaningful (connected to important neighbors)
- Graph density reaches the healthy 0.05-0.15 range
- Attention view can surface neglected areas

### Phase 4: ENRICH (Metadata & Future Work)

**Goal:** Add descriptions, design notes, acceptance criteria, and labels that make the graph navigable by agents AND humans.

**For each significant bead, update with:**
```bash
bd update <id> --description "Purpose: What this module does and why it exists.
Key files: list of primary files.
Public API: exported functions/classes.
Known issues: gotchas or technical debt."

bd update <id> --design "Architecture notes: How this fits into the larger system.
Data flow: What data enters and leaves this module.
Dependencies rationale: Why it depends on what it depends on."

bd update <id> --acceptance "An agent understands this module when it can:
1. Explain its purpose in one sentence
2. List its public API
3. Identify what would break if this module changed
4. Name its upstream and downstream dependencies"
```

**Label taxonomy (use consistently):**
- Domain labels: `auth`, `payments`, `users`, `api`, `database`, `frontend`, `backend`
- Layer labels: `controller`, `service`, `model`, `middleware`, `config`, `test`
- Quality labels: `tech-debt`, `fragile`, `well-tested`, `needs-refactor`
- Priority: Set P0 for foundational/core, P1 for important modules, P2 for standard, P3 for peripheral

---

## Formulas: Recursive Exploration Templates

BCC uses beads formulas (`.formula.toml` files) to create repeatable, recursive exploration workflows. Each formula is a molecule template that, when instantiated, creates a set of beads with dependency-driven execution order.

### Core Formula: `explore-module`

The fundamental recursive exploration formula. When an agent discovers a module worth investigating, it instantiates this formula as a molecule attached to the discovery bead.

```toml
# .beads/formulas/explore-module.formula.toml
formula = "explore-module"
type = "workflow"
phase = "liquid"
version = 1

[vars]
module_name = { description = "Name of the module to explore", required = true }
module_path = { description = "Filesystem path to the module", required = true }
depth = { description = "Exploration depth (shallow|medium|deep)", default = "medium" }

[[steps]]
id = "scan-structure"
title = "Scan {{module_name}} structure"
description = "List all files, identify sub-modules, count LOC, detect languages"
priority = 0

[[steps]]
id = "identify-public-api"
title = "Map {{module_name}} public API"
description = "Find all exported functions, classes, types, constants"
needs = ["scan-structure"]
priority = 0

[[steps]]
id = "trace-imports"
title = "Trace {{module_name}} import graph"
description = "Find all imports INTO and OUT OF this module. Create blocking deps."
needs = ["scan-structure"]
priority = 0

[[steps]]
id = "detect-patterns"
title = "Detect patterns in {{module_name}}"
description = "Identify design patterns, anti-patterns, tech debt signals"
needs = ["identify-public-api", "trace-imports"]
priority = 1

[[steps]]
id = "create-child-beads"
title = "Create child beads for {{module_name}} sub-components"
description = "For each significant sub-component, create a task bead. If any sub-component is complex enough (>5 files, >500 LOC), attach an explore-module formula to it (RECURSIVE)."
needs = ["detect-patterns"]
priority = 1

[[steps]]
id = "wire-dependencies"
title = "Wire {{module_name}} dependencies"
description = "Create blocking and related deps between child beads and external beads"
needs = ["create-child-beads"]
priority = 1

[[steps]]
id = "enrich-metadata"
title = "Enrich {{module_name}} bead metadata"
description = "Update the parent bead with description, design notes, acceptance criteria"
needs = ["wire-dependencies"]
priority = 2
```

### Formula: `analyze-api-boundary`

For cross-module API contracts that are critical bridge nodes.

```toml
# .beads/formulas/analyze-api-boundary.formula.toml
formula = "analyze-api-boundary"
type = "workflow"
phase = "liquid"
version = 1

[vars]
api_name = { description = "Name of the API boundary", required = true }
provider_bead = { description = "Bead ID of the provider module", required = true }
consumer_beads = { description = "Comma-separated bead IDs of consumers", required = true }

[[steps]]
id = "catalog-endpoints"
title = "Catalog {{api_name}} endpoints/interfaces"
description = "List all endpoints, function signatures, or interface methods"
priority = 0

[[steps]]
id = "map-consumers"
title = "Map {{api_name}} consumer usage"
description = "For each consumer, identify which endpoints they use"
needs = ["catalog-endpoints"]
priority = 0

[[steps]]
id = "assess-coupling"
title = "Assess {{api_name}} coupling strength"
description = "Rate coupling: loose (interface), medium (shared types), tight (impl details). Update bead labels."
needs = ["map-consumers"]
priority = 1

[[steps]]
id = "create-contract-bead"
title = "Create contract bead for {{api_name}}"
description = "Create a dedicated bead representing the API contract. Wire it as a blocker for all consumers and a dependency of the provider."
needs = ["assess-coupling"]
priority = 1
```

### Formula: `discover-and-dive`

The recursive discovery formula. When something interesting is found, this formula decides whether to go deeper.

```toml
# .beads/formulas/discover-and-dive.formula.toml
formula = "discover-and-dive"
type = "workflow"
phase = "vapor"
version = 1

[vars]
discovery = { description = "What was discovered", required = true }
source_bead = { description = "Bead ID where discovery originated", required = true }
significance = { description = "low|medium|high|critical", default = "medium" }

[[steps]]
id = "assess-significance"
title = "Assess significance of: {{discovery}}"
description = "Determine if this discovery warrants deeper investigation. Check: does it affect multiple modules? Is it on a critical path? Is it a potential bottleneck?"
priority = 0

[[steps]]
id = "create-discovery-bead"
title = "Create bead for: {{discovery}}"
description = "Create a new bead representing this discovery. Link it to {{source_bead}} with discovered-from dependency. Set priority based on {{significance}}."
needs = ["assess-significance"]
priority = 0

[[steps]]
id = "decide-recursion"
title = "Decide recursion depth for: {{discovery}}"
description = "If significance >= medium AND the discovery represents a module/system: instantiate explore-module formula on the new bead. If significance == critical: also instantiate analyze-api-boundary if it crosses module boundaries."
needs = ["create-discovery-bead"]
priority = 1
```

### Formula: `future-work-scaffold`

For mapping planned/desired work onto the existing graph.

```toml
# .beads/formulas/future-work-scaffold.formula.toml
formula = "future-work-scaffold"
type = "workflow"
phase = "liquid"
version = 1

[vars]
feature_name = { description = "Name of the planned feature", required = true }
affected_modules = { description = "Comma-separated module names that will be touched", required = true }

[[steps]]
id = "impact-analysis"
title = "Impact analysis for {{feature_name}}"
description = "Query bv --robot-insights. Identify which existing beads will be affected. Check PageRank and betweenness of affected beads to assess risk."
priority = 0

[[steps]]
id = "create-feature-epic"
title = "Create epic for {{feature_name}}"
description = "Create an epic bead with P1 priority. Label with affected domain labels."
needs = ["impact-analysis"]
priority = 0

[[steps]]
id = "decompose-tasks"
title = "Decompose {{feature_name}} into tasks"
description = "For each affected module, create a task bead as child of the epic. Wire blocking deps based on the order work must happen (respecting existing graph topology)."
needs = ["create-feature-epic"]
priority = 1

[[steps]]
id = "wire-to-existing"
title = "Wire {{feature_name}} tasks to existing graph"
description = "Add blocking deps from new tasks to existing beads they depend on. Add related deps for beads that will need coordinated changes."
needs = ["decompose-tasks"]
priority = 1

[[steps]]
id = "validate-graph"
title = "Validate graph after {{feature_name}} addition"
description = "Run bv --robot-insights. Check for: new cycles (MUST fix), density still in healthy range, critical path change. Report findings."
needs = ["wire-to-existing"]
priority = 2
```

---

## Graph Quality Metrics (Self-Evaluation)

After each phase, BCC should evaluate the quality of the bead graph using bv's robot mode. A well-constructed graph has specific measurable properties.

### Target Graph Properties

| Metric | Healthy Range | What It Means |
|--------|--------------|---------------|
| **Density** | 0.03 - 0.12 | Connected enough for signal, not so dense it's noise |
| **PageRank variance** | StdDev > 0.02 | Clear differentiation between foundational and leaf nodes |
| **Betweenness max** | > 0.10 | At least one meaningful bridge/bottleneck exists |
| **HITS hub/auth ratio** | Both top-5 non-empty | Graph has both aggregators and providers |
| **Critical path length** | 3 - 15 nodes | Deep enough for prioritization, not pathologically deep |
| **Cycle count** | 0 | No circular deps (these are bugs) |
| **Topo sort valid** | true | Graph is a valid DAG |
| **Eigenvector variance** | > 0.01 | Influence is concentrated, not uniform |
| **Node count : Edge count** | 1:1.5 to 1:4 | Each node has 1.5-4 connections on average |

### Evaluation Commands

```bash
# After each phase, run:
bv --robot-insights | jq '{
  density: .clusterDensity,
  cycles: (.cycles | length),
  top_bottleneck: .bottlenecks[0],
  top_keystone: .keystones[0],
  top_hub: .hubs[0],
  top_authority: .authorities[0],
  topo_valid: (.stats.topologicalOrder | length > 0)
}'

# Check graph health:
bv --robot-triage | jq '.project_health'

# Verify no cycles:
bv --robot-insights | jq '.cycles'
```

---

## Operational Rules

### Bead Naming Convention
- **Epics:** `Architecture: <Boundary Name>` or `Feature: <Feature Name>`
- **Features:** `Module: <Module Name>` or `Domain: <Domain Name>`
- **Tasks:** `<Component>: <Specific Concern>` (e.g., `Auth Controllers: Session Management`)
- **Bugs:** `Debt: <Description>` for tech debt discoveries

### ID Prefixes
Use the project's configured prefix. If none, use `bcc-` prefix when initializing.

### Batching for Performance
- Create beads in batches using `bd sync` after every 10-20 operations
- Use `--json` flag on all bd commands for reliable parsing
- Avoid creating more than 500 beads for any single repo (diminishing returns)
- Target 50-200 beads for most codebases (sweet spot for metric quality)

### Incremental Compilation
BCC supports re-running on an existing graph:
1. Check `bv --robot-triage` for current state
2. Compare file system state to existing beads
3. Only create/update beads for new or changed areas
4. Run `bv --robot-diff --diff-since HEAD~1` to detect what changed

---

## Execution Flow

When the user invokes `/bcc` or asks to compile a codebase into beads:

### Step 1: Initialize
```bash
# Ensure beads is initialized
bd init --quiet
bd sync
```

### Step 2: Reconnaissance
Explore the repo to understand its shape before creating ANY beads:
- Count files by language/extension
- Identify top-level directories
- Read README, package.json/go.mod/pyproject.toml for dependency info
- Check for existing .beads/ directory (incremental mode)

### Step 3: Execute Phases
Run Phase 1 (SCAN) -> evaluate -> Phase 2 (ANALYZE) -> evaluate -> Phase 3 (CONNECT) -> evaluate -> Phase 4 (ENRICH)

After each phase, run the evaluation commands and report:
- Current bead count and edge count
- Density
- Whether cycles were introduced (fix immediately)
- Top 3 nodes by PageRank (are they the right ones?)

### Step 4: Validate
```bash
# Final validation
bv --robot-insights
bv --robot-triage
bv --robot-plan
```

Report the full graph health to the user with specific recommendations.

### Step 5: Export
```bash
# Generate the interactive visualization
bv --export-graph bcc-output.html --graph-title "BCC: <Project Name>"
```

---

## Hypotheses for Experimentation

The following hypotheses should be tested via the eval harness to determine optimal bead graph construction strategies:

### H1: Optimal Granularity
**Hypothesis:** Beads at the module/package level (5-20 files per bead) produce better PageRank differentiation than file-level (1:1) or directory-level (1 bead per top dir) granularity.
**Test:** Create the same repo at 3 granularity levels, compare PageRank StdDev.

### H2: Bridge Bead Injection
**Hypothesis:** Explicitly creating "contract" beads at module boundaries (even when no single file represents the contract) significantly increases betweenness centrality signal quality.
**Test:** Create the graph with and without synthetic contract beads, compare betweenness max.

### H3: Recursive Formula Depth
**Hypothesis:** 2-3 levels of recursive explore-module formula instantiation produces optimal graph depth for critical path analysis. Deeper recursion adds noise.
**Test:** Run explore-module at depths 1, 2, 3, 4, compare critical path length and metric variance.

### H4: Related Deps as Eigenvector Amplifiers
**Hypothesis:** Adding related (non-blocking) deps based on co-change history significantly improves eigenvector centrality signal without pathologically increasing density.
**Test:** Create the graph with blocking-only deps, then add related deps. Compare eigenvector variance and density.

### H5: Label Consistency for Attention View
**Hypothesis:** Using a consistent, limited label taxonomy (<20 labels) produces more actionable attention view scores than organic/unlimited labeling.
**Test:** Create the same graph with strict taxonomy vs. free-form labels, compare attention score variance.

### H6: Future Work Integration
**Hypothesis:** Adding planned feature beads (status: open) wired to existing code beads produces useful triage recommendations that correctly prioritize foundation work.
**Test:** Add 3-5 feature beads to an existing code graph, check if robot-triage correctly identifies blocking foundation work.

---

## Anti-Patterns (What NOT to Do)

1. **One bead per file:** Destroys signal-to-noise ratio. Graph becomes too flat.
2. **No blocking deps:** Without blocking edges, PageRank/betweenness/critical path are all meaningless.
3. **Everything depends on everything:** Density > 0.15 means the graph is pathologically coupled.
4. **Skipping labels:** Without labels, label-health, label-flow, and attention views are empty.
5. **Ignoring cycles:** Cycles make topo sort impossible and break most graph algorithms.
6. **Not running bv after changes:** BCC MUST verify graph health after every phase.
7. **Creating beads without descriptions:** Bare-title beads are useless for agent navigation.
