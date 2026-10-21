---
name: gocam-review
description: Review, check, QC or validate an existing GO-CAM model the way a second curator would, read-only, and hand the author a severity-ranked report with concrete fixes. Use when a curator asks to review, check, QC, audit or validate a GO-CAM by id (gomodel:...), by Noctua URL, or as an exported Turtle file, for production or noctua-dev models. Fetches without any token, never edits a model, never uses --live. For building or editing a model use the noctua and gocam-best-practice skills instead.
license: BSD-3-Clause
argument-hint: "<gomodel id | Noctua URL | exported .ttl> [dev] [--with-uniprot]"
metadata:
  version: "0.2.0"
  source: https://github.com/geneontology/go-skills/tree/main/skills/gocam-review
---

# GO-CAM model review

This skill performs a review of a GO-CAM model: consistent checks, the same
severities and report format every time, and feedback the author can act on in
Noctua. Uses a token-free fetch and a tested checks script.

## Ground rules

1. **Read-only.** This skill never edits a model, on any server. Suggested fixes go in
   the report as text and as short Noctua comments the author can paste.
2. **No access to production Noctua, ever.** The GO AI Hub has no write access
   to production Noctua, by policy, and nothing in this skill or any other
   obtains one. Models are read from Noctua's public download route. Never
   ask for, accept or use a Noctua token here; never run anything with
   `--live`. If offered a token, decline and continue. Edits to a production
   model are made by its author, in Noctua, outside the GO AI Hub.
3. **Literature honesty.** Never assert what a paper shows from its abstract.
   Every finding that rests on a paper says whether the full text was read;
   if not, it is "not verified (abstract only)", not "wrong".
4. **Judgement over mechanics.** The script's flags are inputs. Most real
   problems (a reference reused on an edge it does not cover, a direct
   relation with no known mechanism, an ISS with no experimental source) are
   found by reading, against the guidelines in `gocam-best-practice`.
5. **The author decides.** Items they declined with a reason in an earlier
   round are not raised again (except references reused out of context).
6. **Bounded.** One pass over the check groups, the limits in each step, then
   stop. A review is not an open-ended investigation of the biology.

## Step 1: Identify the model and the round

Accept an id (`gomodel:...` or bare), a Noctua URL (editor, form, pathway
editor or download link; a noctua-dev URL selects that server), or a file the
curator exported from Noctua. Production is the default; a bare id of a
development model needs `dev`. Ask once if ambiguous.

```bash
ID=<bare id>                                  # no gomodel: prefix in paths
ls -d ~/reviews/*-$ID 2>/dev/null             # earlier rounds? read their checklist.md first
R=~/reviews/$(date +%Y-%m-%d)-$ID; mkdir -p "$R"
```

If an earlier round exists, read its `checklist.md` first: what was fixed,
what was declined and why. Issue ids stay stable across rounds.

`${CLAUDE_SKILL_DIR}` below is set by Claude while this skill runs; typed by
hand, it is the path of this skill's directory (`~/.claude/skills/gocam-review`
on the GO AI Hub).

## Step 2: Fetch (read-only, no credential)

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/fetch_model.sh" "<id | URL | file>" "$R"     # add: dev   for a dev model by id
```

Writes `$R/$ID.ttl` (and `$R/$ID.gpad` when Noctua has it) and prints the
paths and the environment; use those, and keep the environment for Step 3:
`ENV=production` or `ENV=dev`. HTTP 400 means the id is not on that server;
"could not reach" is a network problem, not a missing model.

## Step 3: Mechanical checks

```bash
uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/gocam_qc.py" "$R/$ID.ttl" --gpad "$R/$ID.gpad" \
    --env "$ENV" --markdown "$R/qc.md" --json "$R/qc.json"
```

The two noctua-models production QC checks (disconnected individuals,
multiply reified edges) run natively. To also run the production queries
verbatim, fetch them and add `--sparql-dir "$R/sparql"`:

```bash
mkdir -p "$R/sparql" && for q in check-disconnected-individuals check-multiply-reified-edges; do
  curl -fsS -o "$R/sparql/$q.rq" "https://raw.githubusercontent.com/geneontology/noctua-models/master/sparql/$q.rq"; done
```

`qc.md` is the dump a reviewer reads: model header (title, state, taxon,
contributors, group, comments to read), every activity with enabler, process,
location, inputs and outputs, every fact with its evidence lines (`CODE
reference with:...`), the references with the facts each supports, the
with/from values, the terms with labels, obsolescence and GO subsets, and the
flags by severity. Term lookups use the OLS API (cached); add `--offline`
only without network, and say so in the report. If the header shows "Derived
from", fetch the parent the same way (it is written as `$R/<parent id>.ttl`)
and diff:

```bash
PARENT=<parent bare id>; bash "${CLAUDE_SKILL_DIR}/scripts/fetch_model.sh" "$PARENT" "$R"
diff <(uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/gocam_qc.py" "$R/$PARENT.ttl" --offline --facts-only) \
     <(uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/gocam_qc.py" "$R/$ID.ttl" --offline --facts-only)
```

## Step 4: Gather context, within limits

- Read the `gocam-best-practice` references that match the activity types in
  the model (receptor, TF, transporter, enzyme regulator, adaptor, complex,
  carrier, E3 ligase, ChEBI) and `Relation_selection.md` and
  `Evidence_and_evidence_codes.md`. Do not judge a pattern from memory.
- Title and abstract for every PMID in the model (`pubmed-eutils`, in
  batches); check E needs all of them. Above 50 PMIDs, ask the curator which
  facts matter most and cover those first.
- For every ortholog in an ISS/ISO/ISA `with` value: does the source gene have
  an experimental annotation to the same or a more specific term (`amigo`
  skill, `bioentity-annotations`)? Limit 10 lookups.

## Step 5: The judgement pass

Work through `references/checks.md`, checks A to I, once. Each finding has an
id (`Q1`, `Q2`, ... stable across rounds), a severity (critical, major,
moderate, minor, note), its group letter, where (the fact, with the node
handles from `qc.md`, and the evidence line), what is wrong, the proposed fix
in Noctua, and when useful a one- or two-sentence Noctua comment (including PMID and
figure as appropriate) that makes sense to someone who never saw the report. Also record
what is fine; authors need to know what passed.

Full text is read for a finding you are about to rate critical or major that
depends on figure-level detail (species of the cells, the assay, the direction
of an effect): PMC open access, or a PDF the curator supplies. Budget: 5 papers
per review, 10 for a model with more than ten activities, more if the curator
asks; a finding whose paper was not read is downgraded to "not verified
(abstract only)", never stated as fact.

When a cited paper does not support a fact, offer the author a better
reference rather than only flagging the weak one: first look for one already
cited elsewhere in the model (the references index in `qc.md`; curators often
have the right paper on a neighbouring fact), then one `pubmed-eutils` search
for that fact. At most 3 such facts per review; the candidate PMID goes into
the drafted fix, marked as a candidate the author must read.

## Step 6: Optional modules, only when asked

- `--with-uniprot`: the model against the enablers' UniProt entries (function,
  Rhea reaction and ChEBI participants, location), both directions, written to
  a separate `uniprot-review.md`; `references/uniprot.md` has the procedure.
- Duplicate models on the same process and genes: not searchable without a
  token; suggest the curator check Noctua's search.

## Step 7: Deliver, report back, stop

Write, per `references/report.md`: `review.md` (findings by severity, what is
fine, evidence notes with full text versus abstract per PMID, verdict:
approve, approve with suggestions, or changes requested), `checklist.md`
(one row per finding with a status column, the durable tracker across rounds)
and `issues.json`. Then, in the conversation: where the model came from, counts
by severity and the critical and major items in one line each, what changed
since the last round or the parent, the literature caveat, the file paths, and
the pathway-editor link from `qc.md` (never the graph editor link).

Then stop. Do not re-derive the annotations, search the literature beyond the
limits above, or propose a different model. Follow-up happens only when the
curator returns the checklist (save it as `checklist-done.md`, answer their
notes, and for a disputed finding say what evidence would settle it) or a new
version (rerun, keep ids, add "what changed since"). If an earlier report was
wrong, say so at the top of the next one and withdraw the finding by id.

## If something fails

- `fetch_model.sh` "no model": wrong id or wrong server; try the other only if
  the curator agrees that is where it is.
- `gocam_qc.py` exits 2: not Turtle (OWL functional syntax and JSON are not
  read); ask for the Turtle export or fetch by id.
- OLS unreachable: `--offline`, and the report says terms were not checked
  and that activities typed with a specific function term and no enabler
  could not be classified.

## Provenance

From skills GO curators wrote on the GO AI Hub in October 2026. From
`gocam-qc` (pmasson55, lbreuza): the check groups A to I, the five
severities, the deliverables, the rounds with stable ids and a returned
checklist, the lineage and literature-honesty rules, the dump the script now
produces. From `gocam-review` (ccasalsc): the reading protocol (full text,
attribution, assay level to evidence code, species, coupled reactions), the
blocker/should-fix/suggestion items folded into the groups, the better-
reference step, the pathway-editor link, the UniProt cross-check module. The
token-free fetch, the checks script and its tests are the hub's.

Where the drafts differed: production is the default server (the owners'
decision for reviewing live models; the drafts defaulted to dev or read
production from the GitHub mirror); title length is a note, not a finding
(`gocam-review`'s author asked that it not be raised); a fact with no
evidence, a missing enabler and a single-activity model keep `gocam-review`'s
blocker severity. Not carried: `gocam-qc`'s HTML tick-box checklist (the
Markdown checklist is the tracker; the HTML can follow as its authors' own
change), duplicate-model search (needs a token), and the per-session log (a
personal house rule).
