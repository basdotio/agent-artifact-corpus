# Scripts Guide

Detailed documentation for the extraction scripts.

**All outputs are saved to `.claude/pr-review-comments/`**

## incremental_update.sh

**Purpose**: Fast, incremental extraction that tracks state.

**Usage**:
```bash
bash scripts/incremental_update.sh OWNER REPO_NAME
```

**Output**: `.claude/pr-review-comments/{repo}_inline_comments.ndjson`

**How it works**:
- Tracks last update timestamp in `.state.json`
- Fetches only PRs merged since last update
- Much faster than full extraction (10-30 seconds vs 5-10 minutes)
- Automatically runs full extraction on first use

**First run output**:
```
🆕 No previous update found for this repository
   Running FULL extraction...

Done! Extracted 450 comments from 100 PRs
✅ State saved. Next run will be incremental.
```

**Subsequent runs**:
```
📅 Last update: 2025-12-20T10:00:00Z
   Fetching only NEW PRs merged after this date...

📊 Found 3 new merged PRs
  ✓ PR #1234: 5 comments
  ✓ PR #1235: 2 comments

✅ Incremental Update Complete
💾 State updated. Next run will start from: 2025-12-28T10:30:00Z
```

---

## extract_pr_comments.sh

**Purpose**: Full extraction of all PR comments.

**Usage**:
```bash
bash scripts/extract_pr_comments.sh REPO_NAME
```

**Output**: `.claude/pr-review-comments/{repo}_inline_comments.ndjson`

**What it does**:
- Fetches all PRs from repository
- Extracts all inline code review comments
- Creates `.claude/pr-review-comments/` directory if needed

**Output format (NDJSON)**:
```json
{
  "repo": "backend",
  "owner": "earlyai",
  "pr_number": 1207,
  "file": "src/components/Dashboard.tsx",
  "line": 30,
  "author": "reviewer",
  "body": "Consider using a more descriptive variable name here",
  "created_at": "2025-12-24T08:55:51Z",
  "url": "https://github.com/earlyai/backend/pull/1207#discussion_r2645175276"
}
```

---

## sort_comments_by_filetree.sh

**Purpose**: Organize comments by directory structure.

**Usage**:
```bash
bash scripts/sort_comments_by_filetree.sh .claude/pr-review-comments/{repo}_inline_comments.ndjson
```

**Output**: `.claude/pr-review-comments/sorted/`

**What it creates**:
```
.claude/pr-review-comments/sorted/
├── summary.json                    # Overall statistics
├── src/
│   ├── core/config/
│   │   └── comments.json           # Comments for this directory
│   ├── telemetry/
│   │   └── comments.json           # 23 comments
│   └── ...
```

**Each `comments.json` contains**:
```json
{
  "directory": "src/telemetry",
  "generated_at": "2025-12-28T...",
  "comment_count": 23,
  "files": ["src/telemetry/ai-cost-telemetry.service.ts"],
  "comments": [...]
}
```

**Benefits**:
- Identifies hotspots (files with most feedback)
- Finds patterns by module/directory
- Enables per-directory best practices

---

## State Management

### State File: `.state.json`

Tracks extraction history:

```json
{
  "version": "1.0.0",
  "repos": {
    "owner/repo": {
      "last_update": "2025-12-28T10:30:00Z",
      "total_prs_processed": 103,
      "total_comments_collected": 457,
      "update_count": 4
    }
  }
}
```

### Reset State

To start fresh:
```bash
rm .state.json
bash scripts/incremental_update.sh owner repo  # Will run full extraction
```

---

## Troubleshooting

### GitHub API rate limit

```bash
gh api rate_limit  # Check current limit
```

Wait for reset or reduce PR count.

### jq not found

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt install jq

# Windows
winget install jqlang.jq
```

### No inline comments found

Many teams don't use inline comments. Alternatives:
1. Check PR reviews: `gh api repos/owner/repo/pulls/PR/reviews`
2. Check issue comments: `gh api repos/owner/repo/issues/PR/comments`
3. Direct codebase analysis instead of PR comments

### Script permissions

```bash
chmod +x scripts/*.sh
```

---

## Advanced Usage

### Filter by Author

```bash
gh pr list --repo owner/repo --state merged --author username
```

### Filter by Date Range

```bash
gh pr list --repo owner/repo --search "merged:2024-01-01..2024-12-31"
```

### Multiple Repositories

```bash
for repo in backend frontend mobile; do
  bash scripts/incremental_update.sh myorg $repo
done
```
