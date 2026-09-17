---
name: shipment-tracker
description: Generate a visual report of what was shipped in GitHub repositories over a specified time period by analyzing merged PRs and closed issues.
license: MIT
compatibility: Requires gh CLI tool and Python 3.8+ with no additional dependencies (uses only stdlib)
metadata:
  author: GitHub Copilot
  version: "1.0"
allowed-tools: gh python3 python
---

# Shipment Tracker

Analyze one or more GitHub repositories to visualize what was shipped over a specified time period. Creates an interactive HTML report showing merged pull requests and closed issues with timeline visualization.

## When to Use

- User asks "what was shipped in the last X days/weeks/months"
- User wants to see a report of completed work across repositories
- User requests a "shipment report" or "delivery timeline"
- User wants to visualize team progress over a quarter or sprint
- User asks for examples: "show me what we shipped last quarter" or "what went out in the past 30 days"

## Instructions

### 1. Parse Time Period

Accept natural language time periods from the user:
- "past 30 days" / "last 30 days"
- "last week" / "past week"
- "last month" / "past month"
- "last quarter" / "past 90 days"
- "last 6 months"
- "since YYYY-MM-DD"
- "between YYYY-MM-DD and YYYY-MM-DD"

Convert to ISO 8601 date format for GitHub API queries.

### 2. Gather Repository Information

Ask the user which repositories to analyze:
- Single repo: `owner/repo`
- Multiple repos: `owner/repo1 owner/repo2`
- If not specified, use current repository from git remote

### 3. Fetch Data with GitHub CLI

For each repository, fetch:

**Merged Pull Requests:**
```bash
gh pr list \
  --repo owner/repo \
  --state merged \
  --search "merged:>=YYYY-MM-DD" \
  --json number,title,author,mergedAt,url,labels \
  --limit 1000
```

**Closed Issues:**
```bash
gh issue list \
  --repo owner/repo \
  --state closed \
  --search "closed:>=YYYY-MM-DD" \
  --json number,title,author,closedAt,url,labels \
  --limit 1000
```

### 4. Generate HTML Report

Use the helper script `scripts/generate-report.py` to create an interactive HTML page:

```bash
python3 scripts/generate-report.py \
  --repos "owner/repo1,owner/repo2" \
  --since "2024-01-01" \
  --until "2024-03-31" \
  --output shipment-report.html
```

The script will:
- Parse JSON data from gh CLI
- Group items by repository and type (PR/Issue)
- Create a timeline visualization
- Generate statistics (total shipped, by author, by label)
- Include filtering and sorting capabilities
- Create a standalone HTML file with embedded CSS/JS

### 5. Open the Report

```bash
open shipment-report.html
# or on Linux:
xdg-open shipment-report.html
```

## Output Format

The generated HTML report includes:

1. **Summary Section**
   - Total PRs merged
   - Total issues closed
   - Date range analyzed
   - Repositories included
   - Top contributors

2. **Timeline Visualization**
   - Interactive timeline showing when items were shipped
   - Color-coded by type (PR vs Issue)
   - Grouped by repository

3. **Detailed Lists**
   - Filterable and sortable tables
   - Links to GitHub items
   - Author information
   - Labels and metadata

4. **Charts**
   - Shipment velocity over time
   - Breakdown by repository
   - Contribution distribution

## Examples

### Example 1: Single Repository, Last 30 Days

**User:** "Show me what was shipped in the past 30 days"

**Agent Actions:**
1. Determine current repo: `gh repo view --json nameWithOwner`
2. Calculate date 30 days ago
3. Fetch merged PRs: `gh pr list --state merged --search "merged:>=2024-12-06" --json number,title,author,mergedAt,url,labels --limit 1000`
4. Fetch closed issues: `gh issue list --state closed --search "closed:>=2024-12-06" --json number,title,author,closedAt,url,labels --limit 1000`
5. Generate report: `python3 scripts/generate-report.py --repos "owner/repo" --since "2024-12-06" --output shipment-report.html`
6. Open report

### Example 2: Multiple Repositories, Last Quarter

**User:** "Create a shipment report for github/copilot and github/copilot-cli for last quarter"

**Agent Actions:**
1. Parse time: "last quarter" = past 90 days
2. Calculate date: 90 days ago from today
3. For each repo, fetch merged PRs and closed issues
4. Generate combined report: `python3 scripts/generate-report.py --repos "github/copilot,github/copilot-cli" --since "2024-10-07" --output shipment-report.html`
5. Open report

### Example 3: Custom Date Range

**User:** "Show what we shipped between January 1st and March 31st 2024"

**Agent Actions:**
1. Parse dates: since="2024-01-01", until="2024-03-31"
2. Fetch data for date range
3. Generate report: `python3 scripts/generate-report.py --repos "owner/repo" --since "2024-01-01" --until "2024-03-31" --output shipment-report.html`
4. Open report

## Notes

### Date Parsing

- Use ISO 8601 format (YYYY-MM-DD) for GitHub API queries
- "Last quarter" = 90 days
- "Last month" = 30 days
- "Last week" = 7 days
- Always calculate dates relative to current date

### API Limits

- GitHub CLI uses authenticated requests (higher rate limits)
- Each query returns up to 1000 results
- For very active repos, consider narrower time ranges
- The skill will warn if hitting limits

### Filtering Considerations

- Only includes **merged** PRs (not closed without merging)
- Only includes **closed** issues (not open)
- Draft PRs are excluded
- Private repositories require appropriate permissions

### Performance

- Fetching data for multiple repos is done in parallel when possible
- Large datasets (hundreds of items) may take 10-30 seconds to process
- Generated HTML is standalone and works offline after creation

### Customization

Users can request:
- Filtering by labels: "only show PRs with label:bug"
- Filtering by author: "only show @username's contributions"
- Grouping preferences: by week, by month, by repository
- Chart types: timeline, bar chart, pie chart

### Error Handling

If a repository is not accessible:
- Skip it and continue with other repos
- Show a warning in the report
- Don't fail the entire operation
