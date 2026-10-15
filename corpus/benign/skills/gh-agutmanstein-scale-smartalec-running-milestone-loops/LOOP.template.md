# Loop: <milestone> in <repo>

- **Lead:** <name>
- **Started:** <YYYY-MM-DD>
- **Instruction, verbatim:** "<what the user said>"
- **Loop dir:** <absolute path>. Every subagent reads this file first.

## Sources of truth
| Source | Where and how to read it | Wins on |
|---|---|---|
| Ticket comments (the latest decision) | <tracker / team / project>; e.g. Linear `list_comments` | scope changes and decisions |
| Ticket description and done-when | e.g. Linear `get_issue` | scope and done-when |
| Design doc | `<path>`, read by section with `<command or skill>`; cite `§N (doc:L123)` | behaviour, model and invariants |
| Code on the unit's branch | the worktree | what exists |

A conflict the table doesn't settle:
- record it in DECISIONS.md with the default taken and both citations;
- or, if it changes behaviour, put it in QUESTIONS.md, which blocks only that unit.

## Authority
Every row is required. An unanswered row means **not allowed**.

| Action | Allowed? | Conditions |
|---|---|---|
| Push branches, open PRs | | reviewer(s): |
| Merge PRs | | e.g. existing approval + all checks green, bottom-up, squash |
| Tracker writes (comments, state changes, new tickets) | | |
| Chat messages (to whom, what trigger) | | |
| Request reviewers, @-mention people | | |
| Reply to and resolve bot review threads | | |
| Prod runs, deploys, writes to shared data | | |
| Secrets and credentials | never | |
| Killing processes you didn't start | never | |

## Gates
Run them as commands and record the counts.

| Gate | Command | Baseline on main |
|---|---|---|
| tests | | |
| lint/format | | |
| types | | |
| integration / corpus | | |

## Code and PR conventions
- Code: <style rules: comments, shims, test naming>
- Commits: <format, trailers>
- PR description: <structure>; write it from the final diff.
- Release and version bumps: <only in release PRs?>

## Integration constraints
<Consumers that pin released versions, generated fixtures, cross-package callers. Say how the loop handles each, e.g. "worker changes needing unreleased API go in a patch file, applied by the release PR".>

## People
- **Reviewers:** <names and handles>
- **Don't contact:** <names>
- **Who answers which kind of question:** <names>
