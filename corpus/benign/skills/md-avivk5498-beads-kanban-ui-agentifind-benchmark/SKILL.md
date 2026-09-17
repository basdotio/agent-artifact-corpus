---
name: agentifind-benchmark
description: Create a benchmark to measure CODEBASE.md effectiveness. Sets up hooks to run two parallel agents (one with guide, one without) and compare their efficiency. Requires /agentifind to be run first.
---

# Agentifind Benchmark Setup

This skill creates a benchmark infrastructure to measure how effectively CODEBASE.md helps AI agents navigate your codebase.

## Prerequisites

- `.claude/CODEBASE.md` must exist (run `/agentifind` first)
- `.claude/codebase.json` must exist

## Procedure

### Step 1: Verify Prerequisites

Check that required files exist:

```bash
test -f .claude/CODEBASE.md && test -f .claude/codebase.json && echo "Ready" || echo "Missing"
```

**If files don't exist:**
> CODEBASE.md not found. Please run `/agentifind` first to generate the codebase guide, then run `/agentifind-benchmark` again.

Exit the skill if prerequisites are not met.

### Step 2: Detect Repo Type and Tech Stack

Read `.claude/codebase.json` and check the `repo_type` field:

**If `repo_type` is `"terraform"` (or other IaC types):**
- This is an infrastructure repository
- Use the **Infrastructure Benchmark Template** (Step 6B)
- Focus on resource navigation, blast radius, dependency tracing

**If `repo_type` is missing or not an IaC type:**
- This is an application code repository
- Use the **Application Benchmark Template** (Step 6A)
- Identify:
  - Primary language (Python, TypeScript, JavaScript, Go)
  - Framework (FastAPI, Django, Flask, React, Next.js, Express, etc.)
  - Key patterns (async jobs, API routes, components, services)

This information will be used to create relevant benchmark tasks.

### Step 3: Create Hooks Directory

```bash
mkdir -p .claude/hooks
```

### Step 4: Create Hook Scripts

Create these 5 executable scripts in `.claude/hooks/`:

#### 4.1: `enforce-guide-restriction.sh`

This hook blocks `AGENT_WITHOUT_GUIDE` from reading CODEBASE.md and **logs violations**:

```bash
#!/bin/bash
#
# Enforce Guide Restriction Hook
# Blocks AGENT_WITHOUT_GUIDE from reading CODEBASE.md or .claude/ files
# Logs all violation attempts
#

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
AGENT_TRANSCRIPT=$(echo "$INPUT" | jq -r '.agent_transcript_path // empty')

LOG_DIR="$(pwd)"
VIOLATIONS_FILE="$LOG_DIR/benchmark_violations.jsonl"

# Only check Read tool
if [[ "$TOOL_NAME" != "Read" ]]; then
    echo '{"decision":"approve"}'
    exit 0
fi

# Only check subagents with transcript
if [[ -z "$AGENT_TRANSCRIPT" || ! -f "$AGENT_TRANSCRIPT" ]]; then
    echo '{"decision":"approve"}'
    exit 0
fi

# Extract agent identifier from transcript (try multiple patterns)
TRANSCRIPT_CONTENT=$(cat "$AGENT_TRANSCRIPT" 2>/dev/null)

# Try to find AGENT_WITHOUT_GUIDE in various message structures
IS_WITHOUT_GUIDE=false
if echo "$TRANSCRIPT_CONTENT" | grep -q "AGENT_WITHOUT_GUIDE"; then
    IS_WITHOUT_GUIDE=true
fi

if [[ "$IS_WITHOUT_GUIDE" != "true" ]]; then
    echo '{"decision":"approve"}'
    exit 0
fi

# Check for restricted file access
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // empty')

if echo "$FILE_PATH" | grep -qiE "(CODEBASE\.md|\.claude/)"; then
    # Log the violation
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    jq -n \
        --arg ts "$TIMESTAMP" \
        --arg agent "WITHOUT_GUIDE" \
        --arg file "$FILE_PATH" \
        --arg action "BLOCKED" \
        '{timestamp:$ts, agent:$agent, attempted_file:$file, action:$action, violation:true}' \
        >> "$VIOLATIONS_FILE"

    echo '{"decision":"block","reason":"BENCHMARK RULE: AGENT_WITHOUT_GUIDE cannot read CODEBASE.md or .claude/ files."}'
    exit 0
fi

echo '{"decision":"approve"}'
exit 0
```

#### 4.2: `log-benchmark-tools.sh`

This hook logs all tool calls for analysis with robust agent detection:

```bash
#!/bin/bash
#
# Benchmark Tool Call Logger
# Logs every tool call with agent identification
#

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
TOOL_USE_ID=$(echo "$INPUT" | jq -r '.tool_use_id // empty')
AGENT_TRANSCRIPT=$(echo "$INPUT" | jq -r '.agent_transcript_path // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

AGENT_TYPE="main"
AGENT_NAME="main"
TRANSCRIPT_FILE=""

if [[ -n "$AGENT_TRANSCRIPT" && -f "$AGENT_TRANSCRIPT" ]]; then
    AGENT_TYPE="subagent"
    TRANSCRIPT_FILE="$AGENT_TRANSCRIPT"

    # Read full transcript content for pattern matching
    TRANSCRIPT_CONTENT=$(cat "$AGENT_TRANSCRIPT" 2>/dev/null)

    # Robust detection: search entire transcript for agent markers
    if echo "$TRANSCRIPT_CONTENT" | grep -q "AGENT_WITH_GUIDE"; then
        AGENT_NAME="WITH_GUIDE"
    elif echo "$TRANSCRIPT_CONTENT" | grep -q "AGENT_WITHOUT_GUIDE"; then
        AGENT_NAME="WITHOUT_GUIDE"
    else
        # Fallback: use transcript filename as identifier
        AGENT_NAME=$(basename "$AGENT_TRANSCRIPT" .jsonl 2>/dev/null || echo "unknown")
    fi
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_DIR="$(pwd)"
JSONL_FILE="$LOG_DIR/benchmark_log.jsonl"

# Extract file path for Read tools (useful for analysis)
FILE_PATH=""
if [[ "$TOOL_NAME" == "Read" || "$TOOL_NAME" == "Glob" || "$TOOL_NAME" == "Grep" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // .path // .pattern // empty')
fi

jq -n \
    --arg ts "$TIMESTAMP" \
    --arg type "$AGENT_TYPE" \
    --arg name "$AGENT_NAME" \
    --arg tool "$TOOL_NAME" \
    --argjson input "$TOOL_INPUT" \
    --arg id "$TOOL_USE_ID" \
    --arg session "$SESSION_ID" \
    --arg transcript "$TRANSCRIPT_FILE" \
    --arg file "$FILE_PATH" \
    '{timestamp:$ts, agent_type:$type, agent_name:$name, tool:$tool, input:$input, tool_use_id:$id, session_id:$session, transcript_path:$transcript, target_file:$file}' \
    >> "$JSONL_FILE"

exit 0
```

#### 4.3: `analyze-benchmark.sh`

```bash
#!/bin/bash
#
# Analyze Benchmark Results
# Comprehensive analysis of tool calls, violations, and efficiency
#

LOG_DIR="$(pwd)"
LOG_FILE="$LOG_DIR/benchmark_log.jsonl"
VIOLATIONS_FILE="$LOG_DIR/benchmark_violations.jsonl"
TURNS_FILE="$LOG_DIR/benchmark_turns.jsonl"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "No benchmark log found at: $LOG_FILE"
    echo "Run benchmark tasks first."
    exit 1
fi

echo "# Benchmark Analysis"
echo "Generated: $(date)"
echo ""

# Total entries
TOTAL=$(wc -l < "$LOG_FILE" | tr -d ' ')
echo "**Total logged tool calls:** $TOTAL"
echo ""

echo "## Tool Calls by Agent"
echo "| Agent | Count |"
echo "|-------|-------|"

for AGENT in "main" "WITH_GUIDE" "WITHOUT_GUIDE"; do
    COUNT=$(grep "\"agent_name\":\"$AGENT\"" "$LOG_FILE" | wc -l | tr -d ' ')
    [[ "$COUNT" -gt 0 ]] && echo "| $AGENT | $COUNT |"
done

echo ""

# Tool breakdown by agent
echo "## Tool Breakdown by Agent"
echo ""

for AGENT in "WITH_GUIDE" "WITHOUT_GUIDE"; do
    COUNT=$(grep "\"agent_name\":\"$AGENT\"" "$LOG_FILE" | wc -l | tr -d ' ')
    if [[ "$COUNT" -gt 0 ]]; then
        echo "### $AGENT"
        echo "| Tool | Count |"
        echo "|------|-------|"
        grep "\"agent_name\":\"$AGENT\"" "$LOG_FILE" | \
            jq -r '.tool' | sort | uniq -c | sort -rn | \
            while read count tool; do
                echo "| $tool | $count |"
            done
        echo ""
    fi
done

# Violations section
echo "## Violations (Blocked Access Attempts)"
if [[ -f "$VIOLATIONS_FILE" ]]; then
    VIOLATION_COUNT=$(wc -l < "$VIOLATIONS_FILE" | tr -d ' ')
    echo "**Total violations:** $VIOLATION_COUNT"
    echo ""
    if [[ "$VIOLATION_COUNT" -gt 0 ]]; then
        echo "| Time | Agent | Attempted File |"
        echo "|------|-------|----------------|"
        jq -r '[.timestamp, .agent, .attempted_file] | @tsv' "$VIOLATIONS_FILE" | \
            while IFS=$'\t' read ts agent file; do
                echo "| $ts | $agent | \`$file\` |"
            done
    fi
else
    echo "No violations recorded (good - enforcement working correctly)"
fi
echo ""

# Turns tracking (if available)
if [[ -f "$TURNS_FILE" ]]; then
    echo "## Agent Turns (API Round-trips)"
    echo "| Agent | Turns |"
    echo "|-------|-------|"
    for AGENT in "WITH_GUIDE" "WITHOUT_GUIDE"; do
        TURNS=$(grep "\"agent_name\":\"$AGENT\"" "$TURNS_FILE" | wc -l | tr -d ' ')
        [[ "$TURNS" -gt 0 ]] && echo "| $AGENT | $TURNS |"
    done
    echo ""
fi

# Efficiency comparison
echo "## Efficiency Comparison"
echo ""

WITH=$(grep "\"agent_name\":\"WITH_GUIDE\"" "$LOG_FILE" | wc -l | tr -d ' ')
WITHOUT=$(grep "\"agent_name\":\"WITHOUT_GUIDE\"" "$LOG_FILE" | wc -l | tr -d ' ')

if [[ "$WITH" -gt 0 && "$WITHOUT" -gt 0 ]]; then
    RATIO=$(awk "BEGIN {printf \"%.2f\", $WITHOUT / $WITH}")
    REDUCTION=$(awk "BEGIN {printf \"%.1f\", (1 - $WITH / $WITHOUT) * 100}")

    echo "| Metric | Value |"
    echo "|--------|-------|"
    echo "| WITH_GUIDE calls | $WITH |"
    echo "| WITHOUT_GUIDE calls | $WITHOUT |"
    echo "| Efficiency ratio | ${RATIO}x |"
    echo "| **Reduction** | **${REDUCTION}% fewer calls with guide** |"
else
    echo "Insufficient data for comparison."
    echo "- WITH_GUIDE calls: $WITH"
    echo "- WITHOUT_GUIDE calls: $WITHOUT"
fi

echo ""

# Files accessed comparison
echo "## Files Accessed"
echo ""

for AGENT in "WITH_GUIDE" "WITHOUT_GUIDE"; do
    COUNT=$(grep "\"agent_name\":\"$AGENT\"" "$LOG_FILE" | wc -l | tr -d ' ')
    if [[ "$COUNT" -gt 0 ]]; then
        echo "### $AGENT"
        echo "\`\`\`"
        grep "\"agent_name\":\"$AGENT\"" "$LOG_FILE" | \
            jq -r 'select(.tool == "Read") | .input.file_path // empty' | \
            sort -u | head -20
        echo "\`\`\`"
        echo ""
    fi
done
```

#### 4.4: `track-turns.sh`

PostToolUse hook to track agent turns (API round-trips):

```bash
#!/bin/bash
#
# Track Agent Turns (PostToolUse)
# Logs completed tool calls to measure turns/round-trips
#

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_USE_ID=$(echo "$INPUT" | jq -r '.tool_use_id // empty')
AGENT_TRANSCRIPT=$(echo "$INPUT" | jq -r '.agent_transcript_path // empty')

# Only track subagent activity
if [[ -z "$AGENT_TRANSCRIPT" || ! -f "$AGENT_TRANSCRIPT" ]]; then
    exit 0
fi

# Detect agent type
TRANSCRIPT_CONTENT=$(cat "$AGENT_TRANSCRIPT" 2>/dev/null)
AGENT_NAME="unknown"

if echo "$TRANSCRIPT_CONTENT" | grep -q "AGENT_WITH_GUIDE"; then
    AGENT_NAME="WITH_GUIDE"
elif echo "$TRANSCRIPT_CONTENT" | grep -q "AGENT_WITHOUT_GUIDE"; then
    AGENT_NAME="WITHOUT_GUIDE"
fi

# Skip if not a benchmark agent
if [[ "$AGENT_NAME" == "unknown" ]]; then
    exit 0
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_DIR="$(pwd)"
TURNS_FILE="$LOG_DIR/benchmark_turns.jsonl"

jq -n \
    --arg ts "$TIMESTAMP" \
    --arg name "$AGENT_NAME" \
    --arg tool "$TOOL_NAME" \
    --arg id "$TOOL_USE_ID" \
    '{timestamp:$ts, agent_name:$name, tool:$tool, tool_use_id:$id}' \
    >> "$TURNS_FILE"

exit 0
```

#### 4.5: `reset-benchmark.sh`

```bash
#!/bin/bash
#
# Reset all benchmark logs
#

LOG_DIR="$(pwd)"

rm -f "$LOG_DIR/benchmark_log.jsonl"
rm -f "$LOG_DIR/benchmark_log.md"
rm -f "$LOG_DIR/benchmark_violations.jsonl"
rm -f "$LOG_DIR/benchmark_turns.jsonl"
rm -f "$LOG_DIR/benchmark_results.md"

echo "Benchmark logs cleared:"
echo "  - benchmark_log.jsonl"
echo "  - benchmark_violations.jsonl"
echo "  - benchmark_turns.jsonl"
echo ""
echo "Ready for new benchmark run."
```

Make all scripts executable:
```bash
chmod +x .claude/hooks/*.sh
```

### Step 5: Create settings.json

Create `.claude/settings.json` (or merge with existing):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {"type": "command", "command": ".claude/hooks/log-benchmark-tools.sh"}
        ]
      },
      {
        "matcher": "Read",
        "hooks": [
          {"type": "command", "command": ".claude/hooks/enforce-guide-restriction.sh"}
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {"type": "command", "command": ".claude/hooks/track-turns.sh"}
        ]
      }
    ]
  }
}
```

### Step 6: Create Benchmark Tasks

Based on the repo type detected in Step 2, use the appropriate template.

---

### Step 6A: Application Benchmark Template

**Use this template when `repo_type` is NOT `"terraform"` or similar IaC types.**

Create `.claude/BENCHMARK_ENGINEERING.md` with **7 tasks** tailored to the detected tech stack.

**Task Categories:**
1. **TASK-1 (⭐ Fundamental):** Find a configuration value
2. **TASK-2 (⭐ Fundamental):** Locate a specific function/class
3. **TASK-3 (⭐⭐ Intermediate):** Trace a data flow
4. **TASK-4 (⭐⭐⭐ Advanced):** Add a new feature following existing patterns
5. **TASK-5 (⭐⭐⭐ Advanced):** Fix a bug with provided symptoms
6. **TASK-6 (⭐⭐⭐⭐ Expert):** Debug a race condition or performance issue
7. **TASK-7 (⭐⭐⭐⭐⭐ Expert):** Design a cross-cutting feature

**Template:**

```markdown
# {Project Name} Engineering Benchmark

**Purpose:** Measure CODEBASE.md effectiveness on real engineering tasks.

---

## Orchestrator Instructions

You are running a benchmark to compare agent efficiency WITH vs WITHOUT the CODEBASE.md guide.

**IMPORTANT RULES:**
1. Run agents in FOREGROUND (do NOT use run_in_background)
2. Run both agents IN PARALLEL for the same task (single message, two Task calls)
3. Wait for both to complete before reporting results
4. Report token usage from the Task tool response if available
5. Track metrics from agent self-reports

---

## How to Run

### 1. Reset Logs
\`\`\`bash
.claude/hooks/reset-benchmark.sh
\`\`\`

### 2. Run Both Agents in Parallel (Foreground)

For each task, spawn BOTH subagents in a SINGLE message using two Task tool calls.
Do NOT use run_in_background - we need the full response including token usage.

\`\`\`
Task 1 (WITH_GUIDE):
- subagent_type: "general-purpose"
- run_in_background: false  # IMPORTANT: foreground for token tracking
- prompt: |
    AGENT_WITH_GUIDE: BENCHMARK

    You have access to .claude/CODEBASE.md - a navigation guide for this codebase.

    WORKFLOW:
    1. Read .claude/CODEBASE.md FIRST
    2. Use "Key Files" and "Architecture" sections to identify exactly where to look
    3. Go DIRECTLY to relevant files - don't search broadly
    4. Minimize tool calls - the guide tells you where things are

    TASK: [task description]

    DELIVERABLES:
    - Answer with specific file paths and line numbers
    - Confidence: HIGH/MEDIUM/LOW
    - METRICS: Read=[n] Grep=[n] Glob=[n] Total=[n] | Files: [list]

Task 2 (WITHOUT_GUIDE):
- subagent_type: "general-purpose"
- run_in_background: false  # IMPORTANT: foreground for token tracking
- prompt: |
    AGENT_WITHOUT_GUIDE: BENCHMARK

    RESTRICTION: Do NOT read .claude/CODEBASE.md or any .claude/ files.
    You must explore the codebase using only Grep, Glob, and Read on source files.

    TASK: [task description]

    DELIVERABLES:
    - Answer with specific file paths and line numbers
    - Confidence: HIGH/MEDIUM/LOW
    - METRICS: Read=[n] Grep=[n] Glob=[n] Total=[n] | Files: [list]
\`\`\`

### 3. Record Results

After both agents complete, fill in this comparison table:

| Metric | WITH_GUIDE | WITHOUT_GUIDE |
|--------|------------|---------------|
| Tool calls | | |
| Read | | |
| Grep | | |
| Glob | | |
| Confidence | | |
| Correct? | | |
| Tokens (if available) | | |

### 4. (Optional) Analyze Main Agent Activity
\`\`\`bash
.claude/hooks/analyze-benchmark.sh
\`\`\`

Note: The analysis script captures main agent tool calls. Subagent metrics come from self-reporting.

---

## Tasks

### TASK-1: Fundamental - Find Configuration
**Difficulty:** ⭐
[Create task based on project's config patterns]

### TASK-2: Fundamental - Locate Component
**Difficulty:** ⭐
[Create task to find a specific class/function]

### TASK-3: Intermediate - Trace Data Flow
**Difficulty:** ⭐⭐
[Create task tracing request through system]

### TASK-4: Advanced - Add Feature
**Difficulty:** ⭐⭐⭐
[Create task adding feature following existing patterns]

### TASK-5: Advanced - Fix Bug
**Difficulty:** ⭐⭐⭐
[Create task with bug symptoms to diagnose]

### TASK-6: Expert - Debug Issue
**Difficulty:** ⭐⭐⭐⭐
[Create task with race condition or performance issue]

### TASK-7: Expert - Design Feature
**Difficulty:** ⭐⭐⭐⭐⭐
[Create cross-cutting feature design task]

---

## Scoring

| Criteria | 0 | 1 | 2 | 3 |
|----------|---|---|---|---|
| Completion | Failed | Partial | Minor issues | Correct |
| Efficiency | >50 calls | 30-50 | 15-30 | <15 |
| Quality | Wrong patterns | Partial | Minor deviations | Matches style |

**Total: /9 per task, /63 overall**
```

**Important:** Each task must be specific to the actual codebase. Use information from:
- `codebase.json` stats (files, functions, classes)
- `codebase.json` modules (real file paths)
- `codebase.json` call_graph (real function relationships)
- `CODEBASE.md` architecture section

---

### Step 6B: Infrastructure Benchmark Template

**Use this template when `repo_type` is `"terraform"`, `"kubernetes"`, `"ansible"`, or `"cloudformation"`.**

Create `.claude/BENCHMARK_INFRASTRUCTURE.md` with **7 tasks** tailored to IaC navigation.

**Infrastructure Task Categories:**
1. **TASK-1 (⭐ Fundamental):** Find a resource by type
2. **TASK-2 (⭐ Fundamental):** Locate a variable definition
3. **TASK-3 (⭐⭐ Intermediate):** Trace resource dependencies
4. **TASK-4 (⭐⭐⭐ Advanced):** Assess blast radius of a change
5. **TASK-5 (⭐⭐⭐ Advanced):** Add a new resource following patterns
6. **TASK-6 (⭐⭐⭐⭐ Expert):** Debug a dependency cycle
7. **TASK-7 (⭐⭐⭐⭐⭐ Expert):** Design module refactoring

**Template:**

```markdown
# {Project Name} Infrastructure Benchmark

**Purpose:** Measure CODEBASE.md effectiveness on infrastructure navigation tasks.

---

## Orchestrator Instructions

You are running a benchmark to compare agent efficiency WITH vs WITHOUT the CODEBASE.md guide.

**IMPORTANT RULES:**
1. Run agents in FOREGROUND (do NOT use run_in_background)
2. Run both agents IN PARALLEL for the same task (single message, two Task calls)
3. Wait for both to complete before reporting results
4. Report token usage from the Task tool response if available
5. Track metrics from agent self-reports

---

## How to Run

### 1. Reset Logs
\`\`\`bash
.claude/hooks/reset-benchmark.sh
\`\`\`

### 2. Run Both Agents in Parallel (Foreground)

For each task, spawn BOTH subagents in a SINGLE message using two Task tool calls.
Do NOT use run_in_background - we need the full response including token usage.

\`\`\`
Task 1 (WITH_GUIDE):
- subagent_type: "general-purpose"
- run_in_background: false  # IMPORTANT: foreground for token tracking
- prompt: |
    AGENT_WITH_GUIDE: BENCHMARK

    You have access to .claude/CODEBASE.md - an infrastructure navigation guide.

    WORKFLOW:
    1. Read .claude/CODEBASE.md FIRST
    2. Use "Resource Inventory" and "Blast Radius" sections to identify targets
    3. Go DIRECTLY to relevant .tf files - don't search broadly
    4. Minimize tool calls - the guide tells you where things are

    TASK: [task description]

    DELIVERABLES:
    - Answer with specific file paths and line numbers
    - List affected resources if applicable
    - Confidence: HIGH/MEDIUM/LOW
    - METRICS: Read=[n] Grep=[n] Glob=[n] Total=[n] | Files: [list]

Task 2 (WITHOUT_GUIDE):
- subagent_type: "general-purpose"
- run_in_background: false  # IMPORTANT: foreground for token tracking
- prompt: |
    AGENT_WITHOUT_GUIDE: BENCHMARK

    RESTRICTION: Do NOT read .claude/CODEBASE.md or any .claude/ files.
    You must explore the infrastructure using only Grep, Glob, and Read on .tf files.

    TASK: [task description]

    DELIVERABLES:
    - Answer with specific file paths and line numbers
    - List affected resources if applicable
    - Confidence: HIGH/MEDIUM/LOW
    - METRICS: Read=[n] Grep=[n] Glob=[n] Total=[n] | Files: [list]
\`\`\`

### 3. Record Results

After both agents complete, fill in this comparison table:

| Metric | WITH_GUIDE | WITHOUT_GUIDE |
|--------|------------|---------------|
| Tool calls | | |
| Read | | |
| Grep | | |
| Glob | | |
| Confidence | | |
| Correct? | | |
| Tokens (if available) | | |

### 4. (Optional) Analyze Main Agent Activity
\`\`\`bash
.claude/hooks/analyze-benchmark.sh
\`\`\`

---

## Tasks

### TASK-1: Fundamental - Find Resource
**Difficulty:** ⭐
**Task:** Find all resources of type `{resource_type}` (e.g., aws_security_group, aws_iam_role).
**Expected:** List all instances with file paths and line numbers.
[Use resources from codebase.json stats.providers to pick a common type]

### TASK-2: Fundamental - Locate Variable
**Difficulty:** ⭐
**Task:** Find where variable `{variable_name}` is defined and list all resources that use it.
**Expected:** Variable definition location + list of usages.
[Pick a variable with used_by.length > 3 from codebase.json]

### TASK-3: Intermediate - Trace Dependencies
**Difficulty:** ⭐⭐
**Task:** Trace all resources that depend on `{resource.type}.{resource.name}`.
**Expected:** Complete dependency chain (direct and transitive).
[Pick a resource with multiple dependents from dependency_graph]

### TASK-4: Advanced - Blast Radius Assessment
**Difficulty:** ⭐⭐⭐
**Task:** If we modify `{high_risk_resource}`, what resources would be affected?
**Expected:** Complete blast radius analysis with severity assessment.
[Pick from blast_radius where severity is "high"]

### TASK-5: Advanced - Add Resource
**Difficulty:** ⭐⭐⭐
**Task:** Add a new `{resource_type}` resource following the existing naming and tagging patterns.
**Expected:** Code snippet following project conventions.
[Analyze existing resources to determine patterns]

### TASK-6: Expert - Debug Dependency Issue
**Difficulty:** ⭐⭐⭐⭐
**Task:** Resource `{resource}` fails to create with "dependency not ready" error. Find the root cause.
**Expected:** Identify missing explicit depends_on or circular dependency.
[Create realistic scenario from dependency_graph]

### TASK-7: Expert - Module Refactoring
**Difficulty:** ⭐⭐⭐⭐⭐
**Task:** Refactor `{set of resources}` into a reusable module. What inputs/outputs are needed?
**Expected:** Module interface design with variable list and output values.
[Pick related resources that could be modularized]

---

## Scoring

| Criteria | 0 | 1 | 2 | 3 |
|----------|---|---|---|---|
| Completion | Failed | Partial | Minor issues | Correct |
| Efficiency | >50 calls | 30-50 | 15-30 | <15 |
| Blast Radius | Missed deps | Partial | Minor misses | Complete |

**Total: /9 per task, /63 overall**
```

**Important:** Each task must be specific to the actual infrastructure. Use information from:
- `codebase.json` stats (resources, modules, providers)
- `codebase.json` resources (real resource types and names)
- `codebase.json` dependency_graph (real dependency chains)
- `codebase.json` blast_radius (high-risk resources)
- `CODEBASE.md` infrastructure sections

---

### Step 7: Report Completion

Tell the user (adjust based on repo type):

**For Application Repos:**

> **Benchmark setup complete!**
>
> **Repo Type:** Application Code
>
> Created:
> - `.claude/hooks/` (5 scripts)
> - `.claude/settings.json` (hook configuration with PreToolUse + PostToolUse)
> - `.claude/BENCHMARK_ENGINEERING.md` (7 tasks)
>
> **To run the benchmark:**
> 1. Reset: `.claude/hooks/reset-benchmark.sh`
> 2. For each task, spawn two parallel subagents (see BENCHMARK_ENGINEERING.md)
> 3. Analyze: `.claude/hooks/analyze-benchmark.sh`
>
> **The hooks will:**
> - Block `AGENT_WITHOUT_GUIDE` from reading CODEBASE.md
> - **Log violations** when WITHOUT_GUIDE attempts to access restricted files
> - Log all tool calls for comparison
> - **Track agent turns** (API round-trips)
>
> **Metrics captured:**
> - Tool call counts per agent
> - Tool breakdown (Read, Grep, Glob, etc.)
> - Violation attempts (blocked reads)
> - Agent turns (completed operations)
> - Files accessed by each agent
>
> **Expected result:** 40-60% fewer tool calls with CODEBASE.md

**For Infrastructure/Terraform Repos:**

> **Benchmark setup complete!**
>
> **Repo Type:** Infrastructure (Terraform/IaC)
>
> Created:
> - `.claude/hooks/` (5 scripts)
> - `.claude/settings.json` (hook configuration with PreToolUse + PostToolUse)
> - `.claude/BENCHMARK_INFRASTRUCTURE.md` (7 infrastructure tasks)
>
> **To run the benchmark:**
> 1. Reset: `.claude/hooks/reset-benchmark.sh`
> 2. For each task, spawn two parallel subagents (see BENCHMARK_INFRASTRUCTURE.md)
> 3. Analyze: `.claude/hooks/analyze-benchmark.sh`
>
> **Infrastructure-specific metrics:**
> - Resource navigation efficiency
> - Blast radius identification accuracy
> - Dependency tracing completeness
> - Variable usage mapping
>
> **The hooks will:**
> - Block `AGENT_WITHOUT_GUIDE` from reading CODEBASE.md
> - Log all .tf file accesses for comparison
> - Track how efficiently each agent finds resources/modules
>
> **Expected result:** 40-60% fewer tool calls with CODEBASE.md, better blast radius accuracy

## Notes

- Tasks must reference real files and patterns from this specific codebase
- Do not create generic tasks - analyze codebase.json to find actual components
- Each task should have a clear expected answer based on the codebase
- The benchmark measures navigation efficiency, not code quality
- **For IaC repos:** Focus on resource discovery, dependency tracing, and blast radius assessment

## Technical Limitations

**Hooks don't run inside subagents:** Claude Code hooks only execute in the main conversation context. Subagent tool calls are not captured by PreToolUse/PostToolUse hooks.

**Workaround:** Agents self-report their metrics at the end of each task. The prompt includes a METRICS template they must fill out.

**What the hooks DO capture:**
- Main agent spawning subagents (Task tool calls)
- Violations if WITHOUT_GUIDE tries to read .claude/ files (blocked by hook)

**Token usage:** Not directly available via hooks. To estimate:
- Tool calls correlate with input/output tokens
- Check API billing dashboard for actual usage
- Or parse conversation transcripts in `~/.claude/projects/`
