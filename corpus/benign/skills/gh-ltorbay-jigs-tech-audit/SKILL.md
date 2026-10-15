---
name: tech-audit
description: Deep technical audit. Discovers the source tree at runtime, assigns every directory to a domain agent (exhaustive by construction), and spawns parallel subagents plus an orthogonal dependency/seam agent and a test-coverage agent. Produces tech-audit.md (findings) and tech-audit-deps.md (dependency/cycle map) at project root. Research only; edits nothing else.
license: MIT
compatibility: Requires the Agent tool with model selection, plus Bash/Glob/Grep for the discovery and dependency pre-passes.
metadata:
  version: "1.0"
---

Run a comprehensive technical audit. The goal is two artifacts at the project root: `tech-audit.md` (concise findings covering technical debt, architecture issues and code smells, with precise `file:line` pointers, short explanations and fix leads) and `tech-audit-deps.md` (the dependency/cycle map from the mechanical pre-pass and the seam agent).

**IMPORTANT:** the whole audit completes in a single request. Spawn all subagents in parallel, with the strongest model available: the value is in deep reading, and a cheaper model that skims returns findings you then have to re-verify.

**Why this skill is structured the way it is.** A previous version hardcoded a per-agent list of file paths. That manifest silently rotted when the codebase was reorganised, and it partitioned work on a single axis (feature domain), which structurally cannot see coupling, because coupling lives on the edges *between* domains. This version **discovers** the tree at runtime so coverage cannot rot, and adds an **orthogonal seam agent** so the inter-module edges have an owner.

---

## Step 1: Discover the source tree and build the coverage map

Do NOT hardcode file paths. Enumerate the actual tree, then assign every source directory to exactly one domain agent.

1. Enumerate every directory under `scripts/` that contains at least one `.gd` file:
   ```bash
   find scripts -name '*.gd' | sed 's#/[^/]*$##' | sort -u
   ```
2. Apply a **stable directory→domain rule** (pattern match, first match wins). The rule is by *directory*, so each directory is owned wholesale by one agent; feature agents read into other directories to follow references, but do not *own* them. Fill this table for your project; keep the catch-all:

   | Directory pattern | Domain agent |
   |---|---|
   | `scripts/systems/<subsystem-a>/**` | **Subsystem A** |
   | `scripts/systems/<subsystem-b>/**` | **Subsystem B** |
   | `scripts/ui/**`, `scripts/systems/vfx/**` | **UI & VFX** |
   | `scripts/data/**` | **Data Model & Resources** |
   | `scripts/tools/**` | **Tooling** |
   | `scripts/tests/**` | **Test Coverage** |
   | `scripts/*.gd`, `scripts/autoloads/**`, `scripts/utils/**` | **Architecture & Glue** |
   | *anything else (catch-all)* | **Architecture & Glue**, and print an `UNCLASSIFIED DIR` warning naming it |

3. **Print the coverage table** and **assert the partition is total and disjoint**: every discovered source directory appears under exactly one domain. If any directory is unassigned or assigned twice, STOP and report it. The catch-all guarantees an owner always exists; the warning makes a brand-new top-level concept loud rather than invisible.

**Scope boundary (explicit, not accidental):** discovery covers `scripts/`. Scenes are sampled by the UI agent, resources by the Data agent, `addons/` is out of scope (third-party). State this boundary in the final report.

---

## Step 2: Mechanical dependency pre-pass

Before any agent reasons about coupling, build the dependency graph mechanically and detect cycles.

1. Extract edges:
   - `class_name` declarations (`grep -rn '^class_name' scripts`) and their usages. The global `class_name` registry is GDScript's dominant coupling vector: any file can reference any `class_name` with no import.
   - `preload(...)` / `load(...)` path references.
   - Autoload singletons from `project.godot` (the `[autoload]` block).
2. Build a file→file (or class→class) edge list.
3. Run cycle detection and record every cycle with its participating files.
4. Compute per-module fan-in / fan-out so the seam agent can spot god-nodes and unstable hubs.

Treat this graph as **high-recall, not ground truth** (a `class_name` token can appear in a comment or string). The seam agent confirms edges by reading.

---

## Step 3: Read project context

Read root `CLAUDE.md` and every per-folder `CLAUDE.md` surfaced by discovery, plus `project.godot`. Each subagent prompt MUST carry the slice of this context relevant to its domain, so it can tell intentional conventions from accidental smells.

---

## Step 4: Spawn ALL subagents in parallel

In a single message, spawn every domain agent from the coverage table, plus the **Test Coverage** agent and the **Seam & Dependency** agent. Each is research-only.

Every subagent prompt MUST include: the relevant CLAUDE.md slice; its **owned directories** as globs (not a frozen file list) with the instruction *read every source file in your owned directories thoroughly, no skimming, and follow references outward as needed (read, don't own)*; the severity taxonomy; the output format.

### Severity taxonomy

- `structural`: architecture flaw, wrong abstraction boundary, circular dependency, design that will break at scale. Requires redesign.
- `friction`: code smell, unnecessary complexity, coupling that slows development, inconsistent patterns. Worth fixing, not blocking.
- `minor`: naming, missing types, small duplication, style. Fix opportunistically.

### Subagent output format

```markdown
## <Domain Name>

### Findings

#### [structural] <Short title>
**Location:** `path/to/file.gd:42`
**Issue:** One-sentence description of the problem.
**Impact:** Why this matters (concrete consequence, not theoretical).
**Lead:** Direction for fixing; not a prescription, just enough to start.
```

Findings sorted by severity. Each finding has a real `file:line`. No vague observations without code pointers.

### Domain agents

Each domain agent reads its owned directories with **two lenses applied together**: domain correctness (wrong abstractions, broken invariants, edge cases, dead branches, contracts that can desync) and code quality (long methods, duplication, inconsistent naming, loose typing, GDScript typing gotchas such as `Dictionary.get()` without an explicit type, `:=` on a Variant return, untyped `for` over arrays, dead code). Layer domain-specific key questions on top per subsystem (determinism under fixed seed, read-only contracts, hidden state mutation, unreachable states, race conditions in async flow, entity cleanup, editor-only tooling leaking into runtime).

### Test Coverage agent (`scripts/tests/`)

Audits the test layer as a system: subsystems with no behavioural suite; parity invariants asserted nowhere; **silently-skipped suites** (a green pass count can hide a suite that failed to compile and attached as a bare Node; verify every suite header actually runs); brittle or tautological tests (reading both input and expected output from the same resource); meta-suite escape hatches (`SKIP_*` / `EXCLUDE_*` / `ALLOWED_*`) growing without justification.

### Seam & Dependency agent (orthogonal)

Unit of analysis is the dependency **edge between** modules. Give it the Step-2 graph. Mandate: confirm each mechanically-detected cycle by reading and report it with `file:line`; layering violations (UI reaching into core internals, data classes depending on systems); cohesion and god objects (cross-reference high fan-in); **global coupling specific to GDScript**: which modules reach into each autoload singleton, breadth of the `class_name` registry, and **signal temporal coupling** (implicit connection-order dependencies). Do NOT treat "uses signals" as automatically decoupled.

---

## Step 5: Synthesise

Once all agents return, write the two artifacts.

`tech-audit.md`: header (date, coverage: N directories across M domains, scope boundary), executive summary (3 to 5 sentences), then structural / friction / minor sections, then cross-cutting observations including the seam agent's narrative.

`tech-audit-deps.md`: module dependency overview, detected cycles (each traceable from a structural finding), fan-in/out hotspots, global-coupling summary.

**Synthesis rules:** deduplicate (merge the same issue found from two angles); promote (a friction finding in 3+ domains may be structural); cut anything that is "could theoretically be a problem" with no evidence; respect intentional design documented in CLAUDE.md ("intentional, documented", downgrade or drop); **never fabricate**: synthesis only merges findings the agents returned; keep it to 40 to 80 findings.

---

## Guardrails

- **Research only.** The ONLY files written are `tech-audit.md` and `tech-audit-deps.md`.
- **Exhaustive by construction.** If you find yourself typing a literal file path into an agent prompt, stop; pass directory globs instead.
- **Precise pointers, fix leads not prescriptions, no false positives.** Precision over recall.
