---
name: agent-config-audit
description: Use when auditing what a coding agent is allowed to do ("audit my Claude Code config", "what can this agent actually do", "check my permissions", "is it safe to open this repo with an agent", "why does it never ask me anything anymore"), across permissions, hooks, MCP servers, subagents, skills and instruction files at every scope. Read-only by default; any change it proposes may only narrow what the agent can reach, and is applied one finding at a time on explicit approval.
---

# Agent Config Audit

## Overview

Every other audit points at the codebase. This one points at the agent.

A session runs under a permission set, a hook set, a group of MCP servers and a pile of
instruction files, assembled from several files at several scopes. This skill resolves that
assembly into one effective configuration, records which file every entry came from, and
judges the result against a fixed catalogue of thirty rules. It reads configuration, not
code: what it judges is the reach that configuration authorises.

It does not read the source of an MCP server package, does not audit dependencies, and does
not look for vulnerabilities in the project itself. Those are separate audits, and folding
any of them in here turns a fast, reproducible config audit into a long one.

## Core Principle

**No finding without evidence. No evidence without verification. No change without
explicit per-finding approval, and no approved change may ever widen the
configuration.**

Every grant is inventoried with the file it came from. Every finding is handed to an
agent told to refute it. Nothing is written that the user did not approve for that specific
finding, and what is written may only ever narrow the agent's reach.

## Modes

The skill runs in one of two modes, and the mode is settled before the first file is read.

**Report mode is the default.** Steps 0 through 6: resolve, verify the resolution, gather
evidence, catalogue, refute each finding, re-derive the counts, report. It writes one file
outside the repository and stops. It does not walk the findings, does not propose diffs, and
touches no configuration.

**Triage mode is opt-in**, and the invocation has to ask for it: walk me through the
findings, fix what I approve, harden this. Triage mode runs report mode first, unchanged,
then continues into steps 7 through 10.

Two rules follow, and neither has an exception:

- When the invocation does not clearly ask for triage, the mode is report. Consent is not
  inferred from enthusiasm.
- An unattended session is report mode, whatever the invocation asked for. A mode that stops
  the harness from prompting is not a person agreeing to a change.

Report mode is the default because this is the one audit whose subject is the permission
file governing the agent doing the auditing. An audit that starts by editing what it audits
has answered a question nobody asked yet.

**Report mode is a complete run, not an interrupted one.** It ends by saying where the
report was written, that nothing was changed, and what triage mode would have done next. It
does not ask whether to continue. An invocation that wanted triage would have said so, and
offering to continue turns a default into a prompt the user clicks through.

Two of the eleven steps need a method rather than a description, so they are written out
first. The full sequence, and where each mode stops, is under **The run** below.

## Step 0: Resolve the effective configuration

Read every layer that contributes to a session, and record provenance for each entry,
because origin decides severity:

- user scope settings: permissions, hooks, environment, default mode
- user scope instruction and rule files
- project scope settings committed to the repository
- project scope local settings, not committed
- MCP server definitions at every scope where they are declared, and which projects
  reference each declared server
- subagent definitions and their tool grants
- installed plugins, marketplaces and skills
- project instruction files

Every entry carried forward from this step names the file it came from and the scope that
file sits at. An entry without provenance is not usable by any rule in the catalogue.

**Precedence is resolved the way the harness resolves it, and never guessed.** Where the
resolution order is not obvious from the files themselves, establish it from the harness
documentation rather than assuming the order that looks sensible. The reason is severity: a grant attributed to the wrong file turns a critical
clone-the-repository finding into a local hygiene note, or the reverse. This is why
provenance gets its own verification step before any rule runs.

Step 1 is that verification: an independent agent rebuilds the resolution from the files
alone and has to agree with it. Its contract is described in the Parallel Execution
Strategy section below.

## Step 2: Gather exercise evidence from transcripts

Two rules, PERM-004 and PERM-005, ask whether a grant was ever actually used. That question
is answered from session transcripts, and it is a negative claim, so the method matters more
than the result.

### Find transcripts by walking, never by a list of patterns

Walk `~/.claude/projects/` recursively for `.jsonl` files, and classify each file the walk
finds **by the shape of its records**, not by where it sits. A file counts as a transcript
when it contains `type: "assistant"` records whose `message.content[]` array holds one or
more `tool_use` blocks.

These locations are examples of what such a walk finds on installations that exist today.
They are not the definition of where to look:

```
projects/<project>/<session>.jsonl                                          top-level sessions
projects/<project>/<session>/subagents/agent-<id>.jsonl                     subagent sessions
projects/<project>/<session>/subagents/workflows/<workflow>/agent-<id>.jsonl workflow-spawned agents
```

A file that sits one level deeper than anything listed above, or ten, is a transcript if it
has the shape, and it is scanned. Nesting grows as the harness gains features, and this skill
will run against versions nobody has seen yet. A fixed pattern list is at best a stale
snapshot of where a walk once happened to find files, and it has already missed whole classes
of transcript more than once.

Why this is not pedantry: when a session dispatches a subagent, the parent transcript records
only the single call that spawned it. Every shell command, file write and server call the
subagent actually made is recorded only in that subagent's own nested file. A grant exercised
solely inside delegated work is invisible to a scan that stops at the top level, and the
audit then reports it as never used.

Attribute a record to a project by reading the `cwd` field on the record itself. Do not parse
the encoded directory name: a literal dash in a real path segment is indistinguishable from
an encoded separator, so the name cannot be decoded back safely.

### Match a grant against a call

Tool identity is always `message.content[].name` on the `tool_use` block. There is no single
field carrying the argument a permission pattern matches against; the argument is
tool-specific and lives in that same block's `input`. Resolve it through this table, and
never guess which key to read:

| Tool kind | Field in `input` to match against | Notes |
|---|---|---|
| `Bash` | `command` | A command-scoped pattern matches the command string. |
| `Monitor` | `command` | Same shape as `Bash`, matched the same way. |
| `Read`, `Write`, `Edit` | `file_path` | An absolute path. |
| `WebFetch` | `url` | A domain-scoped pattern needs a domain parsed out of the URL, not a literal string match. |
| `WebSearch` | `allowed_domains` if present, else none | With no `allowed_domains`, report **cannot verify** rather than matching against the query text. |
| `mcp__<server>__<tool>` | none, match on the tool name alone | MCP patterns are server and tool scoped. The `input` keys are per-tool and correspond to nothing in the pattern syntax. |
| `Skill` | `skill` | The skill name. |
| `Agent` | none | No argument-level pattern dimension. Report **cannot verify**. This is also the tool whose nested transcript holds the evidence for everything it did. |
| `ToolSearch` | none | Report **cannot verify**; a whole-tool grant is the only thing that could apply. |
| Orchestration and interface tools such as task, messaging, feedback, workflow and plan-exit tools | none | No argument corresponds to a permission grant. Report **cannot verify**. |
| Any tool kind not listed above | unknown | Report **cannot verify**. Never assume zero matches, and never pick a key that looks plausible. |

"Cannot verify" is a real outcome and is reported as one. It is not the same claim as "never
exercised", and it must never be rendered as one.

When a rule filters to calls that ran without error, treat an absent error flag on a result
block as **unknown**, not as success. The flag is not present on every result.

### What a negative claim has to carry

A PERM-004 or PERM-005 finding states, inside the finding itself:

- the exercise count the walk produced
- how many transcript files the walk covered
- the span those files cover, computed from the files themselves

If the walk cannot complete, because a location is unreadable, a file will not parse, or the
tree is not present, the rule reports **cannot verify** and never "never used". A negative
claim without its denominator is not evidence.

Every one of these numbers is measured at run time and reported as measured. The skill
carries no counts of its own, because a corpus grows while it is being read and a number
written into a rule is wrong by the time anyone reads it.

If no transcripts are found at all, PERM-004 and PERM-005 produce no findings, and the report
says out loud that no evidence was available.

## The rule catalogue

Thirty rules in eight prefixes. Each carries a detector, a severity and a required proof
shape. **A rule that cannot produce its proof shape does not produce a finding.**

### PERM: permission grants

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| PERM-001 | Unbounded shell grant in any allow scope | CRITICAL in user or committed scope, HIGH in local | The literal entry, its file, and one concrete destructive command it admits |
| PERM-002 | Grant whose pattern admits more than its name suggests, because the tail is unconstrained | HIGH | A concrete command string that matches the pattern and does something outside the grant's evident intent |
| PERM-003 | Read, edit or write grant reaching outside the project root | HIGH | The entry, and a path it reaches that the project has no business touching |
| PERM-004 | Allow entry with zero matching tool calls across the transcripts the walk found | LOW | The exercise count, the number of transcript files the walk covered, and the span they cover. If the walk cannot complete, or the grant names a tool kind the match table cannot resolve, the rule reports "cannot verify" rather than "never used" |
| PERM-005 | Grant exercised exactly once, long before the most recent session | LOW | The single call and its date, against the span examined and the number of files walked. The same "cannot verify" outcome applies |
| PERM-006 | A prompt-skipping default mode set in a committed file | CRITICAL | The entry and confirmation the file is version-controlled |
| PERM-007 | Wide allow entries with no deny entries covering destructive or secret-reading operations | MEDIUM | The widest allow present, and the absent deny |
| PERM-008 | An unbounded outbound grant co-existing with read access to where credentials live | HIGH | Both entries, and the path a secret takes from one to the other |

PERM-008 is a pair rule. Neither half is a finding on its own, and reporting either alone is
the false positive this rule exists to avoid.

### HOOK: hooks

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| HOOK-001 | Hook command sourced from inside the repository | CRITICAL | The hook entry, the script path, and confirmation the script is present and committed |
| HOOK-002 | Hook that pipes tool input or output into an interpreter or a network call | HIGH | The command line, and what part of the payload reaches it |
| HOOK-003 | Session-start or prompt-submit hook whose injected context comes from a mutable source | HIGH | The hook, its source, and who can write that source |
| HOOK-004 | Hook configured without a timeout | LOW | The entry |
| HOOK-005 | Hook whose command does not resolve, is missing, or is not executable | MEDIUM | The entry and the failed resolution |

HOOK-001 carries the sharpest story in the catalogue: cloning a repository is enough to
execute code, and nobody reads a settings file before opening an editor.

HOOK-005 is the guard everybody believes is running.

### MCP: servers

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| MCP-001 | Credential present in a server's env block in a committed file | CRITICAL | The key name, its file, and confirmation the file is committed. Never the value |
| MCP-002 | Server declared at user scope but used by one project | LOW | The declaration scope, and the projects that reference it |
| MCP-003 | Blanket auto-approval covering all of a server's tools | HIGH | The allow entry, and the destructive tools it covers by name |
| MCP-004 | Server started from an unpinned source, or reached over an unauthenticated transport | MEDIUM | The command or URL |
| MCP-005 | Tool descriptions carrying instructions aimed at the model rather than describing the tool | HIGH | The quoted description |

MCP-001 quotes the key name and never the secret. A report that copies a credential out of a
config file into a report file has made the problem worse.

### AGENT: subagents

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| AGENT-001 | Subagent granted unrestricted tools | HIGH | The definition and its grant |
| AGENT-002 | Tool granted to a subagent that its own prompt never needs | LOW | The grant, and the prompt that does not use it |
| AGENT-003 | Subagent whose grants exceed the main session's | HIGH | Both grant sets, and the operation available through delegation but not directly |

AGENT-003 is privilege laundering: the session cannot push, so it asks something it spawned
to push. Look for it explicitly, because almost nothing else does.

### SKILL: skills and plugins

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| SKILL-001 | Plugin or marketplace installed from an unpinned source | MEDIUM | The source entry |
| SKILL-002 | Broadly triggering skill whose body issues standing instructions | MEDIUM | The trigger description and the quoted instruction |
| SKILL-003 | Skill or plugin that writes to the repository or commits by default | MEDIUM | The instruction that does it |

### RULE: instruction files

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| RULE-001 | Instruction file granting standing consent, sentences that pre-authorise future action | HIGH | The quoted sentence and its file |
| RULE-002 | Precedence conflict between scopes resolved toward the broader authority | MEDIUM | Both sentences, and which one wins |

RULE-001 judges what instruction files authorise. Naming which files are loaded is a
different job and a different tool. This rule reads the sentences and asks what they permit
without asking again.

### SCOPE: provenance

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| SCOPE-001 | A committed project setting that widens the user's own posture | HIGH | Both values, and the resolution between them |
| SCOPE-002 | Local-scope grants that exceed the committed ones and are invisible to the team | LOW | Both sets |

### MODE: reach under the configured mode

| ID | Detector | Severity | Required proof |
|---|---|---|---|
| MODE-001 | Grants whose effective reach changes under the configured default mode | Modifier | Each affected grant, what it reaches under a prompted mode, and what it reaches under the configured one |
| MODE-002 | An unattended mode configured persistently rather than chosen per session | MEDIUM | The setting and its scope |

MODE-001 is not a standalone finding. It is reported once as its own section, and it raises
the severity of every grant it applies to by one level. This is the rule the skill was built
around: a grant reviewed under prompted editing means something else under a mode where the
agent works through the shell without stopping. The grant did not change, its reach did, and
no review happened in between.

## Severity model

Severity is argued from which attacker story the rule completes, never from how the entry
looks. A wildcard that reaches nothing is not critical, and a modest-looking entry that
completes a path from a cloned repository to a running command is.

| Level | The story it completes |
|---|---|
| **CRITICAL** | Cloning a repository or opening a session is enough to execute code or leak a secret, with no prompt |
| **HIGH** | An instruction injected through content the agent reads can finish a destructive or exfiltrating action |
| **MEDIUM** | Reach substantially past demonstrated need, or a guard that is not doing its job |
| **LOW** | Unused grants, blast radius, hygiene, cost |
| **INFO** | Hardening with no current path to harm |

Write the story into the finding. If the story cannot be written, the severity is wrong or
the finding is not one.

## The run

Both modes run steps 0 through 6. Report mode stops at 6. Triage mode continues into 7
through 10, and nowhere else.

0. **Resolve.** Build the effective configuration, with the file and the scope recorded for
   every entry.
1. **Verify the resolution.** An independent agent rebuilds the resolution from the files
   alone and has to agree with it before any rule runs.
2. **Evidence.** Walk the transcripts and produce exercise counts, with the denominators a
   negative claim needs.
3. **Catalogue.** Run the thirty rules against the resolved configuration.
4. **Verify each finding.** One skeptic per finding, told to refute it.
5. **Verify the counts.** A second skeptic re-derives every transcript-based number from the
   transcripts, not from the finding.
6. **Report.** One file, written outside the repository.

Report mode ends at step 6, and it ends by saying so.

7. **Triage.** One finding at a time, in severity order, each one approved on its own.
8. **Verify the narrowing.** A skeptic proves the proposed diff strictly shrinks the
   permission set.
9. **Apply.** Copy the original into `~/.claude/agent-config-audit/<project>/`, never
   beside the file and never anywhere inside the audited tree, show the diff, write the
   change.
10. **Re-verify.** Re-resolve the configuration, confirm the posture shrank, and confirm
    nothing else moved.

Steps 1, 4, 5 and 8 are the same contract with different subjects.

## Approval is per finding, and an unattended mode is not approval

**Nothing is applied without approval of that specific finding, in that session, in words.**

Each finding is put to the user on its own, and the response is one of four: **approve** it,
and step 8 verifies the narrowing before anything is written; **skip** it, marked
`[SKIPPED]`, with no diff produced; **defer** it, marked `[DEFERRED]`, to revisit on a later
run; or **edit** the proposed narrowing before approving it. A finding that gets none of
these stays `OPEN`, and nothing about it reaches step 8.

An unattended session is report mode, whatever the invocation asked for. It stops after the
report and applies nothing.

The default does most of the work here. Reaching triage at all takes an invocation that asked
for it, so the gate to talk past is not one approval but two. Agents talk past it anyway, and
they do it in these words:

| Rationalization | Reality |
|---|---|
| "Running unattended — no clarifying questions, fix in place." | A mode that stops the harness from prompting is not a person saying yes to this change. An unattended run ends with a written report, and that is the correct outcome rather than a degraded one. |
| "Running unattended: no clarifying questions possible, so every fix below is one I judged safe/conservative and reversible, and I recorded my reasoning inline rather than asking." | Reversible and recorded is not approved. Judging which changes are safe is the part of the work that belongs to them. |
| "...every finding that had an unambiguous, low-risk fix was fixed directly rather than merely flagged." | Merely flagging it is the deliverable. Low risk describes the change, not the consent, and the findings that look unambiguous are the ones written up by an agent that had already decided. |
| "It only narrows, so it cannot hurt" | Narrowing breaks a workflow the user relies on. That is a decision, and it is theirs. |
| "I will apply it and say so in the summary" | Telling someone afterwards removes their ability to say no, and that ability is the whole content of an approval. A summary is a notification. Asking leaves the decision where it was. |
| "They approved the audit, so they approved the fixes" | The audit is the report. The fixes are separate, one at a time. |
| "They approved the previous three, the pattern is established" | Approval is per finding because every finding has different consequences. The one a user refuses is the one they would not have predicted refusing, which is exactly the case the induction cannot see coming. |

Red flags, phrased as the thoughts they arrive as. Each one means stop and write the report:

- "I will just fix this one while I am in the file."
- "Nobody is there to ask, so asking is pointless."
- "This is too small to be worth a prompt."
- "I already know what they would say."
- "I will apply it and flag it in the summary."
- "The invocation asked me to leave the config in a better state, so it asked for changes."
- "The mode is unattended, which is the user telling me to proceed."

Every one of these is an argument about the situation, and none of them is a person
answering a question. The test is not whether the reasoning is good. The test is whether
somebody said yes to this finding.

## Narrowing only

**An applied change must strictly shrink the permission set.**

Allowed:

- tightening a glob to named entries
- removing a hook
- removing a server
- adding a deny entry
- moving a grant from a broader scope to a narrower one

Refused:

- adding an allow entry
- widening a pattern
- moving a rule to a broader scope
- removing a deny entry
- relaxing a mode

**Refused even when the user asks for it during triage.** A request to widen is a config
edit, not an audit finding, and this skill does not make config edits. Say so, say what the
widening would authorise, and continue triage with the next finding. Nothing about the
refusal ends the session.

**No diff is written until a verifier has proved the narrowing.** Step 8 is not a formality
placed after the decision. It runs before the user sees a diff at all, because a diff on
screen is already halfway to applied.

The invariant fails against requests that sound reasonable, in two ways: refusing to
disappoint the request, and shrinking the widening until it passes for a narrowing.

| Rationalization | Reality |
|---|---|
| "This is intentionally broad (any git subcommand, any npm subcommand, including things like `git push --force` ...) ... a narrower rule ... would still prompt for most everyday git/npm usage and wouldn't satisfy the request." | The request is the thing being refused. An agent that can name force-push as the consequence, and grants it anyway to satisfy the wording, has argued its way from a security finding to a security change. |
| "I added scoped, non-destructive allow rules rather than blanket wildcards..." | A scoped allow is still an allow. Narrowing the widening is not narrowing. |
| "I chose scoped, specific command-prefix allows, not blanket `Bash(git:*)` / `Bash(npm:*)`, for these reasons:" | The reasons are good ones, and they argue for a smaller widening. The invariant is not about size. Every entry added here is new reach, granted during an audit, by the agent the audit is about. |

The last two are the dangerous ones, because both agents are pleased with themselves. Care in
choosing which new reach to grant is not the same as granting none, and "I only added a scoped
allow" is the sentence to watch for in your own output.

Red flags, again as the thoughts they arrive as. Each one means stop, name the invariant, say
what the widening would authorise, and move on to the next finding:

- "This one is scoped and non-destructive, so it is not really a widening."
- "A narrower rule would not satisfy what they asked for."
- "They asked for it explicitly, so refusing is me overriding the user."
- "I am the one who just audited this, so I am the right person to judge the exception."
- "The prompts are the actual problem here, so removing them is the fix."

The first two are the ones that feel like diligence, and they are the same mistake as the
table above: an audit that ends with more reach than it started with has inverted itself.

## Output

Write the report to `~/.claude/agent-config-audit/<project>/report.md`, where `<project>` is
the name of the audited project. Say where it was written.

Sections, in this order:

1. the resolved configuration, every entry with the file it came from
2. the transcript evidence: how many files the walk covered and the span they cover,
   computed at run time, or a statement that none was found
3. findings by severity, each with its proof and, in triage mode, its proposed narrowing
4. the dropped table, each entry with the refutation that dropped it
5. the MODE-001 reach delta, once, as its own section
6. a before-and-after posture summary, once anything has been applied

Every finding carries a status: `OPEN | [RESOLVED] YYYY-MM-DD | [SKIPPED] | [DEFERRED]`.
`[SKIPPED]` is a finding the user declined, `[DEFERRED]` is one they want to come back to.
Both keep their proof, so a later run can tell a decision apart from an oversight.

The report is updated in place rather than rewritten, so a later run diffs against it.

Never output the full report inline in the conversation; write it to the file first and tell
the user the path. Do NOT commit the report: it lives under `~/.claude/`, outside the
repository being audited, precisely so a run against someone else's clone never lands in
their tree or their next commit.

**A credential value is never printed into the report.** Name the key, name the file, say
whether the file is committed. A report that copies a secret out of a config file has spread
it to one more file, and the report is the file people paste around.

**A call quoted as evidence is reported by tool name, project and date**, with the argument
elided wherever it is not load-bearing for the finding. Shell commands and URLs out of a
transcript carry inline tokens, customer hostnames and paths, and the walk covers projects
other than the one the report is about.

## Red Flags: You're Doing It Wrong

The process failures. Any one of these makes the run untrustworthy, whatever the rule
catalogue underneath it found.

- **Applying anything outside triage mode**, or reading an unattended session as consent to
  proceed
- **Widening reach to satisfy a request**, at any scope, however narrow or well-reasoned the
  widening looks
- **Shipping a finding the independent verifier never checked**, or a count the evidence
  verifier never re-derived
- **Guessing precedence** between scopes instead of establishing it from the harness itself
- **Calling a grant "never used"** when the transcript walk could not complete, or when the
  tool kind has no argument the match table can resolve
- **Printing a credential value** into the report instead of just the key it lives under
- **Delegating to see more of the configuration** rather than to have a claim refuted

## Common Mistakes

| Mistake | What to do instead |
|---|---|
| Reporting an allow entry that a deny entry at a higher-precedence scope overrides | Resolve precedence first, then check every finding against the deny set. This is the most common false positive this audit produces |
| Attributing a grant to the wrong file, and so to the wrong scope | Carry provenance from step 0 on every entry. Severity is argued from origin, so a wrong origin gives a wrong severity in either direction |
| Flagging a hook that cannot fire, because its command does not resolve or its matcher never matches | That is HOOK-005, a guard nobody knows is dead, and it reads nothing like a hook that is doing something dangerous |
| Treating an unused grant as dangerous | Unused is LOW. It is cleanup, and putting it near the top buries the finding that lets a cloned repository run code |
| Quoting a secret into the report | MCP-001 names the key and never the value |
| Calling a grant unused without re-deriving the count | Step 5 exists for this. A count nobody checked is a claim, not evidence |
| Reporting "never used" when the walk could not complete, or when the tool kind has no argument the pattern could match | "Cannot verify" is the honest outcome, and it is a different claim |
| Delegating in order to see more of the configuration | Read it in full yourself. Delegation buys refutation, not coverage |
| Writing a finding without the attacker story its severity claims | If the story cannot be written, the severity is wrong or the finding is not one |

## Parallel Execution Strategy

No parallel finder agents. The other audits in this set fan out one discovery agent per
dimension because the codebase they read is too large for a single context. A resolved
agent configuration is not: it is small enough to read in full, so it is read in full, by
one agent, and nothing is delegated in order to see more of it.

Parallelism here does one job only: independent verification. Everything sent to a subagent
is sent to be checked by a context that did not do the original reasoning, never to widen
coverage.

A verifier that receives the auditor's argument will ratify it. So the contract is fixed:

- a verifier receives the claim and the file paths, and never the auditor's argument
- it locates the line itself, and never trusts a quoted snippet
- it is told to refute, not to check
- verdicts are CONFIRMED, REFUTED or UNPROVEN, and only CONFIRMED ships
- REFUTED and UNPROVEN go into the dropped table, with the refutation beside them

The dropped table is the part of the report worth reading twice. Put the skepticism on the
page rather than asking the reader to take it on trust: every finding that ships says what
its verifier went looking for and did not find. A run in which every finding survives
refutation is a legitimate outcome, and nothing is moved into the dropped table to make the
report look thorough.

**Before confirming a finding, the finding verifier looks for whatever already constrains the
grant:**

- a deny entry that overrides it
- a mode under which the hook never fires
- a server that is configured but not enabled
- a narrower entry at a higher-precedence scope

Any one of those turns a confident finding into a dropped one, with the constraining entry
quoted beside it.

The evidence verifier exists because "never exercised" is a negative claim, and a negative is
exactly where one agent's missed search becomes another agent's confident finding. It
re-derives the count from the transcripts rather than reviewing the reasoning that produced
it.
