---
name: review
description: >
  Reviews implemented features against a specification file to verify the
  implementation matches requirements. Compares git diffs with spec criteria,
  optionally captures screenshots of critical UI paths, and produces a
  structured JSON report with issue severity classification. Use when a user
  wants to review work against a spec, validate an implementation, check if
  features match requirements, or verify work before merging. Triggers on
  "review the spec", "review my work", "validate against the spec", "check
  the implementation", "review this feature", "does this match the spec",
  "spec review", "review before merge". Do NOT use for implementing features
  (use the implement skill). Do NOT use for creating or writing specs (use
  the spec skill). Do NOT use for running tests or linting directly — the
  build skill handles validation.
---

# Purpose

Reviews implemented features against a specification file to verify the work matches requirements. Produces a structured JSON report with optional screenshots and issue severity classification. Does NOT fix issues — it only classifies and reports them. Does NOT run the test/lint suite — the build skill handles validation before review runs.

## Variables

- `argument` — Optional spec file path (e.g., `specs/feat-user-auth.md`). If omitted, the skill discovers the spec from the current branch name.

## Instructions

### Step 1: Determine the Spec File

Identify which spec to review against:

- **Explicit path** — If the user provides a spec file path, use it directly.
- **Branch-based discovery** — If no spec is provided, run `git branch --show-current` to get the current branch name, then search `specs/` for a matching file.
- **Ambiguous** — If multiple specs match or none match, list available specs in `specs/` and ask the user to confirm which one to review against.

### Step 2: Determine the Base Branch

Detect the default branch:

```bash
git remote show origin | grep 'HEAD branch' | sed 's/.*: //'
```

Falls back to `main` if detection fails.

### Step 3: Gather Context

Run these commands to understand what was built:

1. `git branch --show-current` — Identify the working branch
2. `git diff origin/<base-branch>` — See all changes made relative to base. Continue the review even if the diff is empty.
3. Read the identified spec file thoroughly. Extract:
   - Required features and acceptance criteria
   - UI/UX requirements (if any)
   - API or backend requirements (if any)
   - Edge cases or constraints mentioned

### Step 4: Determine Review Strategy

Based on the spec requirements, decide which review paths apply:

- **Code review** — Always performed. Compare the git diff against spec requirements to verify all stated criteria are addressed.
- **UI review** — Performed only if the spec describes user-facing features (pages, components, visual elements). Requires the application to be running and a browser automation tool to be available.

If UI review is needed, proceed to Step 5. Otherwise, skip to Step 6.

### Step 5: UI Review with Screenshots

This step validates visible functionality. The goal is to visually confirm that implemented features match the spec.

#### 5a: Prepare the Application

Check if a dev server is already running. If not, start one using the project's start command (discovered from justfile, package.json, or Makefile).

#### 5b: Capture Screenshots

Use available browser automation (Playwright MCP or similar) to navigate the application and capture screenshots:

- Navigate to the critical paths described in the spec
- Capture **1-5 targeted screenshots** that demonstrate the implemented functionality
- Focus on critical functionality — avoid screenshots of routine or unchanged areas
- If an issue is found, capture a screenshot of the issue specifically

Screenshot naming convention: `01_descriptive_name.png`, `02_descriptive_name.png`, etc.
Screenshot storage: Store screenshots in the `review_img/` directory. Create the directory if it does not exist.

#### 5c: Compare Against Spec

For each spec requirement with a UI component:
- Verify the visual implementation matches the described behavior
- Check layout, content, interactions, and error states as described
- Note any discrepancies as review issues

### Step 6: Classify Issues

For each issue found during review, classify its severity using the guidelines in `references/severity-guide.md`:

- **blocker** — Prevents release. The feature does not function as specified or will harm the user experience.
- **tech_debt** — Does not prevent release but creates debt that should be addressed in a future iteration.
- **skippable** — Non-blocking and minor. A real problem but not critical to the feature's core value.

Think carefully about impact before classifying. When in doubt, lean toward the less severe classification — only `blocker` should prevent a release.

### Step 7: Produce the Report

Output the review result as a JSON object. Return ONLY the JSON — no surrounding text, markdown formatting, or explanation. The output must be valid for `JSON.parse()`.

Use the schema defined in `references/output-schema.json`.

```json
{
  "success": true,
  "review_summary": "2-4 sentence summary of what was built and whether it matches the spec.",
  "review_issues": [],
  "screenshots": []
}
```

Key rules:
- `success` is `true` if there are no `blocker` issues
- `success` is `false` ONLY if there are `blocker` issues
- `screenshots` should always contain paths to captured screenshots, regardless of success status
- All paths must be absolute
- `review_summary` should read like a standup update: what was built, does it match, any concerns

## Workflow

1. **Determine spec** — Find the spec file from argument or branch-based discovery
2. **Base branch** — Detect the default branch
3. **Gather context** — Collect git diff and extract spec requirements
4. **Review strategy** — Decide code-only or code + UI review
5. **UI review** — If needed: start app, capture screenshots, compare against spec
6. **Classify** — Assign severity to each issue found
7. **Report** — Produce a JSON report with summary, issues, and screenshots

## Cookbook

<If: no spec file found matching the current branch>
<Then: list all files in `specs/` and ask the user to specify which spec to review against>

<If: browser automation not available>
<Then: skip UI review. Perform code-only review and note in the `review_summary` that visual validation was not performed. Do not fail the review for this reason.>

<If: application fails to start for UI review>
<Then: attempt to install dependencies first. If still failing, skip UI review and note it in the summary. Code review can still proceed.>

<If: git diff is empty>
<Then: continue the review. Check `git status` for uncommitted changes. If there truly are no changes, note this in the summary but still verify whether the current codebase satisfies the spec.>

<If: unsure about issue severity>
<Then: lean toward the less severe classification. Over-classifying as `blocker` creates unnecessary churn.>

<If: no issues found>
<Then: skip directly to the report. Output `"success": true` with an empty `review_issues` array.>

## Validation

Before finalizing the report, verify:

- Every spec requirement has been checked against the implementation
- All `blocker` issues genuinely prevent release (not just cosmetic preferences)
- Screenshots clearly demonstrate the critical functionality paths
- The JSON output is valid and parseable
- All file paths in the output are absolute

## Examples

### Example 1: Review with issues found

**Spec:** `specs/feat-user-auth.md`

**Actions:**

1. Read spec, gather git diff
2. Compare changes against spec requirements
3. Find 1 blocker (missing auth check on /admin route) and 1 tech_debt (hardcoded session timeout)
4. Classify both issues with severity and recommended resolution
5. Output JSON report with `"success": false` (unfixed blocker present)

### Example 2: Clean review — no issues

**Spec:** `specs/fix-health-endpoint.md`

**Actions:**

1. Read spec, gather git diff
2. All requirements met, no issues found
3. Output JSON report with `"success": true`, empty `review_issues`

### Example 3: Review with skippable-only issues

**Spec:** `specs/feat-dashboard.md`

**Actions:**

1. Read spec, gather git diff
2. Find 2 skippable issues (minor spacing, copy wording)
3. Output JSON report with `"success": true`, 2 skippable issues listed
