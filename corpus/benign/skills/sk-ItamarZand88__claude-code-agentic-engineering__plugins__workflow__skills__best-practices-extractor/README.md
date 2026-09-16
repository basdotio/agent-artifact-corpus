# Best Practices Extractor

Extract coding best practices from PR review comments to build living documentation of your team's standards.

## Overview

This skill helps you:
- **Extract** patterns from PR review comments
- **Categorize** feedback into best practice categories
- **Generate** structured documentation in `.claude/best-practices/`
- **Integrate** with code review for automatic compliance checking

## Quick Start

### 1. Extract PR Comments

```bash
cd plugin/skills/best-practices-extractor
bash scripts/incremental_update.sh OWNER REPO_NAME
```

### 2. Analyze and Generate Best Practices

Ask Claude to analyze the extracted comments:
```
Analyze the extracted PR comments and generate best practices documentation in .claude/best-practices/
```

### 3. Use in Reviews

The `/4_review` command and `code-reviewer` agent automatically validate against `.claude/best-practices/`.

## Prerequisites

- **GitHub CLI (`gh`)**: Install from https://cli.github.com/
  - Check: `gh auth status`
- **jq**: Install from https://stedolan.github.io/jq/
  - Check: `jq --version`

## Scripts

All outputs are saved to `.claude/pr-review-comments/`.

| Script | Purpose | Output |
|--------|---------|--------|
| `incremental_update.sh` | Fast updates with state tracking | `.claude/pr-review-comments/{repo}_inline_comments.ndjson` |
| `extract_pr_comments.sh` | Full extraction | `.claude/pr-review-comments/{repo}_inline_comments.ndjson` |
| `sort_comments_by_filetree.sh` | Organize by directory | `.claude/pr-review-comments/sorted/` |

See `references/scripts-guide.md` for detailed documentation.

## Output Structure

```
.claude/
├── pr-review-comments/              # Extracted PR comments
│   ├── {repo}_inline_comments.ndjson
│   └── sorted/                      # Organized by directory
│       ├── summary.json
│       └── src/.../comments.json
└── best-practices/                  # Generated best practices
    ├── README.md
    ├── naming-conventions.md
    ├── error-handling.md
    ├── type-safety.md
    ├── testing.md
    └── ...
```

## Update Schedule

| Team Size | Recommended Frequency |
|-----------|----------------------|
| Small (2-5) | Monthly |
| Medium (6-15) | Bi-weekly |
| Large (16+) | Weekly |

## Integration with Code Review

This skill **generates** best practices. They're consumed by:

- **`code-reviewer` agent**: Validates code against best practices
- **`/4_review` command**: Includes best practices compliance in reviews

**Workflow**:
```
Extract PR Comments → Generate Best Practices → Validate in Reviews
```

## Files

```
best-practices-extractor/
├── SKILL.md                        # Skill definition
├── README.md                       # This file
├── .state.json                     # Extraction state
├── references/
│   ├── default-categories.md       # Example categories
│   └── scripts-guide.md            # Detailed script docs
└── scripts/
    ├── extract_pr_comments.sh      # Full extraction
    ├── incremental_update.sh       # Incremental updates
    └── sort_comments_by_filetree.sh # Directory organization
```

## Related

- **Code Compliance Skill**: Validates code against best practices
- **`/4_review` Command**: Uses best practices in code reviews
- **`code-reviewer` Agent**: Reviews code against guidelines
