# Classification rules - FILL THIS IN

This file + its example store are the ONLY inputs a classifier subagent loads. Everything in
`<angle brackets>` is a placeholder. The section headings and the protocol around them are the
part worth keeping; the rules inside them must be yours.

Changes to this file go through the feedback loop in `SKILL.md` and get a dated Changelog line at
the bottom. Replace contradicted rules and examples - never stack a correction under the rule it
contradicts.

## Role and scope

You are <a virtual version of the specialist - name the discipline>, evaluating <cycle> feature
requests for <specialty> relevance.

The backlog spans <list the areas/products it covers>. You care about <which subset>; work in
<the other areas> matters ONLY if it surfaces something in <your subset>. Do not over-analyze
tickets that are structurally out of scope.

Read each feature's Title, Description, and Acceptance Criteria before deciding (rich-text fields
may arrive as HTML - ignore the markup, read the content).

## CORE PRINCIPLE (apply first, above every rule below)

Write ONE question that separates relevant from irrelevant in your domain, e.g. for analytics:
*"Does this create a NEW user action / data worth analyzing / user-facing experience in a product
we measure - or is it something users passively see, or pure plumbing?"*

Mark RELEVANT (Yes) if it does ANY of:
- <positive condition 1>
- <positive condition 2>
- <positive condition 3>

Mark NOT RELEVANT (No) if it is:
- <negative condition 1>
- <negative condition 2>
- <negative condition 3>

CALIBRATION (a sanity check, never a quota): across past cycles roughly <N>% of requested
features were relevant. If your batch is coming out far above that, re-read the CORE PRINCIPLE -
you are probably rescuing borderline items. Never flip a genuine Yes to No to hit a ratio;
recall-first still wins. A cycle can legitimately land BELOW the band when a whole workstream is
out of scope - before concluding the rules over-trim, check whether one large out-of-scope family
explains the gap.

When genuinely unsure, make your best Yes/No call and mark `Confidence: Low` - do NOT flip to Yes
to be safe. The cost asymmetry is handled downstream: Low-confidence No rows surface in the human
miss-scan queue, so a Low-confidence No is safe; a silent drop is not.

## TITLE-TAG PRE-CHECK

Many verdicts are obvious from the title's tags/prefixes alone. Use tags as a strong prior, but
the CORE PRINCIPLE still governs - never drop a clearly relevant feature for a tag alone.

DE-PRIORITIZING TAGS (default No): `<[TagA]>`, `<[TagB]>`, `<[TagC]>` - <why: platform work,
another team's product, hardware with no software surface, ...>

IN-SCOPE TAGS (judge normally): `<[TagX]>`, `<[TagY]>` - <the products/surfaces you actually cover>

How to decide:
1. De-prioritizing tag AND no in-scope tag -> default No; rescue only on concrete evidence in the
   description/AC. Borderline -> No, Confidence: Low.
2. Both kinds of tag present -> do NOT auto-reject; judge on the in-scope surface.
3. <your third tag rule>

## OWNERSHIP: who builds it, and where does it land?

Some feature families are built by ANOTHER team in a SEPARATE product you have no reach into.
Those tickets can describe rich, interactive functionality that reads as textbook Yes - and every
one is still No, because nothing lands in a product you cover. The disqualifying fact usually
appears NOWHERE in the ticket, which is why `SKILL.md` step 3 asks the user about every large
unexplained tag family BEFORE the fleet runs.

Record confirmed ownership facts here as hard rules, e.g.:
- `<[TagZ]>` features are built by <external team> in <separate product> -> **always No**, even
  when the ticket describes dashboards/telemetry/admin surfaces, and even when your own team is
  named as a collaborator. When the deliverable is measurement, ask the second question too:
  **measurement landing in WHOSE system?**

## TEAM / AREA SIGNAL

If your tracker's area or team field names the delivery team, use it: a platform/infrastructure
team's ticket usually lands before anything reaches a surface you cover.

| Team | What they do | Default |
|---|---|---|
| `<team 1>` | <platform team - work lands before any user-facing surface> | No |
| `<team 2>` | <product team for a surface you cover> | judge normally |

Extend as teams appear; confirm a team's role before adding it - never guess from the name.

## READ THE ACCEPTANCE CRITERIA STRUCTURALLY

The AC is the definition of done and OUTRANKS the narrative description. Named sections settle
calls on their own:

1. **"Out of scope" list.** If it explicitly excludes <your domain's deliverable - e.g.
   telemetry/instrumentation>, the answer is No, whatever the rest suggests.
2. **"Impacted teams" list.** If it names only teams outside your surfaces, the answer is No.
3. **AC that contradicts the framing prose** ("backend only" note vs AC requiring user-facing
   capability): trust the AC. Caveat: this settles WHAT the ticket delivers, never WHOSE product
   it lands in - apply the ownership and scope rules first.
4. **Empty AC + empty description** -> see the placeholder rule below.

## KILL RULES (high-precision No patterns)

Generic archetypes that produce most false positives in any domain - keep the ones that apply,
add your own, and give each a real exemplar from your backlog:

- **Passive-display rule.** A read-only view of data that already exists (an inventory column, a
  status indicator) creates nothing new for you. *<exemplar>*
- **Enablement rule.** Backend/platform work that prepares a capability but exposes nothing on a
  surface you cover yet - the later exposure ticket is the relevant one. "Adds a setting/control"
  wording does not rescue it when no surface ships. *<exemplar>*
- **Already-covered-generically rule.** Work your existing instrumentation/process already absorbs
  with zero new effort (e.g. one more entry flowing through an existing generic pipeline). Do not
  write an action item for it. *<exemplar>*
- **Design-artifact-only rule.** The deliverable is the design document, not the build - nothing
  ships, nothing to act on; the implementation ticket that follows is where you come in. A
  rigorously specified design deliverable is still a design deliverable. *<exemplar>*
- **Routine-release rule.** A dated version bump of something already shipped, marketing/store
  work, or a bug fix that changes no flow. *<exemplar>*
- **Placeholder rule.** A capacity reservation whose title declares it ("<X> placeholder",
  "Support <Y> development", body says "unknown work") is No at Medium confidence - Medium on
  purpose, so it drops out of the miss-scan queue too. Exception: an empty ticket whose title
  names CONCRETE functionality stays Yes/Low for a second look once scope lands.

## POSITIVE TRIGGERS (mark Yes)

- <new user interaction / capability on a covered surface>
- <the feature's own deliverable IS your domain's work - overrides the out-of-scope lists, with
  the ownership limit above>
- <launch of a new product/platform/capability, as opposed to a routine release>
- <migration/decommission funnels you must measure or secure>
- <your domain-specific triggers>

## TIE-BREAKER RULES (for ambiguous cases)

1. <platform vs surface: ready-in-backend is No; exposed-on-surface is Yes>
2. <passive view vs action: displays existing data No; new action/configuration Yes>
3. <release vs capability: dated bump No; first launch or the capability itself Yes>
4. <your fourth tie-breaker>

## PROGRESSIVE CONTEXT LADDER (when the call is genuinely hard)

Do not guess from a pattern when one more cheap read would settle it. Climb one rung at a time
and STOP at the first decisive rung; most features never leave rung 1.

| Rung | What to read | Reach for it when |
|---|---|---|
| 1 | Title + tags + area/team | always (pass-1 triage) |
| 2 | Description + acceptance criteria in full | title is not decisive (pass-2 escalation) |
| 3 | The AC's named sections - "Out of scope", "Impacted teams" | it looks relevant but may have been scoped out |
| 4 | Parent epic's title/description | the ticket is one slice of a larger effort and its own text is thin |
| 5 | Sibling tickets (near-identical titles, same family, adjacent IDs) | an ambiguous word could mean either thing - what siblings say EXPLICITLY beats what the pattern suggests |
| 6 | The work item's comment thread | scope is contested or the description was overtaken by events |
| 7 | Ask the user | only after rungs 1-6 leave it genuinely 50/50 |

Evidence beats pattern-matching. When you climb, say so in the `reason` field (e.g. "sibling
<id> names <surface> explicitly, this one does not"). Climbing is for CONTESTED rows only - a
handful per run; rungs 4-6 are the orchestrator's job, not a batch subagent's default.

## OUTPUT FORMAT (one JSON object per feature, one per line)

```json
{"id": 12345, "title": "<exact tracker title>", "verdict": "Yes", "confidence": "High", "surface": "<which product/surface>", "reason": "one line naming the rule or pattern that drove the decision", "action": "<2-4 concrete follow-ups for a Yes; exactly NA for a No>"}
```

- `verdict`: `"Yes"` | `"No"` - nothing else.
- `confidence`: `"High"` | `"Medium"` | `"Low"`. Use the full range - Low is a feature, not a
  failure: it routes the item to the human miss-scan.
- If you could not fetch or read an item, still emit its line with
  `"verdict": "No", "confidence": "Low", "reason": "fetch/analysis error - review manually"`.
- Every assigned ID appears exactly once. No prose before, between, or after the JSON lines.

## Locked canaries (immutable without an explicit user unlock)

Run these through a classifier after ANY rule or example change; every expected verdict must
hold. A canary miss means the change regressed a known failure mode - fix the change, never the
canary. Write ~12 rows, each guarding a DIFFERENT failure mode you have actually seen:

| # | Title | Digest (2-3 sentences, enough to judge without fetching) | Expected | Guards against |
|---|---|---|---|---|
| 1 | <a guaranteed-Yes feature> | <digest> | Yes | Pipeline sanity - if this flips, the classifier is broken |
| 2 | <a keyword trap - sounds relevant, is enablement> | <digest> | No | <the keyword> rescuing out-of-scope work |
| 3 | <a recall guard - looks out-of-scope by tag, is relevant by surface> | <digest> | Yes | tag rules over-killing real features |
| ... | | | | |

## Curated example store

Grouped by pattern, hard cap ~120 rows, curated replace-not-append (see the feedback loop in
`SKILL.md`). Format per group:

### <Pattern group name> (<Yes/No/mixed>)

| Feature | Surface | Verdict | Pattern |
|---|---|---|---|
| <real title from your backlog> | <surface> | Yes/No | <one line naming the transferable pattern> |

Keep contrast pairs deliberately (the backend twin of a Yes surface ticket; the design-only twin
of a shipped-UI ticket) - they teach the boundary better than either row alone.

## Changelog

- <date>: Initial version - rules seeded from <your source: past cycles, your team's review
  notes, your own labels>.
