---
name: asciinema-converter
description: Convert .cast recordings to .txt for analysis. TRIGGERS - convert cast, cast to txt, strip ANSI, batch convert.
allowed-tools: Read, Bash, Glob, Write, AskUserQuestion
---

# asciinema-converter

Convert asciinema .cast recordings to clean .txt files for Claude Code analysis. Achieves 950:1 compression (3.8GB -> 4MB) by stripping ANSI codes and JSON structure.

> **Platform**: macOS, Linux (requires asciinema CLI v2.4+)

> **Self-Evolving Skill**: This skill improves through use. If instructions are wrong, parameters drifted, or a workaround was needed — fix this file immediately, don't defer. Only update for real, reproducible issues.

## When to Use This Skill

Use this skill when:

- Converting .cast recordings to searchable .txt format
- Preparing recordings for Claude Code Read/Grep tools
- Batch converting multiple recordings
- Reducing storage size of session archives
- Extracting clean text from ANSI-coded terminal output

---

## Why Convert?

| Format | Size (22h session) | Claude Code Compatible | Searchable |
| ------ | ------------------ | ---------------------- | ---------- |
| .cast  | 3.8GB              | No (NDJSON + ANSI)     | Via jq     |
| .txt   | ~4MB               | Yes (clean text)       | Grep/Read  |

**Key benefit**: Claude Code's Read and Grep tools work directly on .txt output.

---

## Requirements

| Component     | Required | Installation             | Notes                 |
| ------------- | -------- | ------------------------ | --------------------- |
| **asciinema** | Yes      | `brew install asciinema` | v2.4+ for convert cmd |

---

## Workflow Overview

**IMPORTANT**: All phases are MANDATORY. Do NOT skip any phase. AskUserQuestion MUST be used at each decision point.

### Single File Mode (Phases 0-6)

| Phase | Purpose                    | Key Action                        |
| ----- | -------------------------- | --------------------------------- |
| 0     | Preflight check            | Verify asciinema CLI v2.4+        |
| 1     | File discovery & selection | AskUserQuestion: file to convert  |
| 2     | Output options             | AskUserQuestion: conversion opts  |
| 3     | Output location            | AskUserQuestion: save destination |
| 4     | Execute conversion         | `asciinema convert -f txt`        |
| 5     | Timestamp index            | Optional `[HH:MM:SS]` index       |
| 6     | Next steps                 | AskUserQuestion: what's next      |

Full implementation details: [Workflow Phases](./references/workflow-phases.md)

### Batch Mode (Phases 7-10)

Activated via `--batch` flag. Converts all .cast files in a directory with organized output.

| Phase | Purpose             | Key Action                               |
| ----- | ------------------- | ---------------------------------------- |
| 7     | Source selection    | AskUserQuestion (skip if `--source`)     |
| 8     | Output organization | AskUserQuestion (skip if `--output-dir`) |
| 9     | Execute batch       | Convert all with progress reporting      |
| 10    | Batch next steps    | AskUserQuestion: what's next             |

Full implementation details: [Batch Workflow](./references/batch-workflow.md)

---

## iTerm2 Filename Format

iTerm2 auto-logged files follow this format:

```
{creationTimeString}.{profileName}.{termid}.{iterm2.pid}.{autoLogId}.cast
```

**Example**: `20260118_232025.Claude Code.w0t1p1.70C05103-2F29-4B42-8067-BE475DB6126A.68721.4013739999.cast`

| Component          | Description                    | Example                              |
| ------------------ | ------------------------------ | ------------------------------------ |
| creationTimeString | YYYYMMDD_HHMMSS                | 20260118_232025                      |
| profileName        | iTerm2 profile (may have dots) | Claude Code                          |
| termid             | Window/tab/pane identifier     | w0t1p1                               |
| iterm2.pid         | iTerm2 process UUID            | 70C05103-2F29-4B42-8067-BE475DB6126A |
| autoLogId          | Session auto-log identifier    | 68721.4013739999                     |

---

## CLI Quick Reference

```bash
# Basic conversion
asciinema convert -f txt recording.cast recording.txt

# Check asciinema version
asciinema --version

# Verify convert command exists
asciinema convert --help
```

---

## Reference Documentation

### Internal References

- [Workflow Phases](./references/workflow-phases.md) - Single file mode phases 0-6 with full scripts
- [Batch Workflow](./references/batch-workflow.md) - Batch mode phases 7-10 with full scripts
- [Task Templates](./references/task-templates.md) - TodoWrite templates for single and batch modes
- [Post-Change Checklist](./references/post-change-checklist.md) - Verification after modifications
- [Anti-Patterns](./references/anti-patterns.md) - Common mistakes to avoid
- [Batch Processing](./references/batch-processing.md) - Patterns for bulk conversion
- [Integration Guide](./references/integration-guide.md) - Chaining with analyze/summarize

### External References

- [asciinema convert command](https://docs.asciinema.org/manual/cli/)
- [asciinema-cast-format skill](../asciinema-cast-format/SKILL.md)

---

## Troubleshooting

| Issue                       | Cause                     | Solution                                       |
| --------------------------- | ------------------------- | ---------------------------------------------- |
| convert command not found   | asciinema too old         | Upgrade: `brew upgrade asciinema` (need v2.4+) |
| asciinema not installed     | Missing CLI               | `brew install asciinema`                       |
| Empty output file           | Corrupted .cast input     | Verify .cast file has valid NDJSON structure   |
| Conversion failed           | Invalid cast format       | Check header line is valid JSON with `jq`      |
| numfmt not found            | macOS missing coreutils   | Use raw byte count or `brew install coreutils` |
| stat syntax error           | Linux vs macOS difference | Script handles both; check stat version        |
| Batch skipping all files    | All .txt already exist    | Use `--skip-existing=false` to reconvert       |
| Permission denied on output | Directory not writable    | Check output directory permissions             |


## Post-Execution Reflection

After this skill completes, check before closing:

1. **Did the command succeed?** — If not, fix the instruction or error table that caused the failure.
2. **Did parameters or output change?** — If the underlying tool's interface drifted, update Usage examples and Parameters table to match.
3. **Was a workaround needed?** — If you had to improvise (different flags, extra steps), update this SKILL.md so the next invocation doesn't need the same workaround.

Only update if the issue is real and reproducible — not speculative.
