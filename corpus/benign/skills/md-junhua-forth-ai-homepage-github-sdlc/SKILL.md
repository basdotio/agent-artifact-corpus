---
description: Comprehensive GitHub SDLC management covering Issues, Projects, Pull Requests, Releases, Repositories, Branches, and more. Use when user mentions GitHub, gh CLI, or GitHub-related workflows.
trigger: github|gh\s|issue|pull request|pr|release|milestone|repository|repo\b
---

# GitHub SDLC Management

Comprehensive guide for GitHub Software Development Lifecycle management using the latest 2025 features, APIs, CLI commands, and MCP servers.

## When to Use This Skill

Use this skill when the user requests:
- Creating, managing, or querying GitHub **Issues**
- Working with GitHub **Projects** (V2)
- Managing **Pull Requests** and code reviews
- Creating or managing **Releases** and **Milestones**
- Repository, branch, or workflow management
- Using the **gh CLI** for GitHub operations
- Integrating with GitHub via **MCP servers**
- Any GitHub API or automation tasks

---

## 1. GitHub Issues (2025 Features)

### Latest Features (GA April 2025)

#### Sub-Issues
- **Nested hierarchy**: Up to 8 levels of parent-child relationships
- **Progress tracking**: Automatic aggregation across sub-issue hierarchy
- **Visual representation**: Tree view in project boards
- **Conversion**: Transform checklist items to sub-issues directly

**CLI Commands:**
```bash
# Create a sub-issue
gh issue create --title "Sub-issue title" --parent 123

# List sub-issues of a parent
gh issue view 123 --json subIssues

# Convert checklist to sub-issue (via web UI)
```

**REST API:**
```bash
# Create sub-issue
gh api -X POST /repos/{owner}/{repo}/issues \
  -f title="Sub-issue" \
  -f parent_issue_id=123

# Get sub-issues
gh api /repos/{owner}/{repo}/issues/123/sub_issues
```

#### Issue Types
- **Organization-level types**: Bug, Feature, Task, Spike, Infrastructure, Test, Documentation, Refactor
- **Customizable**: Up to 25 custom types per organization
- **Color coding**: Visual classification with 8 color options
- **REST API support**: Full CRUD operations via API

**CLI Commands:**
```bash
# List organization issue types
gh api /orgs/{org}/issue-types

# Create issue type
gh api -X POST /orgs/{org}/issue-types \
  -f name="Spike" \
  -f description="Research task" \
  -f color="purple" \
  -F is_enabled=true

# Set issue type
gh api -X PATCH /repos/{owner}/{repo}/issues/{number} \
  -f type="Feature"
```

#### Advanced Search
- **Complex queries**: AND, OR, parentheses for nested searches
- **Combined filters**: Mix issue metadata, labels, assignees, dates
- **Global search**: Search across all repositories or organization-wide

**Search Examples:**
```bash
# Complex AND/OR search
gh issue list --search "is:open (label:bug OR label:critical) assignee:@me"

# Date range queries
gh issue list --search "created:>=2025-01-01 updated:<2025-02-01"

# Advanced filters
gh search issues "repo:owner/repo is:issue is:open type:bug milestone:v1.0"
```

### Issue Management Commands

```bash
# Create issue with type
gh issue create --title "Title" --body "Description" \
  --label "priority:high" --assignee @me

# List issues with filters
gh issue list --state open --label bug --assignee @me

# Update issue
gh issue edit 123 --add-label "in-progress" --milestone "v2.0"

# Close issue
gh issue close 123 --comment "Fixed in #125"

# Reopen issue
gh issue reopen 123

# Transfer issue to another repo
gh issue transfer 123 owner/other-repo

# Pin important issues
gh api -X PATCH /repos/{owner}/{repo}/issues/123 \
  -f pinned=true
```

### Issue Templates & Forms

**Create issue template:**
```yaml
# .github/ISSUE_TEMPLATE/bug_report.yml
name: Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "triage"]
assignees:
  - username
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: input
    id: contact
    attributes:
      label: Contact Details
      description: How can we get in touch with you if we need more info?
      placeholder: ex. email@example.com
    validations:
      required: false
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us, what did you expect to happen?
      placeholder: Tell us what you see!
    validations:
      required: true
  - type: dropdown
    id: version
    attributes:
      label: Version
      description: What version of our software are you running?
      options:
        - 1.0.2 (Default)
        - 1.0.3 (Edge)
    validations:
      required: true
```

---

## 2. GitHub Projects V2 (2025)

### Custom Fields (Up to 50 per project)

**Field Types:**
- **Single Select**: Priority (High/Medium/Low)
- **Number**: Story points, effort estimates
- **Date**: Due dates, sprint start/end
- **Text**: Quick notes, descriptions
- **Iteration**: Week-by-week planning with breaks
- **Status**: Workflow states (New, In Progress, Done)

**CLI Commands:**
```bash
# List project fields
gh project field-list <number> --owner <org>

# Create custom field
gh project field-create <number> --owner <org> \
  --name "Story Points" \
  --data-type NUMBER

# Create single-select field
gh project field-create <number> --owner <org> \
  --name "Priority" \
  --data-type SINGLE_SELECT \
  --single-select-options "High,Medium,Low"

# Update item field value
gh project item-edit --id <item-id> \
  --project-id <number> \
  --field-id <field-id> \
  --number 8
```

### Views

**View Types:**
- **TABLE**: Spreadsheet-like view with columns
- **BOARD**: Kanban board grouped by status/field
- **ROADMAP**: Timeline view with date fields

**GraphQL API:**
```bash
# Create new view
gh api graphql -f query='
  mutation {
    createProjectV2View(input: {
      projectId: "PROJECT_ID"
      name: "Sprint Board"
      layout: BOARD_LAYOUT
    }) {
      projectV2View {
        id
        name
      }
    }
  }
'

# Update view filters
gh api graphql -f query='
  mutation {
    updateProjectV2View(input: {
      viewId: "VIEW_ID"
      filter: "is:open assignee:@me"
    }) {
      projectV2View {
        id
      }
    }
  }
'
```

### Automation Workflows

**Built-in Workflows:**
1. **Auto-add items**: Automatically add issues/PRs matching criteria
2. **Auto-archive**: Archive items when closed/merged
3. **Auto-set fields**: Set field values on item state changes

**CLI Configuration:**
```bash
# Add item to project
gh project item-add <number> --owner <org> \
  --url https://github.com/owner/repo/issues/123

# Auto-archive closed items
gh api graphql -f query='
  mutation {
    updateProjectV2(input: {
      projectId: "PROJECT_ID"
      autoArchive: true
    }) {
      projectV2 {
        id
      }
    }
  }
'
```

**GitHub Actions Integration:**
```yaml
# .github/workflows/project-automation.yml
name: Add issues to project
on:
  issues:
    types: [opened, labeled]

jobs:
  add-to-project:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/add-to-project@v1.0.2
        with:
          project-url: https://github.com/orgs/ORG/projects/1
          github-token: ${{ secrets.PROJECT_TOKEN }}
          labeled: bug, feature
```

### Insights & Charts

```bash
# Query project items for custom charts
gh api graphql -f query='
  query {
    organization(login: "ORG") {
      projectV2(number: 1) {
        items(first: 100) {
          nodes {
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
'
```

---

## 3. Pull Requests (2025 Features)

### New "Files Changed" Experience (Nov 2025)

**Batch Suggested Changes:**
- Click "Add suggestion to batch" for multiple suggestions
- Review all batched suggestions before committing
- Commit multiple suggestions at once

**Copilot Integration (Enterprise/Pro+):**
- AI-powered change grouping
- Contextual understanding of related changes
- Intelligent file organization

### Merge Queue (GA 2025)

**Features:**
- Ensures changes pass CI with latest main
- Prevents merge conflicts
- Shows optional status checks
- Supports all merge methods

**CLI Commands:**
```bash
# Enable merge queue for branch
gh api -X PUT /repos/{owner}/{repo}/branches/{branch}/protection \
  -f required_status_checks='{"strict":true,"contexts":[]}' \
  -f merge_queue='{"enabled":true}'

# Add PR to merge queue
gh pr merge 123 --merge --queue

# Check queue status
gh api /repos/{owner}/{repo}/merges/queues/{branch}
```

### Pull Request Commands

```bash
# Create PR
gh pr create --title "Feature X" \
  --body "Description" \
  --base main \
  --head feature-branch \
  --assignee @me \
  --reviewer user1,user2 \
  --label "enhancement"

# Create draft PR
gh pr create --draft

# List PRs
gh pr list --state open --author @me

# View PR details
gh pr view 123 --json title,body,reviews,files

# Review PR
gh pr review 123 --approve
gh pr review 123 --request-changes --body "Please fix X"
gh pr review 123 --comment --body "LGTM"

# Checkout PR locally
gh pr checkout 123

# Update PR branch
gh pr edit 123 --add-label "ready-for-review"

# Convert draft to ready
gh pr ready 123

# Merge PR (various methods)
gh pr merge 123 --merge       # Create merge commit
gh pr merge 123 --squash      # Squash and merge
gh pr merge 123 --rebase      # Rebase and merge
gh pr merge 123 --auto        # Auto-merge when checks pass
gh pr merge 123 --queue       # Add to merge queue

# Close without merging
gh pr close 123 --comment "Closing due to X"
```

### Code Review Features

```bash
# Request reviewers
gh pr edit 123 --add-reviewer user1,team1

# Dismiss review
gh api -X PUT /repos/{owner}/{repo}/pulls/123/reviews/{review_id}/dismissals \
  -f message="Outdated review"

# Enable auto-merge
gh pr merge 123 --auto --squash

# Add review comment on specific line
gh pr review 123 --comment \
  --body "Consider using const here" \
  --path src/file.ts \
  --line 42
```

---

## 4. Releases & Milestones

### Automated Release Notes (2025)

**Features:**
- Auto-generate from commits and PRs
- Categorize by labels (features, bugs, breaking changes)
- Exclude specific labels/users
- Semantic versioning support

**CLI Commands:**
```bash
# Create release with auto-generated notes
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --generate-notes

# Create release with custom notes template
gh release create v1.0.0 \
  --notes-file RELEASE_NOTES.md

# Create pre-release
gh release create v1.0.0-beta.1 --prerelease

# Upload assets
gh release create v1.0.0 --notes "Release notes" \
  dist/app.zip dist/app.tar.gz

# Edit release
gh release edit v1.0.0 --draft=false

# Delete release
gh release delete v1.0.0 --yes

# Download release assets
gh release download v1.0.0 --pattern "*.zip"
```

### Release Notes Configuration

**`.github/release.yml`:**
```yaml
changelog:
  exclude:
    labels:
      - ignore-for-release
    authors:
      - dependabot
  categories:
    - title: Breaking Changes 🛠
      labels:
        - breaking-change
    - title: New Features 🎉
      labels:
        - enhancement
        - feature
    - title: Bug Fixes 🐛
      labels:
        - bug
        - fix
    - title: Other Changes
      labels:
        - "*"
```

### Milestones

```bash
# Create milestone
gh api -X POST /repos/{owner}/{repo}/milestones \
  -f title="v2.0" \
  -f description="Major release" \
  -f due_on="2025-12-31T00:00:00Z"

# List milestones
gh api /repos/{owner}/{repo}/milestones

# Add issue to milestone
gh issue edit 123 --milestone "v2.0"

# Close milestone
gh api -X PATCH /repos/{owner}/{repo}/milestones/1 \
  -f state="closed"

# Get milestone progress
gh api /repos/{owner}/{repo}/milestones/1 --jq \
  '{open: .open_issues, closed: .closed_issues, progress: (.closed_issues / (.open_issues + .closed_issues) * 100)}'
```

---

## 5. Repository & Branch Management

### Repository Operations

```bash
# Create repository
gh repo create my-repo --public --description "My project"
gh repo create my-repo --private --clone

# Clone repository
gh repo clone owner/repo

# Fork repository
gh repo fork owner/repo --clone

# View repository
gh repo view owner/repo --web

# Set default branch
gh api -X PATCH /repos/{owner}/{repo} \
  -f default_branch="main"

# Archive repository
gh api -X PATCH /repos/{owner}/{repo} \
  -f archived=true

# Enable/disable features
gh api -X PATCH /repos/{owner}/{repo} \
  -f has_issues=true \
  -f has_projects=true \
  -f has_wiki=false

# Sync fork
gh repo sync owner/forked-repo \
  -b main \
  --source upstream/original-repo
```

### Branch Protection Rules

```bash
# Create branch protection rule
gh api -X PUT /repos/{owner}/{repo}/branches/{branch}/protection \
  -f required_status_checks='{"strict":true,"contexts":["ci"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":2}' \
  -f restrictions=null

# Rulesets (new approach, 2024+)
gh api -X POST /repos/{owner}/{repo}/rulesets \
  -f name="Protect main" \
  -f target="branch" \
  -f enforcement="active" \
  -f bypass_actors='[]' \
  -f conditions='{"ref_name":{"include":["refs/heads/main"]}}' \
  -f rules='[{"type":"required_status_checks","parameters":{"required_status_checks":[{"context":"ci"}]}}]'

# List rulesets
gh api /repos/{owner}/{repo}/rulesets

# Require signed commits
gh api -X PUT /repos/{owner}/{repo}/branches/{branch}/protection \
  -f required_signatures=true
```

### Branch Operations

```bash
# Create branch from issue
gh issue develop 123 --checkout

# List branches
gh api /repos/{owner}/{repo}/branches

# Delete branch
gh api -X DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}

# Compare branches
gh api /repos/{owner}/{repo}/compare/main...feature-branch
```

---

## 6. GitHub CLI (gh) Advanced Features

### Configuration

```bash
# Login
gh auth login

# Set default editor
gh config set editor vim

# Set protocol (HTTPS/SSH)
gh config set git_protocol ssh

# View configuration
gh config list

# Aliases
gh alias set co 'pr checkout'
gh alias set pv 'pr view --web'
```

### Extensions

**Popular Extensions:**
```bash
# Install extensions
gh extension install dlvhdr/gh-dash        # Interactive dashboard
gh extension install mislav/gh-branch      # Enhanced branch management
gh extension install k1LoW/gh-grep         # Search across repos
gh extension install seachicken/gh-poi     # Clean up local branches

# Browse extensions
gh extension browse

# Search extensions
gh extension search dashboard

# List installed extensions
gh extension list

# Upgrade extensions
gh extension upgrade --all
```

### API Access

```bash
# Call any GitHub API endpoint
gh api /user
gh api /repos/{owner}/{repo}/issues

# POST request
gh api -X POST /repos/{owner}/{repo}/issues \
  -f title="New issue" \
  -f body="Description"

# GraphQL queries
gh api graphql -f query='
  query {
    viewer {
      login
      repositories(first: 5) {
        nodes {
          name
        }
      }
    }
  }
'

# Paginate results
gh api --paginate /orgs/{org}/repos

# Output as JSON and process with jq
gh api /repos/{owner}/{repo}/issues | jq '.[] | {number, title}'
```

### Workflows (GitHub Actions)

```bash
# List workflows
gh workflow list

# View workflow runs
gh run list --workflow=ci.yml

# View specific run
gh run view 123456

# Re-run workflow
gh run rerun 123456

# Watch workflow run
gh run watch 123456

# Trigger workflow manually
gh workflow run deploy.yml -f environment=production

# Download workflow artifacts
gh run download 123456

# View workflow logs
gh run view 123456 --log
```

---

## 7. Model Context Protocol (MCP) Integration

### GitHub MCP Servers

**Official Servers:**
- **Git MCP Server**: Repository manipulation, commit history, diff operations
- **Filesystem MCP Server**: File operations with security constraints
- **GitHub API MCP Server**: Full GitHub API access via MCP

**Installation:**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token"
      }
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git"]
    }
  }
}
```

**Available Tools via MCP:**
- `create_repository`: Create new GitHub repository
- `get_file_contents`: Read file from repository
- `create_or_update_file`: Commit changes to files
- `push_files`: Batch commit multiple files
- `create_issue`: Create GitHub issue
- `create_pull_request`: Open pull request
- `fork_repository`: Fork a repository
- `create_branch`: Create new branch
- `search_repositories`: Search GitHub repositories
- `search_code`: Search code across GitHub
- `search_issues`: Search issues and PRs
- `search_users`: Find GitHub users

### GitHub Copilot + MCP (GA Aug 2025)

**Supported IDEs:**
- JetBrains (IntelliJ, PyCharm, WebStorm, etc.)
- Eclipse
- Xcode
- VS Code (via extensions)

**Configuration:**
```json
{
  "github.copilot.mcp.servers": {
    "custom-github-tools": {
      "command": "node",
      "args": ["/path/to/mcp-server.js"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 8. Common Workflows & Automation

### Issue Triage Workflow

```bash
# Daily triage script
#!/bin/bash

# Get all new unlabeled issues
gh issue list --label "!triage" --state open --json number,title | \
  jq -r '.[] | "\(.number): \(.title)"' | \
  while read issue; do
    echo "Triage issue: $issue"
    # Add triage label
    gh issue edit $(echo $issue | cut -d: -f1) --add-label "triage"
  done

# Auto-label based on title patterns
gh issue list --state open --json number,title,labels | \
  jq -r '.[] | select(.labels | length == 0) |
    if .title | test("\\[bug\\]|bug:"; "i") then
      "\(.number) bug"
    elif .title | test("\\[feature\\]|feat:"; "i") then
      "\(.number) enhancement"
    else empty end' | \
  while read num label; do
    gh issue edit $num --add-label "$label"
  done
```

### PR Review Reminder

```yaml
# .github/workflows/pr-review-reminder.yml
name: PR Review Reminder
on:
  schedule:
    - cron: '0 9 * * 1-5'  # Weekdays at 9 AM

jobs:
  remind:
    runs-on: ubuntu-latest
    steps:
      - name: Find stale PRs
        run: |
          gh pr list --state open --json number,title,createdAt,reviews \
            --jq '.[] | select((.reviews | length) == 0 and
              ((now - (.createdAt | fromdateiso8601)) > 86400))' | \
            while read pr; do
              gh pr comment $pr --body "⏰ Reminder: This PR needs review"
            done
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Release Automation

```yaml
# .github/workflows/release.yml
name: Create Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build artifacts
        run: |
          npm ci
          npm run build
          npm run package

      - name: Create Release
        uses: ncipollo/release-action@v1
        with:
          artifacts: "dist/*.zip,dist/*.tar.gz"
          generateReleaseNotes: true
          makeLatest: true
```

---

## 9. Best Practices

### Issue Management
1. Use **issue templates** for consistent bug reports and feature requests
2. Apply **issue types** at organization level for consistency
3. Use **sub-issues** for breaking down epics (max 8 levels)
4. Enable **advanced search** for complex queries
5. **Pin** important issues to repository overview

### Project Planning
1. Use **Projects V2** for cross-repo tracking
2. Create **multiple views** (Board, Table, Roadmap) for different audiences
3. Set up **automation workflows** to reduce manual work
4. Use **iteration fields** for sprint planning
5. Leverage **custom fields** for team-specific metadata

### Pull Request Workflow
1. Use **draft PRs** for work-in-progress
2. Enable **merge queue** for busy repositories
3. Require **status checks** before merge
4. Use **CODEOWNERS** for automatic reviewer assignment
5. Batch **suggested changes** for efficient reviews

### Release Management
1. Use **semantic versioning** (MAJOR.MINOR.PATCH)
2. Enable **auto-generated release notes**
3. Categorize changes with **labels**
4. Create **milestones** for version planning
5. Use **GitHub Actions** for automated releases

### CLI & Automation
1. Set up **gh aliases** for common operations
2. Use **gh extensions** for enhanced workflows
3. Leverage **GitHub Actions** for CI/CD
4. Use **MCP servers** for AI-powered automation
5. Create **shell scripts** for repetitive tasks

---

## 10. Troubleshooting

### Common Issues

**Issue: gh CLI auth fails**
```bash
# Clear credentials and re-auth
gh auth logout
gh auth login
```

**Issue: Project automation not working**
```bash
# Check GitHub Actions permissions
# Settings → Actions → General → Workflow permissions
# Enable "Read and write permissions"
```

**Issue: Merge queue stuck**
```bash
# Check merge queue status
gh api /repos/{owner}/{repo}/merge-queue/{branch}

# Remove item from queue
gh api -X DELETE /repos/{owner}/{repo}/merge-queue/{branch}/items/{item_id}
```

**Issue: Cannot set issue type**
```bash
# Ensure you have admin:org scope
gh auth refresh -h github.com -s admin:org

# Verify issue type exists
gh api /orgs/{org}/issue-types
```

---

## References

- [GitHub Issues Features](https://github.com/features/issues)
- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub REST API](https://docs.github.com/en/rest)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Evolving GitHub Issues (GA)](https://github.blog/changelog/2025-04-09-evolving-github-issues-and-projects/)

---

**Last Updated**: December 2025
**Version**: 1.0.0
