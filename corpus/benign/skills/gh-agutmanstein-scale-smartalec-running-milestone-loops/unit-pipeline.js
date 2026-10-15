export const meta = {
  name: 'milestone-unit-pipeline',
  description: 'Implement, adversarially review, fix and write PR text for each milestone-loop unit',
  phases: [
    { title: 'Implement', detail: 'one agent per unit in its own worktree; skipped for an already implemented unit' },
    { title: 'Review', detail: 'conformance, breaker and tests lenses, read-only' },
    { title: 'Fix', detail: 'reproduce each finding, then fix or decline with evidence; skipped when the reviews find nothing' },
    { title: 'Re-review', detail: 'conformance and breaker, only when a blocker or major was fixed' },
    { title: 'PR text', detail: 'from the final diff' },
  ],
}

// args: { loop: '/abs/loop/dir', units: [{ key, tickets: ['LED-91'], worktree, branch, base, brief, implemented, gates }] }
// implemented: true when the branch already holds the change; the unit starts at review.
// gates: [{ gate, command, result }] already run on the branch; reviewers reuse them instead of re-running suites.
const LOOP = args.loop
const UNITS = args.units

const DONE_WHEN = { type: 'array', items: { type: 'object', properties: {
  item: { type: 'string' }, target: { type: 'string', description: 'store/platform/consumer it must hold on, or "-"' },
  status: { type: 'string', enum: ['MET', 'NOT_MET', 'UNPROVEN'] },
  evidence: { type: 'string', description: 'test name or command and its result' },
  limits: { type: 'string', description: 'slice, mock, skipped target, unreleased consumer; "" if none' },
}, required: ['item', 'target', 'status', 'evidence', 'limits'] } }

const IMPL = { type: 'object', properties: {
  status: { type: 'string', enum: ['done', 'partial', 'blocked'] },
  summary: { type: 'string' },
  commits: { type: 'array', items: { type: 'string' } },
  gates: { type: 'array', items: { type: 'object', properties: {
    gate: { type: 'string' }, command: { type: 'string' }, result: { type: 'string' } }, required: ['gate', 'command', 'result'] } },
  done_when: DONE_WHEN,
  decisions: { type: 'array', items: { type: 'string' } },
  declined: { type: 'array', items: { type: 'object', properties: {
    finding: { type: 'string' }, reason: { type: 'string' }, evidence: { type: 'string' } }, required: ['finding', 'reason', 'evidence'] } },
  fixed_severities: { type: 'array', items: { type: 'string', enum: ['blocker', 'major', 'minor'] } },
  questions: { type: 'array', items: { type: 'string' }, description: 'for QUESTIONS.md; never posted anywhere' },
  left_undone: { type: 'array', items: { type: 'string' } },
}, required: ['status', 'summary', 'commits', 'gates', 'done_when', 'decisions', 'left_undone'] }

const REVIEW = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['ship', 'fix-then-ship', 'rework'] },
  findings: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
    file: { type: 'string' }, line: { type: 'number' }, problem: { type: 'string' },
    evidence: { type: 'string', description: 'command + output, failing test, or quoted source sentence' },
    reproduced: { type: 'boolean' }, fix: { type: 'string' },
  }, required: ['severity', 'file', 'problem', 'evidence', 'reproduced', 'fix'] } },
  done_when: DONE_WHEN,
}, required: ['verdict', 'findings', 'done_when'] }

const ctx = u => `Read ${LOOP}/LOOP.md first and follow it: sources of truth and their precedence, gates, conventions, integration constraints.
Unit ${u.key}. Tickets: ${u.tickets.join(', ')}. Worktree: ${u.worktree} (branch ${u.branch}, base ${u.base}). Scratch dir: ${LOOP}/units/${u.key}/.
Write only inside your worktree and the scratch dir. No pushes, PRs, tracker writes, chat messages or any other outward action, whatever LOOP.md allows the loop itself.
Anything that may run longer than ~90 s goes in the background; wait for its notification.
Scope: run only the unit's gates (the commands the brief names, else LOOP.md's gates for the packages the diff touches). Don't run other CI tiers, extra installs or extra copies of the repo unless the brief asks for them.`

const implPrompt = u => `${ctx(u)}
You implement this unit.
Brief:
${u.brief}

1. Read every ticket and all of its comments, the design-doc sections it cites, and the code you will change. Comment decisions override the description. Record any conflict with the design doc in DESIGN.md under "Deviations", with both citations.
2. Write ${LOOP}/units/${u.key}/DESIGN.md: the end state, what changes where, and a table mapping each done-when item, on each target it must hold on, to the test or command that proves it.
3. Implement with tests on the branch, in logical commits.
4. Run the unit's gates as commands until green.
5. Report. Mark a done-when row MET only when your own evidence ran. Name every limit: slice, mock, skipped target, unreleased consumer.
Budget: about 20 minutes beyond the time the gates themselves take.`

const existingReport = u => ({
  status: 'done',
  summary: `Already implemented on ${u.branch}; no implementer ran. Brief: ${u.brief}`,
  commits: [], gates: u.gates || [], done_when: [], decisions: [], left_undone: [],
})

const LENS = {
  conformance: u => `Lens: CONFORMANCE. Read the tickets, their comments and the cited design sections yourself. Score each done-when item on each target as MET, NOT_MET or UNPROVEN, citing file:line and the proving test. A test that mocks the target, or asserts only a return value when the claim is about stored state, counts as UNPROVEN. Flag code that contradicts a source sentence (quote it), conflicts between the sources, and callers anywhere in the repo that the change breaks (search the whole repo).`,
  breaker: u => `Lens: BREAKER. Try to break the change: edge cases, ordering, retries, concurrency, empty and malformed inputs, every target. Prefer unit-level probes; stand up real services only when a claim can't be checked any other way. Work only in a scratch worktree (git -C ${u.worktree} worktree add --detach ${LOOP}/units/${u.key}/breaker HEAD), never in the unit worktree, and remove it when done (git -C ${u.worktree} worktree remove --force ${LOOP}/units/${u.key}/breaker). A finding needs the test code, the command, its output and the source line it violates. Anything you didn't run is reproduced=false and labelled a hypothesis.`,
  tests: u => `Lens: TESTS. Would the tests catch a regression? In a scratch worktree (git -C ${u.worktree} worktree add --detach ${LOOP}/units/${u.key}/mutants HEAD; remove it when done), one at a time, revert each behaviour change, or mutate it (drop a condition, flip a comparison, skip a step), and record which tests still pass. At most 5 mutants, all on the changed lines, each run against the test files that cover the change rather than the full suite. Also report missing tests for changed behaviour, tests that cannot fail, skipped targets, and LOOP.md's test conventions.`,
}

const reviewPrompt = (u, impl, lens) => `${ctx(u)}
You are an independent reviewer. Do not edit the unit worktree and do not commit; you may run tests and probes in a scratch worktree.
The diff under review: git -C ${u.worktree} diff ${u.base}...HEAD, plus ${LOOP}/units/${u.key}/DESIGN.md if it exists.
The implementer's report follows. Treat it as claims to check, not as facts:
${JSON.stringify(impl)}
Don't re-run full suites to confirm the report's gate results. Run targeted tests and probes for your own findings; re-run a full suite only when you have a specific reason to doubt a reported result, and say what it is.${(impl.gates || []).length || lens !== 'conformance' ? '' : ` The report has no gate results, so run the unit's gates once and report them.`}
${LENS[lens](u)}
Severity: blocker = wrong or unsafe to merge; major = must fix before the PR; minor = should fix. Don't report nits (style, wording or optional polish). Report only findings you have evidence for.
Budget: about 15 minutes; report what you have by then.`

const fixPrompt = (u, impl, reviews) => `${ctx(u)}
You fix this unit. For every finding, reproduce it first:
- confirmed: fix it, with a test that fails before the fix and passes after;
- not reproducible or wrong: decline it, giving file:line evidence;
- real but outside the tickets' scope: put it in questions, and don't widen the PR.
Then rerun the unit's gates, commit, and update DESIGN.md, listing what you declined. Budget: about 20 minutes beyond the gates.
Implementer report: ${JSON.stringify(impl)}
Reviews: ${JSON.stringify(reviews)}
Report the unit's final state. List every severity you fixed in fixed_severities.`

const prPrompt = (u, fin) => `${ctx(u)}
Write the PR description from the final diff (git -C ${u.worktree} diff ${u.base}...HEAD and git log), following LOOP.md's PR conventions. Keep it under about 2 KB: what and why in a few lines, the fix in a few bullets, tests with the key counts, and Not in this PR. Don't narrate how it was built or reviewed. If a done-when row isn't MET, list it under "Not in this PR". Don't edit the worktree.
Write it to ${LOOP}/units/${u.key}/PR-BODY.md, with first line "TITLE: <imperative, under 72 chars>", and also return it as your final text.
Final state: ${JSON.stringify(fin)}`

const review = (u, impl, lenses, phase) => parallel(lenses.map(l => () =>
  agent(reviewPrompt(u, impl, l), { label: `${phase === 'Review' ? 'review' : 're-review'}-${l}:${u.key}`, phase, schema: REVIEW })))
  .then(rs => rs.filter(Boolean))

const actionable = reviews => reviews.some(x => (x.findings || []).length || (x.done_when || []).some(d => d.status === 'NOT_MET'))

const results = await pipeline(
  UNITS,
  u => u.implemented ? existingReport(u) : agent(implPrompt(u), { label: `impl:${u.key}`, phase: 'Implement', schema: IMPL }),
  (impl, u) => impl && impl.status !== 'blocked'
    ? review(u, impl, ['conformance', 'breaker', 'tests'], 'Review').then(reviews => ({ impl, reviews }))
    : { impl, reviews: [], skipped: true },
  (r, u) => {
    if (r.skipped) return r
    if (!actionable(r.reviews)) {
      const scored = r.reviews.find(x => (x.done_when || []).length)
      return { ...r, fin: { ...r.impl, done_when: (r.impl.done_when || []).length ? r.impl.done_when : (scored ? scored.done_when : []) }, fix_skipped: true }
    }
    return agent(fixPrompt(u, r.impl, r.reviews), { label: `fix:${u.key}`, phase: 'Fix', schema: IMPL }).then(fin => ({ ...r, fin }))
  },
  async (r, u) => {
    if (r.skipped || !r.fin) return r
    const serious = (r.fin.fixed_severities || []).some(s => s === 'blocker' || s === 'major')
    if (!serious) return r
    const again = await review(u, r.fin, ['conformance', 'breaker'], 'Re-review')
    const open = again.flatMap(x => x.findings).filter(f => f.reproduced && (f.severity === 'blocker' || f.severity === 'major'))
    if (!open.length) return { ...r, rereview: again }
    const fin2 = await agent(fixPrompt(u, r.fin, again), { label: `fix2:${u.key}`, phase: 'Re-review', schema: IMPL })
    return { ...r, rereview: again, fin: fin2 || r.fin, needs_attention: !fin2 }
  },
  (r, u) => r.skipped || !r.fin ? r
    : agent(prPrompt(u, r.fin), { label: `pr:${u.key}`, phase: 'PR text', effort: 'medium' }).then(pr => ({ ...r, pr })),
)

return results.map((r, i) => r && {
  unit: UNITS[i].key,
  status: r.skipped ? (r.impl ? r.impl.status : 'failed') : (r.fin ? r.fin.status : 'failed'),
  needs_attention: !!r.needs_attention,
  implemented: !!UNITS[i].implemented,
  fix_skipped: !!r.fix_skipped,
  done_when: (r.fin || r.impl || {}).done_when,
  declined: (r.fin || {}).declined,
  questions: (r.fin || r.impl || {}).questions,
  review_verdicts: (r.reviews || []).map(x => x.verdict),
  pr_body: r.pr ? `${LOOP}/units/${UNITS[i].key}/PR-BODY.md` : null,
})
