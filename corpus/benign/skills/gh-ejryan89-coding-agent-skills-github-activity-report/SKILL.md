---
name: github-activity-report
description: "Report one user's GitHub contributions in one organization month by month: pull requests authored and merged, commits, pull requests reviewed, and reviews submitted. Use it when asked what someone contributed or reviewed over recent months."
argument-hint: "ORG USER [--months N]"
allowed-tools: ["Bash({{PYTHON}} -B \"${CLAUDE_SKILL_DIR}/scripts/github_activity_report.py\" *)", "PowerShell({{PYTHON}} -B \"${CLAUDE_SKILL_DIR}/scripts/github_activity_report.py\" *)"]
---

# GitHub activity report

Produce a calendar-month contribution table for `USER` in the GitHub organization `ORG`, covering the last `N` months (default 12, at most 36) and ending with the current, partial month. Both arguments are required; if either is missing, ask for it rather than guessing.

## Run

The report needs an authenticated GitHub CLI (`gh auth status`) whose token can read the organization's repositories, including SSO authorization when the organization enforces it.

```bash
{{PYTHON}} -B "${CLAUDE_SKILL_DIR}/scripts/github_activity_report.py" --org "<ORG>" --user "<USER>" --months "<N>"
```

Searches are spaced to stay under GitHub's search rate limits, so a 12-month report takes a few minutes; about three for a user with nearly 2,000 reviewed pull requests. That is longer than many runtimes' default shell-command timeout, so give the command a timeout of at least 10 minutes, or run it in the background and wait for it to exit before reading its output. Do not start a second run while one is still going. Progress goes to stderr; the report goes to stdout.

## Output

Show the script's stdout to the user as-is: a Markdown table with one row per month and a **Total** row, followed by notes that say what each column counts. Do not recompute, round, or reinterpret the numbers, and pass on every note, including any `WARNING`, as written.

## Failures

The script fails closed and never prints a partial table. On failure it prints one line, `FAILED <reason> [<kind>]`, instead of the table and exits 1:

- `[prerequisite]` or `[authentication]`: install `gh` or run `gh auth login`.
- `[forbidden]`: the token cannot read some repositories or pull requests, often because it is not SSO-authorized for the organization.
- `[sso_partial]`: GitHub reported that it left out results from organizations the token is not SSO-authorized for. Authorize the token (`gh auth refresh`, or the SSO link on the token's settings page) and rerun.
- `[rate_limit]`: GitHub kept rate-limiting after retries, or asked for a long wait. Suggest rerunning later.
- `[network]`: `gh` could not reach GitHub. Suggest checking the connection and rerunning.
- `[incomplete]`: a search kept returning fewer results than GitHub reported, usually because results changed while it was paging or the search timed out. Suggest rerunning.
- `[api]` saying the listed users or repositories cannot be searched: `USER` or `ORG` does not exist or the token cannot see it. Suggest checking both logins' spelling (the organization's login, not its display name) and that the token can read the organization.
- Any other kind: report the message unchanged.

A `FAILED <type>: <message>` line with no `[<kind>]` is an unexpected failure the script did not classify; it also exits 1. Report it unchanged.

An argument the script refuses is not a `FAILED` line: the script queries nothing, prints nothing on stdout, writes its usage and the reason (such as `argument --org: not a valid GitHub login: 'My Org'`) on stderr, and exits 2. Name the argument and ask the user for a valid login (an organization's login, not its display name) or a month count from 1 to 36.
