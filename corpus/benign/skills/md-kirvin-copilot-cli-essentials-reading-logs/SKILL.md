---
name: reading-logs
description: Efficient log investigation across CI/CD systems — GitHub Actions, CircleCI, and Jenkins. Auto-detects the CI system in use and provides targeted fetch, filter, and triage patterns. Use when debugging failed builds, tracing deployment failures, or analyzing CI pipeline errors.
---

# Reading Logs

**Core principle:** Filter first, expand later. Never load an entire log into context. Start with the narrowest query that could surface the root cause, then widen only where needed.

## CI System Detection

Detect which system is in use by checking for config files:

```bash
# GitHub Actions
[ -d ".github/workflows" ] && echo "github-actions"

# CircleCI
[ -f ".circleci/config.yml" ] || [ -f ".circleci/config.yaml" ] && echo "circleci"

# Jenkins
[ -f "Jenkinsfile" ] || ls Jenkinsfile.* 2>/dev/null && echo "jenkins"
```

Multiple systems may coexist (different apps on the same repo). If ambiguous, ask which system the failing build is on.

## Topic Selection

| CI system detected | Load | File |
|--------------------|------|------|
| `.github/workflows/` exists | **GitHub Actions** | `references/github-actions.md` |
| `.circleci/config.yml` exists | **CircleCI** | `references/circleci.md` |
| `Jenkinsfile` exists | **Jenkins** | `references/jenkins.md` |
| Unknown / multiple | **Generic** | `references/generic.md` |

Load the reference for the detected system before beginning investigation.

---

## Universal Principles

### Filter first, expand later

1. Fetch only failed/error output — not the full log
2. Find the first error (root cause), not just the last one (often a symptom)
3. Get context (10–30 lines) around the error line
4. Trace back to what triggered it

### Error vs. symptom

The last error in a log is usually a cascade from an earlier root cause. Always scroll up from the first error occurrence, not the last.

```bash
# Find ALL error occurrences with line numbers
grep -n "ERROR\|FATAL\|error:\|failed\|exit code [^0]" build.log

# Go to the FIRST one, not the last
```

### Structured investigation

1. **What failed?** — job name, step name, exit code
2. **When?** — timestamp, position in the pipeline
3. **What was running?** — command, test, deploy step
4. **What was the error?** — exact message
5. **What triggered it?** — look 20–50 lines earlier
6. **Is it environmental or code?** — flaky network/resource vs. deterministic failure
