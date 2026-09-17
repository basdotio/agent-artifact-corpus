---
name: rayven-integration
description: Manages exploratory computational analysis sessions using RAYVEN CLI. Use when doing data analysis, scientific computing, machine learning experiments, or any exploratory work where you try approaches, iterate, and need to track what worked.
---

# RAYVEN Integration Guide for Claude Code

This document defines how Claude Code should interact with RAYVEN during exploratory computational analysis sessions.

## What is RAYVEN?

RAYVEN (**R**ecord **A**nal**Y**sis **V**ersions, **E**xplorations, **N**otes) is a lightweight CLI for managing exploratory computational analysis sessions. It tracks:

- **Session state**: goal, uncertainty, status
- **Decision log**: terse record of methodological pivots
- **Artifacts**: figures (versioned), data outputs (registered)
- **Provenance**: what code/data produced each artifact

## When to Use RAYVEN

Use RAYVEN when the user is doing **exploratory computational work**:
- Data analysis and visualization
- Scientific computing
- Machine learning experiments
- Statistical analysis
- Any work where you try approaches, iterate, and need to track what worked

**Do NOT use RAYVEN for**:
- Simple code edits or bug fixes
- Documentation tasks
- Non-exploratory development work

---

## Session Start Protocol

When beginning exploratory work, probe to establish context:

### Always Ask:
1. **What is the goal?** (Can be vague: "make sense of this data")
2. **What data do we have?** (Paths, formats, known issues)
3. **What's uncertain?** (Data quality? Method? Goal clarity?)

### Based on Answers:
```bash
# Initialize with appropriate uncertainty levels
rayven init "Identify patterns in gene expression data" \
  --uncertainty-data low \
  --uncertainty-method high \
  --uncertainty-goal medium \
  --tags "genomics,clustering"
```

### If Goal is Vague:
- Accept it—exploration is valid
- Set `--uncertainty-goal high`
- Plan to revisit goal as understanding develops

---

## Decision Logging Heuristics

The decision log captures the **intellectual history** of exploration—methodological pivots, not code changes.

### Log When You:
- Try a method and it fails or underperforms
- Change parameters that affect interpretation (not just speed/formatting)
- Switch analytical approaches
- Discover something that changes direction
- Reject a hypothesis based on evidence

### Do NOT Log:
- Figure styling changes
- Code refactoring
- File reorganization
- Debugging steps (unless the bug reveals something about the data/method)

### Format Guidance:
- **Decision**: what you tried (be specific about parameters)
- **Outcome**: what happened (concrete, not vague)
- **Next**: what follows (if clear)

### Good Examples:
```bash
rayven log "Tried hierarchical clustering on raw HDX uptake" \
  -o "Variance dominated by back-exchange artifacts, clusters meaningless" \
  -n "Normalize by max deuteration first"

rayven log "k-means with k=3 on normalized data" \
  -o "Cluster 2 internally heterogeneous (high intra-cluster variance)" \
  -n "Try k=4"

rayven log "Parameter sweep: regularization lambda 0.01-1.0" \
  -o "lambda=0.1 gives best cross-validation score, stable across folds"
```

### Bad Examples:
```bash
# Too vague
rayven log "Tried clustering" -o "Didn't work"

# Formatting, not methodology
rayven log "Changed figure colors to colorblind-friendly palette" -o "Looks better"
```

---

## Script Management

When performing data analysis or generating figures, **always save substantive code to `scripts/`** rather than running inline. This ensures reproducibility and enables proper provenance tracking.

### When to Save a Script:
- Any code that produces a registered artifact (data file or figure)
- Analysis code that might need to be re-run or modified
- Code with non-trivial logic (>10-15 lines)
- Any transformation that future-you would want to understand

### When Inline Code is OK:
- Quick exploratory checks (e.g., `df.head()`, `df.describe()`)
- One-off data inspection that won't be repeated
- Simple file operations (moving, renaming)

### Script Naming Convention:
```
scripts/
├── create_<output>.py        # Data transformation scripts
├── plot_<figure>.py          # Visualization scripts
├── analyze_<topic>.py        # Analysis scripts
└── utils.py                  # Shared helper functions (if needed)
```

### Workflow:
1. **Write** the script to `scripts/<name>.py`
2. **Run** the script: `python3 scripts/<name>.py`
3. **Register** the output with provenance:
   ```bash
   rayven artifact add <output_path> "<description>" \
     --source scripts/<name>.py \
     --data <input_files>
   ```

### Example:

```bash
# WRONG: Running inline code that produces an artifact
python3 << 'EOF'
import pandas as pd
# ... 50 lines of analysis ...
df.to_csv('data/results.csv')
EOF

# RIGHT: Save to scripts/ first
# 1. Write scripts/create_results.py
# 2. Run: python3 scripts/create_results.py
# 3. Register: rayven artifact add data/results.csv "..." --source scripts/create_results.py
```

**The principle: If code produces something worth tracking, it's worth saving.**

---

## Artifact Registration

### Register Figures When:
- They represent a meaningful analysis result
- They might be referenced in documentation
- You want to preserve the current state before iterating

### Mark as Final When:
- The figure is publication/report ready
- The analysis it represents is complete
- You're confident you won't need to regenerate

### Always Record Provenance for Final Figures:
```bash
rayven artifact add figures/main_result.png \
  "Final clustering showing 4 conformational states" \
  --source scripts/plot_clusters.py \
  --data scratch/normalized.csv \
  --final
```

### For Data Outputs:
```bash
# Register intermediate data
rayven artifact add scratch/normalized.csv \
  "HDX uptake normalized by max deuteration" \
  --source scripts/normalize.py

# Snapshot important data files
rayven artifact add results/final_clusters.csv \
  "Final cluster assignments" \
  --snapshot \
  --source scripts/cluster.py
```

---

## Breakpoint Detection

Every 5-10 tool calls (calibrate based on context length), ask yourself:

1. Are we still working toward the stated goal?
2. Has scope crept significantly?
3. Have we discovered a sub-problem that deserves its own session?

### Signs to Split (use `rayven spawn`):
- New dataset entered that wasn't in original scope
- "Side quest" that could take substantial effort
- Goal has fundamentally shifted
- Work naturally divides (data generation vs. analysis)

### When Splitting:
```bash
# Discuss with user first, then:
rayven spawn "Generate synthetic variants for testing" --dir ../variant-generation
```

---

## Checkpoint Timing

Documentation (`docs/summary.html`) is **not updated continuously**—it's generated on-demand via `rayven checkpoint`. This keeps overhead low during active exploration.

### When to Run `rayven checkpoint`:
- **After significant progress** (3+ meaningful decisions logged)
- **Before risky operations** (preserves state if something breaks)
- **At natural pauses** (lunch break, end of day, context switch)
- **When user asks** to see current state
- **Before ending** a session (ensures final documentation is complete)

### When NOT to Checkpoint:
- After every single decision (too frequent, adds noise)
- During rapid iteration (wait until you have results worth documenting)

```bash
rayven checkpoint  # Generates docs/summary.html
```

**Rule of thumb**: If you've made progress worth explaining to future-you, checkpoint it.

---

## Session End

Before ending:
1. Ensure all final artifacts are marked `--final` with provenance
2. Review decision log for completeness
3. Write a terse but complete outcome

### Outcome Should Answer: "What did we learn and/or produce?"

### Good Examples:
```bash
rayven end --outcome "Identified 4 conformational states from HDX-MS data using k-means on normalized uptake. States correspond to apo, substrate-bound, product-bound, and intermediate. Scripts generalized for reuse."

# For abandoned sessions
rayven end --abandoned "Data quality insufficient—back-exchange correction unreliable. Need to re-collect with internal standards."
```

### Bad Example:
```bash
rayven end --outcome "Analysis complete"  # Too vague!
```

---

## Quick Reference

### Session Management
```bash
rayven init "<goal>" [--uncertainty-*] [--tags] [--parent]
rayven status
rayven end --outcome "<summary>" | --abandoned "<reason>"
rayven spawn "<new_goal>" [--dir]
```

### Decision Logging
```bash
rayven log "<decision>" -o "<outcome>" [-n "<next>"]
```

### Artifacts
```bash
rayven artifact add <path> "<desc>" [--source] [--data] [--final] [--snapshot]
rayven artifact list [--final] [--figures]
rayven artifact history <path>
rayven artifact verify
```

### Documentation
```bash
rayven checkpoint
rayven export -f <html|markdown> [-o <path>]
```

### Index
```bash
rayven index list [--status] [--tag] [--search]
rayven index show <session_id>
rayven index rebuild
```

---

## Workflow Example

Here's a typical session workflow:

```bash
# 1. Start session
rayven init "Analyze customer churn patterns" \
  --uncertainty-data low \
  --uncertainty-method high \
  --tags "churn,ml"

# 2. Log exploration decisions
rayven log "Tried logistic regression with default params" \
  -o "AUC 0.72, feature importance shows tenure dominant" \
  -n "Try random forest for comparison"

rayven log "Random forest with 100 trees" \
  -o "AUC 0.81, better but overfitting on validation set" \
  -n "Add regularization or reduce features"

# 3. Register artifacts as you go
rayven artifact add figures/feature_importance.png \
  "Feature importance from random forest" \
  --source scripts/train_model.py

# 4. Checkpoint after progress
rayven checkpoint

# 5. Mark final artifacts with provenance
rayven artifact add figures/final_roc_curve.png \
  "ROC curve for tuned model (AUC=0.85)" \
  --source scripts/evaluate.py \
  --data data/test_set.csv \
  --final

# 6. End with clear outcome
rayven end --outcome "Built churn prediction model with 0.85 AUC. Key predictors: tenure, monthly charges, contract type. Model saved to models/churn_rf.pkl"
```

---

## Token Efficiency

RAYVEN commands are cheap. Don't hesitate to:
- Log decisions frequently
- Checkpoint often
- Register artifacts as you go

**The cost of forgetting is higher than the cost of logging.**

---

## Directory Structure Reference

After `rayven init`, the project structure is:

```
project/
├── session.yaml           # Session state (RAYVEN managed)
├── .rayven.log            # Human-readable command log
├── .rayven.trace.jsonl    # Detailed traces
├── .rayven.history        # Command history
├── .rayven.session.bak    # Backup of session.yaml
├── scripts/               # Analysis scripts (user managed)
├── data/                  # Input data (user managed)
├── scratch/               # Working outputs
├── artifacts/             # Tracked outputs (RAYVEN managed)
│   └── figures/           # Versioned figures
└── docs/                  # Generated documentation
    └── summary.html
```

---

## Finding Prior Work

Before starting new analysis, check if relevant prior work exists:

```bash
rayven index list --search "clustering"
rayven index list --tag "genomics"
rayven index show <session_id>
```

This helps avoid reinventing solutions and builds on past learnings.
