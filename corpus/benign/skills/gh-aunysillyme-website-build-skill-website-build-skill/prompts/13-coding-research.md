ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Research how to code this project's selected stack before writing website code.
Run as Builder after CHOOSE in [prompts/05-stack-and-build.md](05-stack-and-build.md)
and before IMPLEMENT. Require accepted research, a named mockup selection, and
site-work/stack.md with the selected stack and exact versions.

LEARN
- Read site-work/research/library/README.md, scope.md, coverage.md, sources.md,
  staleness.md, 08-languages-and-code.md, and checklists/14-code.md.
- Read the approved brief, browser targets, host constraints, and stack.md.
  Top up the chosen path and its unresolved questions against the saved library.
- Return stale or wrong library claims to Researcher with claim IDs and evidence;
  resume affected decisions after a corrected library receipt.

RESEARCH
- Open primary sources as of the ASK DATE: MDN, web.dev Baseline status, WHATWG
  and W3C specifications, TC39 finished proposals, TypeScript release notes, and
  the selected runtime, framework, package manager, and tools' official docs,
  changelogs, upgrade guides, and security advisories.
- Verify the exact selected language targets, runtime and framework versions,
  supported combinations, module format, and build or bundling defaults. For
  living standards, record the dated specification and browser targets; for an
  absent runtime, compiler, or framework, record NOT APPLICABLE with a reason.
- Research current HTML semantics and elements; CSS layout, container queries,
  cascade layers, and nesting; and JavaScript/TypeScript features for this stack.
  Record each proposed feature's Baseline or target browser/runtime support and
  the fallback or exclusion when support misses the project's targets. For
  compiler-only features, mark Baseline NOT APPLICABLE and cite compiler support.
  Verify implementation support separately from a proposal being finished.
- Identify the selected framework version's idioms, deprecated APIs, replacement
  patterns, and upgrade notes. Map organization rules to this project's routes,
  components, data, rendering, tests, and generated output.
- Select unit, integration, and end-to-end checks for the actual failure modes.
  Verify lint, format, and type-check tools and commands for the pinned versions.
  Give any inapplicable test level or tool a project-specific reason.
- Define dependency hygiene: justify each dependency, pin direct versions and
  toolchain versions, preserve the lockfile, use reproducible install commands,
  audit advisories, and record findings, owners, and update/recheck decisions.
- Research secure template and script handling for the actual stack: structural
  escaping by output context, script-safe serialization, URL scheme validation,
  input validation, and secrets supplied through the server-side environment.
  Keep secrets out of inline scripts, client bundles, source, and recorded output.
- For every dated claim, save the opened URL, publication/update date or unknown,
  actual access date, and supporting evidence under site-work/research/builder/.
  Record fetched-page receipts when opening sources using templates/evidence.md.
  Keep disagreements and unresolved claims explicit. Apply the canonical freshness
  windows and later-day rechecks before using a claim.

SAVE AND INGEST
Write site-work/coding-standards.md, opening with "Research as of <ASK DATE>".
Include these sections:
1. Pinned language, runtime, framework, and tooling versions or dated targets,
   with source URLs, source dates, access dates, and relevant claim IDs.
2. Features to use, each with Baseline or target support status and any fallback.
3. Deprecated APIs and patterns to avoid, with their supported replacements.
4. Project commands for unit, integration, and end-to-end tests, linting,
   formatting, and type-checking, including working directory and prerequisites.
   Label commands PLANNED until executed; link actual command output after Build.
5. Dependency policy, lockfile and pinning rules, install/audit commands, advisory
   handling, and the reason each dependency is needed.
6. Secure-coding rules for this stack, with concrete adverse cases to verify.
7. Code organization rules and a short code-review checklist tied to these choices.

Reopen the standards file and record its revision, learned rules, and applied
claim/check IDs in site-work/research/builder/learning.md before implementation.
Use [checklists/code-quality.md](../checklists/code-quality.md) during Build and
include its receipts and the standards file in the Reviewer packet. Revalidate
affected standards when selected versions, requirements, or source freshness change.

BLOCKED RESEARCH
If search or source access is unavailable, follow playbooks/research-and-memory.md:
return a query plan and unresolved-claim ledger for the selected stack, keep research
BLOCKED, and stop before implementation. Training memory or a previous library
does not pass current research. If file writing is unavailable, return named file
bodies for saving and read-back before the standards gate can pass.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
