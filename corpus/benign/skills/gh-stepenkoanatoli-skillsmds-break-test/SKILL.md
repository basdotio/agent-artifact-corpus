---
name: "break-test"
description: Adversarially probe a project for realistic build and test failures (clean-checkout builds, lockfile and dependency drift, stale generated code, missing env vars, toolchain mismatches, order-dependent or flaky tests, races, timezone and locale assumptions, offline installs, permissions, resource limits), prove each one with a repro command, then apply minimal fixes as separate commits, keeping only fixes that demonstrably remove the failure and keep the build green. Use whenever the user asks to break-test, chaos-test, stress-test or harden a build, run a pre-release reliability check, hunt flaky tests, or asks "what could break our CI / our build", even if they never say "break-test". Not for debugging a single known bug or reviewing a diff. Uses Research-Kit (github.com/StepenkoAnatoli/Research-Kit) for every fact about an external tool that a finding's cause or a recommendation rests on.
compatibility: Any coding agent with shell and file access. No vendor-specific tools are assumed. Git is required for the default workflow; a non-git fallback is described. Runnable recipes for the probes are in references/probe-recipes.md; the Research-Kit binding is in references/research-kit.md.
---

# Break Test

## Purpose

Identify the realistic ways this project's build or test suite can fail, demonstrate each failure with a reproducible command, and apply the smallest fix that removes it. A fix is retained only if it removes the demonstrated failure and leaves the build and tests at least as healthy as the recorded baseline. Everything that cannot be fixed under those conditions is reported as a risk.

This procedure deliberately breaks things while guaranteeing that nothing is left broken. The isolation steps in section 0 are what make both possible; complete them before any probe or fix.

## Principles

1. **Reproduce before reporting.** A failure counts only after it has been reproduced with a command whose output you observed. A problem suspected from reading code is a risk marked *unverified*, never a finding.
2. **A probe can manufacture a failure.** Probes change the environment, and the change itself can break tests the project never claimed to support under that change. Before a failure under a probe becomes a finding, run the control described in section 3; a failure that disappears when the probe's own setup is corrected is a *probe defect*, reported as such.
3. **Never damage the user's work.** Probes and fix attempts run in an isolated copy. The user's checkout, uncommitted changes, and environment outside the project are never modified except by the fix commits described in section 0.
4. **Minimal change.** Each fix is the smallest edit that removes the root cause. No new dependencies, refactors, or behaviour changes without the user's decision.
5. **Verified means both checks passed.** A fix is verified only when the repro passes *and* the gate shows no new failures against the baseline. A green gate alone proves nothing was broken, not that anything was fixed.
6. **Null results are results.** A probe that finds nothing is evidence of coverage and goes in the report with its command. A run whose findings are all Low, or empty, is a legitimate outcome; do not promote a severity or invent a risk to make the run look productive.
7. **External facts are fetched, not recalled.** The build's own behaviour is observed by running it. How a third-party tool behaves (what a package manager's policy does, what a runtime's default is, what an advisory covers, what a flag enforces) is an external fact: when a finding's cause, a remaining risk's recommendation or a *Not probed* justification rests on one, that fact is closed through Research-Kit so it traces to a fetched page, and the report cites the evidence row. With no kit available the claim is written as *unverified* and never promoted. See *External facts* below.
8. **Report exactly what was done.** See *Reporting standards*. The report must not claim more coverage, more certainty, or more success than the evidence supports.

## Definitions

- **Gate:** the set of commands that must pass for a change to be retained, normally install, build, typecheck/lint, and tests.
- **Fast gate:** a subset of the gate (build plus the tests covering the touched area) used per fix when the full gate is slow.
- **Baseline:** the gate's results on the untouched code, recorded before any change, as the *set of failing test identifiers*, not a count.
- **Probe:** a controlled attempt to trigger a specific class of failure.
- **Control:** the same tests run with the probe's condition removed or its setup corrected, used to decide whether a failure belongs to the project or to the probe.
- **Finding:** a reproduced failure with a recorded repro command, root cause, severity, and likelihood.
- **Probe defect:** a failure caused by the probe's own setup, shown by a control. Recorded in the report, never as a finding.

## Decisions that are the user's

Ask the user and wait for an answer before:

- Any probe that could reach real external services: deployments, package publishing, production databases, paid APIs, email or messaging. If unsetting an environment variable could make the code fall back to a production URL or real credentials, do not run the probe; record it as a finding.
- Any fix that requires a decision the user should own (section 4, step 2).
- Any single probe expected to run longer than approximately 15 minutes.
- Working on a project that is not under version control.

When nobody can answer (an unattended or scheduled session), do not assume consent and do not block: skip the item, finish everything that does not depend on it, and record it under *Not probed* or *Remaining risks* with the decision that is needed.

## Procedure

### 0. Isolate the work

Isolation serves two purposes: probes must not affect the user's work, and every retained fix must be individually reviewable and revertible. Choose the setup that satisfies both in the current environment.

1. Run `git status`. If there are uncommitted changes, tell the user they are excluded from testing and ask whether they want to commit first.
2. **Default setup:** perform all work in a separate git worktree on a new branch: `git worktree add ../<repo>-break-test -b break-test/<YYYY-MM-DD>`. Commit each retained fix there as its own commit. The user's checkout is not modified.
3. **Pinned-branch setup:** if the environment restricts the session to a single branch or does not permit new branches, run every probe and fix attempt in a temporary clone. Apply each fix that passed there to the current branch by copying the verified file and checking `git diff` before committing, as its own commit with a message naming the finding. Do not squash fixes. Before reporting, run the full gate again in the real checkout, because a fix can behave differently in the clone and in the checkout; if it fails there, revert that commit.
4. Keep every throwaway clone, cache, and temporary directory under one absolute path outside the checkout, and refer to it by that path. State-changing git commands (`checkout -- <file>`, `reset`, `clean`, `stash`) are run only after confirming the current directory is a throwaway copy. In the user's checkout, the only git operations during the run are `status`, `diff`, `add`, and `commit`.
5. A worktree or clone lacks local-only files (`.env`, credentials, build output, installed dependencies). If the gate cannot run without them, record that as a clean-checkout finding. Copy such files in only with the user's confirmation and never commit them.
6. Run probes that deliberately corrupt state (lockfiles, caches, generated files) in a separate throwaway clone, or restore your worktree or clone with `git reset --hard && git clean -fd` before continuing. These commands are acceptable in your own worktree or clone and never in the user's checkout.
7. Do not modify anything outside the project: no global installs, no changes to shell profiles, `~/.npmrc`, global git configuration, system permissions, or network settings, and no clearing of shared caches. Simulate conditions per command instead: inline environment variables, a temporary cache directory, offline flags, `ulimit` in a subshell. If a probe requires a tool the project does not have (a random-order plugin, the declared toolchain version), install it into a session-local directory, never into the project's manifest or the machine's global state, and record that the environment lacked it.
8. **No version control:** with the user's confirmation, copy the project to a temporary directory and initialise a git repository there so the rest of the procedure applies. Deliver fixes as a patch file rather than commits.

### 1. Map the build

Record the following before probing:

- Build system, package manager, and declared toolchain versions (`.nvmrc`, `.node-version`, `engines`, `.python-version`, `go.mod`, `rust-toolchain`, Dockerfile base images), together with the versions CI actually uses and the versions present in your environment. A gap between declared and present is itself the first toolchain probe: run the gate on the declared version, installed session-locally if necessary, and note whether the project *detects* the wrong one.
- The environment you are in: operating system, whether you run as root, CPU count, and which CI steps cannot run on it (another operating system, a GPU, a signing identity). These go in the report, because they bound what the run could show.
- Exact commands for install, build, typecheck/lint, code generation or formatting checks, and each test tier. Prefer the CI configuration over the README as the source of truth, and record any drift between them as a finding. In a monorepo, record per-package commands and whether the root command covers all packages.
- Services the tests depend on (databases, caches, containers, emulators) and whether the suite can run without them.
- Approximate duration of the full suite.

Define the gate from these commands. Tests alone are insufficient because a change can pass the tests and still break the build or the type checker. If the full gate exceeds approximately 10 minutes, also define a fast gate for per-fix checks, and run the full gate at checkpoints and at the end.

### 2. Record the baseline

Run the full gate on the untouched code three times. Use the test runner's machine-readable reporter and save the **set of failing test identifiers** for each run; every later retain-or-revert decision is a set comparison against this record, because an unchanged count can hide one test that started failing while another started passing. Run one test suite at a time on the machine: a second suite running concurrently is a timing probe nobody asked for, and a failure it causes will be misattributed.

- **Stable and green:** retain a fix only if the gate remains green.
- **Consistent failures:** record them as findings (or, when the project documents and checks them elsewhere, as context). Retain a fix only if it introduces no failures beyond the baseline; otherwise every fix would be reverted for a cause it did not introduce.
- **Intermittent failures:** record them as findings with the observed failure rate. When such a test fails after a fix, rerun up to twice before attributing the failure to the fix.
- **Gate cannot run** (install or build broken): this is the primary finding. Report it and ask the user how to proceed, since no fix can be verified until it is resolved.

### 3. Probe

Work through the list in order; it is ordered approximately by how often each cause breaks real builds. Skip what does not apply and record each skip with its reason. Use the commands appropriate to the project's ecosystem; those in parentheses are examples, and `references/probe-recipes.md` has tested shell recipes. Record the exact command for every probe, including probes that found nothing, so the user can rerun them.

**The control, before any failure counts.** When a probe produces a failure the baseline did not have, rerun the failing tests under the same probe with the probe's own setup corrected, or run the same command without the probe condition. If the failure vanishes, it is a probe defect: record it under *Probe defects*, fix the probe, run it again, and only then read the result. Known traps: a fresh network namespace has its loopback interface down, which breaks every test that uses a local fake server; two suites running at once produce timeouts; a shortened `PATH` hides the toolchain itself.

1. **Clean checkout.** Fresh clone, empty caches, build and test. Detects uncommitted files the build depends on, gitignored generated files, and reliance on cached artifacts.
2. **Lockfile and install integrity.** Strict install from the lockfile (`npm ci`, `pnpm install --frozen-lockfile`, `uv sync --locked`, fresh virtualenv with `pip install --require-hashes`, `cargo build --locked`, `go mod verify` and `go mod tidy -diff`). Detects lockfiles out of sync with manifests, unpinned ranges, missing hashes. Read the installer's warnings as well as its exit code: install-script policies, engine warnings and deprecations are findings when they contradict what the repository says it does.
3. **Generated code and formatting.** Rerun every code generation and formatting step the project defines, then `git status --porcelain` and `git diff --exit-code`. Scripts the project labels "maintainer-only, never run in CI" are exactly the ones to run here, in the throwaway clone: they are the ones nothing else checks. Detects committed output that has drifted from its source, a frequent CI-only failure.
4. **Toolchain versions.** Compare declared, CI, and local versions. Build with the declared version, and with another version that is available or installable. If the gate *succeeds* under a version the project declares unsupported, that is a finding: the constraint is not enforced, and a contributor can get a green run that proves nothing about the shipped runtime.
5. **Environment variables and configuration.** Enumerate every environment variable and configuration value the build and tests read (search for the runtime's accessor, for example `process.env`, `os.environ`, `os.Getenv`). Run with the environment emptied to the minimum (`env -i PATH=... HOME=...`), then with each required value unset and empty, inline and per command, subject to the rules above. Detects crashes without a clear message, silent defaults, and tests that require secrets.
6. **Test isolation and order.** Run tests in random order with a recorded seed, at least twice with different seeds, and individually (`pytest -p randomly`, `jest --randomize`, `vitest --sequence.shuffle --sequence.seed=N`, `go test -shuffle=on`, `rspec --order random`). Detects shared state, leftover files or database rows, and leaking global mocks. A runner configured with isolation off is the prime candidate.
7. **Flakiness and races.** Repeat the suite or the timing-sensitive files many times (`go test -race -count=20`, `pytest --count=20`, or a shell loop of ten or more), one run at a time, and in parallel only where the project itself runs in parallel. Detects timing assertions, sleeps, unawaited asynchronous work, fixed ports. Report the rate numerically.
8. **Locale, timezone, platform.** Run with a timezone far from UTC (`TZ=Pacific/Kiritimati`, `TZ=America/St_Johns`), with `LANG=C LC_ALL=C`, and with a non-English locale. Clone with `-c core.autocrlf=true` and rerun the checks that hash or compare committed bytes. Search for hardcoded path separators, imports whose case does not match the filename, line-ending assumptions, and shell-specific scripts.
9. **Network and registry.** `npm ci --offline` against an empty cache fails for every project and proves nothing; probe instead what must work *after* install: run every provisioning step and the whole test suite with external network removed and loopback up (`unshare -rn` plus bringing `lo` up, see the recipes). Detects tests and setup scripts that silently reach the network, and provisioning that cannot explain what it needs. Search for build-time downloads: postinstall scripts, `curl` in Makefiles, unpinned container tags, `latest`.
10. **Permissions and filesystem.** Executable bits on committed scripts, writes to absolute or read-only paths, temporary files that are not cleaned up, very long paths, half-made state directories left by an interrupted run. If you are root, permission probes are void (permission bits are not enforced for root): record them as not probed with that reason rather than reporting a pass.
11. **Resource limits.** Constrain workers and memory where the runner supports it (`--maxWorkers=1`, `NODE_OPTIONS=--max-old-space-size=512`, `ulimit -n 256` in a subshell). Detects tests that pass only on large machines. Never run anything that could hang or exhaust the host.
12. **Dependency health.** The ecosystem's audit tool for known-vulnerable or deprecated packages, separately for production and development dependencies, duplicate or conflicting versions, circular imports. Normally report-only (section 4, step 2), with the proposed fix and whether it is a major change.

Stop when the list is complete. Do not describe the search as exhaustive; the report's *Not probed* section records where it was not.

### 4. Fix

For each finding, one at a time:

1. Record the repro command, root cause, severity, and likelihood. When the root cause is a tool's documented behaviour rather than something the repro shows, the cause names the Research-Kit evidence row that establishes it (section *External facts*); until then it reads "likely cause".
2. Decide whether the fix is yours to make. Apply it if the change is small, local to the repository, and does not require a decision the user should own. Report instead of fixing when the fix would add a dependency, bump or downgrade a version, change public behaviour or an API, change a security policy (which install scripts run, what is trusted), touch CI secrets or infrastructure outside the repository, or require a substantial refactor.
3. Apply the smallest change that removes the root cause.
4. Rerun the repro. If it still fails, the fix is ineffective: revert it and record the attempt.
5. Run the gate (fast or full) and compare the failure set with the baseline. On a new failure, rerun up to twice if that test was intermittent at baseline; if it still fails, revert and record which check failed.
6. If both the repro and the gate pass, commit with a message naming the finding. Follow the repository's own commit convention when it defines one (AGENTS.md, CONTRIBUTING, recent history); the finding's repro and verification belong in the message body.

Do not retain a fix that works by weakening the checks: deleting, skipping, or marking a test as expected-failure; loosening an assertion; raising a timeout without showing why the previous value was wrong; adding retries to mask flakiness; disabling a lint rule or warning instead of fixing its cause; regenerating an entire lockfile to resolve one entry. Such changes pass the gate while making the build less trustworthy. If weakening a check is genuinely the correct outcome, report it as a recommendation for the user to decide.

### 5. Finish

1. Run the full gate on the final state. If it fails although each fix passed individually, bisect the fix commits to identify the combination that fails, revert it, and rerun.
2. Remove temporary clones, caches, and probe artifacts. Confirm that the user's checkout is unchanged apart from the fix commits and contains no probe artifacts.
3. In the default setup, leave the worktree and branch in place for review and state how to inspect and remove them (`git diff <base>...break-test/<date>`, `git worktree remove <path>`).
4. Write the report.

## External facts: Research-Kit

Research-Kit (`https://github.com/StepenkoAnatoli/Research-Kit`) fetches and caches every cited page under `research/raw/`, keeps a hash-chained ledger of where each capture came from, and gates on whether every stated unknown points at real evidence. The break test uses it for the facts the probes cannot observe. In the first run those were: what npm 11 does with an install script its policy does not name, what esbuild's postinstall does and whether skipping it matters on another platform, and what `engine-strict` enforces. Each had shaped a finding's cause or a recommendation, and each was closed from the owner's pages in about fifteen minutes with a keyless transport that spent nothing.

The binding is a rule, not an option:

1. **Check the kit first.** `node "$HOME/.agents/research-kit/bin/doctor.mjs"` from the repository root must end with `READY`. If the kit is not deployed but the user's checkout of it is present, run it from there for the session (`RESEARCH_KIT_HOME=<checkout>/research-kit`, `RESEARCH_KIT_TRANSPORT=http-keyless`) and say so in the report; do not install it into the user's machine or project without asking. If neither exists, every external fact in the report is marked *unverified* and the report says the kit was unavailable.
2. **Read doctor's whole verdict.** A blocker it raises about the repository itself (for example a private-key block in a test fixture) is a finding for the report even when the research can proceed.
3. **One nested research project per break test,** under the repository's research convention (`docs/research/<YYYY-MM-DD>-break-test-external-facts/` unless the project records another), scaffolded with `new-project.mjs`, never at the repository root. Every kit command runs from inside that folder.
4. **The kit's loop, scoped to the facts the probes left open:** `decompose.mjs --dry-run`, mark every map row (dismissing with a reason is fine, omitting is not), one unknown `U-n` per external fact a cause or recommendation rests on, the owner's pages named directly in `plan.json` (official documentation, the tool's repository, the advisory), `research.mjs --dry-run` then collect, rewrite each `Finding` with a `[quote: ...]` copied from the capture on one line, `preflight.mjs` until `PASS`, `brief.mjs` and answer its two judgement sections.
5. **Cite.** A cause or recommendation that rests on an external fact names its `E-nn` row; the report's overview names the research project. `PASS` proves the pages were fetched and the claims point at them; it does not prove the claims true or the risk important. That judgement stays yours.
6. **Do not use the kit for the project's own behaviour** (run the build), for facts the repro already shows, or for stable, uncontroversial facts (that `npm ci` needs a registry). Three to five unknowns is the normal size.
7. **Commit the corpus with its ledger:** `git add <project>/` and `git add -f <project>/research/raw/.fetches.jsonl`, in a commit of its own, before the report commit that cites it.

`references/research-kit.md` holds the tested recipe, including what to do when an owner's page renders client-side and the keyless capture holds only a title (take the documentation's source file from the tool's repository at the exact version tag), and how the kit's commands map to exit codes.

## Severity and likelihood

Severity:

- **Critical:** fails on a clean checkout or in CI today, or could ship a broken artifact or affect production data.
- **High:** fails under common conditions: a new development machine, a CI cache miss, a different timezone, a registry outage.
- **Medium:** fails under plausible but less common conditions, or fails intermittently at a low rate.
- **Low:** hygiene. Unlikely to cause a failure, but makes failures harder to diagnose, or lets a wrong setup pass silently.

Likelihood: **Likely** (expected within normal operation), **Possible** (requires a specific but realistic condition), **Unlikely** (requires an unusual combination of conditions). Rank remaining risks by severity, then likelihood. An all-Low result is reported as all-Low.

## Reporting standards

- Every statement about the build is supported by a command you ran and output you observed. Quote the relevant output lines; do not paraphrase error messages.
- Distinguish what was observed from what was inferred. Where the root cause is not certain, write "likely cause" and state what would confirm it.
- Report intermittent failures numerically (for example, "failed 3 of 20 runs"), not as fixed or passing.
- Describe a fix as verified only if both the repro and the full gate passed. If only the fast gate was run, say so.
- Write repro commands relative to the repository root, without session-specific paths, so the user can run them.
- List every probe that was run, including those that found nothing. A null result is evidence of coverage.
- Name every probe defect and what corrected it; a report that silently drops a probe's false failures is also hiding how the probe was run.
- Every claim about a third-party tool's behaviour names its Research-Kit evidence row (`E-nn`), or is marked *unverified* with the kit's status (not deployed, not ready, no transport) stated once in the overview.
- Record where the environment differed from CI (operating system, root, toolchain installed for the run) and what that prevented.
- If the session ends early because of time, budget, or a blocker, state which steps did not run.
- Do not invent commit identifiers, command output, test counts, or durations. If a value was not captured, say that it was not captured.
- Do not inflate severity to make the report appear more useful, or understate it to make the build appear healthier.

## Report template

Use this structure. Keep entries brief and lead with the repro command.

**Overview:** stack, CI platform, gate commands and duration, environment used for the run, baseline result (consistent and intermittent failure sets), isolation setup used, where the fix commits landed (branch and commit identifiers), and the Research-Kit project that holds the external facts (or the kit's status if none could be made).

**Findings:** one entry each, in this form:

> **[F3] Tests fail when TZ is not UTC** (High, Likely)
> Repro: `TZ=Pacific/Kiritimati npm test -- src/billing`
> Observed: `expected "2026-10-03" to equal "2026-10-04"` in `invoice.test.ts:41`
> Cause: `invoiceDate()` constructs a date from local components; CI runs in UTC, developer machines do not. (When the cause is a tool's documented behaviour: "npm skips uncovered install scripts, E-08".)
> Action: Fixed, commit `a1b2c3d` (use `Date.UTC`).
> Verification: repro passes; full gate green, failure set identical to baseline.

**Applied fixes:** commit, finding ID, files changed.

**Rejected fixes:** what was attempted and which check failed.

**Remaining risks:** ranked, each with a recommended fix and the decision required from the user. Mark anything not reproduced as *unverified*.

**Probe defects:** each probe whose setup produced a false failure, what showed it, and the corrected result.

**Probes run:** a table of every probe, its command, and its result, null results included.

**Not probed:** each skipped probe and the reason (not applicable, requires another operating system, running as root, requires credentials, too slow, nobody to confirm, session ended).

**Summary:** two to four sentences on the current resilience of the build, the single most important open risk or decision, and how to review what was changed.

## Running this skill

The judgement steps (what counts as a finding, whether a failure belongs to the probe, whether a fix weakens a check, the report's wording) deserve the strongest reasoning available. Probe execution is mechanical and can be delegated to cheaper workers, one suite per machine at a time, each returning the exact command, exit code, and failure set rather than a verdict. The Research-Kit project is judgement work too: the map, the unknowns and the rewritten findings decide what the report may claim.

## Provenance

Revised on 2026-10-03 after a complete run of the previous version on the MoonAliza repository (report: `docs/evidence/2026-10-03-break-test.md` there). Each addition in that revision names the observation behind it in `references/probe-recipes.md`, section "What the first run taught". The Research-Kit binding was added the same day after the run's two unverified facts were closed through the kit (`docs/research/2026-10-03-break-test-external-facts/` there, gate `PASS`).
