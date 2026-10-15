# In-session recipes (Mode A)

Each recipe: how to collect items, the request shape, and how to act on the answers.
Mask secrets and PII before building state. Ask before sending an employer's code.
`jev.py` is shorthand for `python3 "<skill-dir>/scripts/jev.py"`, where `<skill-dir>` is
this skill's base directory (see "Running the script" in `SKILL.md`).

## Contents
- The `jev.py batch` shape, worked example
- Custom request shapes (Python)
1. Log triage
2. Crash / stack-trace grouping
3. Lint and build-warning prioritisation
4. PR / diff risk gate
5. File relevance for a task
6. String resource review
7. Commit message check
8. Review-comment triage
9. App Store / Play review triage
10. Are the reviewer's findings fixed? (pre-resubmission check)
11. CI / test-failure triage
12. PR gate that fails closed
13. Content curation funnel
14. Near-duplicate detection
15. Candidate filtering before an expensive step
16. Jev funnel inside a Claude Code Workflow
17. Claude Code hooks (shadow mode, fail open)

## The `jev.py batch` shape, worked example

Most recipes below are one `jev.py batch` call: an **items file** (JSONL, one JSON
object per line, each with a stable `id`) and a **template file** (the questions,
written once, referring to the current item as `item`). Worked end to end, using log
triage:

`lines.jsonl`:
```jsonl
{"id": "L001", "text": "W/OkHttp: SocketTimeoutException connecting to api.example.com"}
{"id": "L002", "text": "I/Choreographer: Skipped 42 frames! The application may be doing too much work on its main thread."}
```

`log-template.json`:
```json
{
  "questions": {
    "category": {
      "type": "choice",
      "instructions": "What kind of problem does `item.text` indicate?",
      "criteria": {
        "crash": "An exception that kills a component or the app",
        "network": "Request failure, timeout, SSL or connectivity issue",
        "performance": "Jank, skipped frames, slow operations",
        "noise": "Framework or vendor chatter with no action needed",
        "none": "None of these fit"
      }
    },
    "own_code": {
      "type": "noul",
      "instructions": "Does `item.text` name this app's own package rather than the framework or a vendor library?"
    }
  }
}
```

Run it:
```bash
python3 "<skill-dir>/scripts/jev.py" batch --items lines.jsonl --template log-template.json \
  --out log-answers.jsonl --label log-triage
```

Each output line is one row:
```json
{"id": "L001", "answers": {"category": {"type": "choice", "choice": "network", "confidence": 0.91, "probabilities": {"network": 0.93, "crash": 0.03, "performance": 0.02, "noise": 0.01, "none": 0.01}}, "own_code": {"type": "noul", "noul": 0.08}}, "model": "typesafe/jev-1.13", "cached": false}
```

Read it: band each answer (`references/question-design.md` has the per-type cutoffs —
`ACT`/`REVIEW`/`ABSTAIN` on `category`'s `p_max`, `YES`/`NO`/`UNCERTAIN` on `own_code`),
then group and sort in code. `jev.py batch` already prints band counts per question to
stderr — read that before writing your own grouping pass. Rerunning the same command
resumes from `--out`, reusing a row only if it already answered every question id in the
current template and (for a real run) wasn't a mock answer. Rows match on question ids,
not wording, so after rewording a question start a new `--out`.

The recipes below give you the items shape and the template; wire them up the same way.

## Custom request shapes (Python)

For a one-off question, or state that doesn't split into one-item-per-line (shared
context plus several related items in one call), build the request directly and call
`--request`. Key items by id, never by position:

```python
import json
items = [...]  # list of dicts with a stable "id" and trimmed "text"
state = {"items": {it["id"]: it["text"] for it in items}}
questions = {f"{it['id']}__q": {"type": "noul", "instructions": f"... `items.{it['id']}` ..."}
             for it in items}
json.dump({"model": "typesafe/jev-1.13", "state": state, "questions": questions},
          open("/tmp/jev-req.json", "w"))
```
```bash
python3 "<skill-dir>/scripts/jev.py" --request /tmp/jev-req.json
```
Ids must be valid in a backticked path (letters, digits, underscore). For anything past
a handful of items, prefer `batch` — it packs requests under the token limit, retries,
resumes and caches for you.

---

## 1. Log triage

Collect: `adb logcat -d -v brief *:W` (Android), `log show --predicate '...' --last 1h`
or a Console.app export (iOS/macOS `os_log`), or a `grep`/`journalctl`/cloud-logging
export (backend) → dedupe identical lines → keep the newest ~200. Strip tokens, emails,
phone numbers, device IDs.

Template: `category` (choice, as in the worked example above) plus `own_code` (noul).
Act: show `crash`/`network`/`performance` lines that are `own_code`, grouped, noise hidden.

## 2. Crash / stack-trace grouping

Collect: Crashlytics (BigQuery or console export), Play Console (Android vitals
export), Xcode Organizer (exported, symbolicated crash logs), or test output. Trim each
trace to exception type, message, and top ~8 own-code frames.

Items: `{"id": "T04", "exception": "...", "message": "...", "frames": [...]}`. Template:
a choice per trace over candidate root causes (from you, or from code — e.g. the top
frame), including `"none": "None of the listed causes"`, plus a score for user impact:
```json
{"type": "score",
 "instructions": "How severe is the crash in `item` for end users?",
 "criteria": ["Background task, invisible to the user",
              "Feature degraded but the app keeps running",
              "Screen or flow unusable",
              "Crash on a core flow (e.g. booking, payment, login)"]}
```
Act: group by the choice, rank groups by summed severity × occurrence count (in code).

## 3. Lint and build-warning prioritisation

Collect: Android lint (`./gradlew lint`, XML/SARIF), SwiftLint (`swiftlint --reporter
json`), or ESLint (`eslint --format json`); one item per warning, with id, message,
file, and the 3–5 source lines around it.

Template, two nouls per warning:
- "Could the issue in `item` cause a crash, security problem, or data loss at runtime?"
- "Is `item` only about style, naming, or formatting?"
Act: fix list = first noul ≥0.8; bulk-suppress candidates = second noul ≥0.8 and first
≤0.2; everything else to the user as "review".

## 4. PR / diff risk gate

Collect: `git diff main...HEAD`, split by hunk; drop lockfiles, generated code, pure
renames. Never include `local.properties`, keystores, `google-services.json`.

Template: a score with levels "Trivial: comments, formatting, renames" / "Low: isolated
logic with obvious behaviour" / "Medium: changes shared logic, threading, or error
handling" / "High: touches auth, payments, signing, security checks, data migration, or
release config", plus nouls "Does `item` remove or weaken a null check, permission
check, or validation?" and "Does `item` change a network request or response model?"
Act: list High and medium-with-yes hunks first; suggest tests for those.

## 5. File relevance for a task

Collect: candidate files (`git ls-files` filtered by extension), then the first ~40
lines or the class signature and public members of each — not whole files.

Template: one noul, "Would a developer need to read or change `item` to implement:
<task>?" Act: open files ≥0.6 first, in descending order.

**Caveat:** jev-axi's own benchmark on a 390k-line repository found no change in cost or
files read from ranking before reading — the difference was inside run-to-run noise.
Reach for this recipe only on very large candidate sets (hundreds of files) or on
non-code documents (docs, tickets, transcripts), not as a default habit on every task.
([jev-axi](https://github.com/CHLIN0/jev-axi))

## 6. String resource review

Collect: `res/values*/strings.xml` (Android), `Localizable.strings`/`.xcstrings` (iOS),
or an i18n JSON bundle — entries as `{id, text}` per locale.

Template, three nouls per string (English source): "Is `item.text` unclear or ambiguous
to an end user?", "Does `item.text` contain a spelling or grammar error?", "Does
`item.text` sound rude or blaming toward the user?" For translations, put source and
translation in the same item and ask "Does `item.translation` change the meaning of
`item.source`?" English is Jev's strongest language; treat non-English answers with
extra caution.

## 7. Commit message check

Collect: `git log --format='%h%x09%s' -n 50`.

Template: a choice over conventional types (`feat`, `fix`, `refactor`, `chore`, `docs`,
`test`, `perf`, `none`), "Which type best describes `item`?", plus a noul "Does `item`
describe *what* changed specifically enough to be useful in a changelog?"
Act: suggest rewrites (you write them) for low-scoring ones.

## 8. Review-comment triage

Collect: PR review comments (`gh api`, or pasted).

Template: a choice `blocking` / `suggestion` / `question` / `nit` / `praise` / `none`,
plus a noul "Does `item` ask for a code change?"
Act: address `blocking` and change-requests first; batch nits.

## 9. App Store / Play review triage

Collect: an App Store Connect / Play Console review export, or an API pull; one item
per review with rating, text, and app version.

Template: a choice `reply_now` / `bug_report` / `feature_request` / `praise` /
`archive` / `none`, a score for urgency ("No reply needed, nothing is broken" / "worth a
look this week" / "needs a reply today"), and a noul "Is the reviewer waiting on a
response from us?"
Act: `reply_now` plus high urgency goes to the top of a reply queue; `bug_report` feeds
recipe 2 or 11; `feature_request` goes to a backlog.

## 10. Are the reviewer's findings fixed? (pre-resubmission check)

Before resubmitting after an App Store or Play rejection, check whether the diff
actually addresses what the reviewer flagged, instead of assuming it does.

Template: one noul per finding, with the reviewer's note and the diff both in the
item — "Does `item.diff` fix the problem described in `item.finding`?" One tool
measured this shape crediting 10 of 10 real fixes (mean 0.86) while unfixed controls
scored 0.06–0.26, so "fixed" and "not fixed" read clearly apart in the noul.
([jevskillz](https://github.com/calelamb/jevskillz))
Act: resubmit only once every finding clears your threshold; anything below goes back
to whoever made the fix, with the reviewer's original note attached.

## 11. CI / test-failure triage

Collect: failing test names, the last ~40 lines of each failure's log tail, and whether
it failed on recent runs (a flaky-test detector, or your own CI history).

Template: a choice `infrastructure` / `assertion_bug` / `flaky` / `none` — "What kind of
failure does `item.log_tail` show?" — plus, when the log tail has numbered candidate
lines, a second choice over those line ids plus `none` for the root-cause line (the
"Semantic find" pattern in `references/question-design.md`).
([jev-code](https://github.com/FrancoisChastel/jev-code), [jev-axi](https://github.com/CHLIN0/jev-axi))
Act: split on a margin, not a bare cutoff — `p_max` well clear of the runner-up and
above ~0.8 auto-files as `infrastructure`/`flaky` with no human paged; anything closer
or lower goes to a person. `assertion_bug` always goes to a human — it needs a real fix,
not a filter.

## 12. PR gate that fails closed

A merge gate that blocks by default and only opens on a confident answer.

Template: one choice `ready` / `needs_review` / `risky` / `unknown` (`unknown` covers a
diff Jev can't assess — no tests changed, an unfamiliar area, or content it isn't
confident on) over the same hunks as recipe 4.
([jevtriage](https://github.com/sathariels/jevtriage))
Act: merge auto-proceeds only at `ready` with `p_max ≥ 0.8`; every other outcome —
including low confidence on `ready` — blocks and needs a human approval. Fail closed:
an API error or a lint failure is also a block, never a silent pass.

Running it in GitHub Actions on pull requests from forks
([fatwang2/awesome-jev](https://github.com/fatwang2/awesome-jev), `.github/jev-review.json`
and its workflow): trigger on `pull_request_target` so the key is available, but check out
the **base** SHA with `persist-credentials: false` and read the PR's diff as data — never
execute the PR's code in a job that holds the key. Give each noul its own accept/reject
pair (there: 0.85/0.2 and 0.8/0.2) with a human for the middle, and fall back across
routes (TypeSafe → Vercel → Cloudflare) so one provider outage doesn't block every PR.

## 13. Content curation funnel

A mine → screen → review pipeline for any content pool (articles, snippets, support
macros, generated copy): mine candidates with ordinary code, screen them with
`jev.py batch` over keyed ids, let the confident ends (high accept, high reject) resolve
automatically, and send only the middle band to a Claude reviewer — a Haiku subagent for
volume, a person for anything sensitive.

Keep the loop closing: store each item's Jev answers next to the reviewer's verdict
(same file or row), rather than discarding one or the other. Once you have 50–100 paired
examples, write them as cases — `{"id": "a17", "text": "...", "expect": {"relevant": true}}`
(noul: true/false, choice: an option key, score: a level index or the exact level text) —
and run `jev.py eval --cases paired.jsonl --template screen-template.json --fields text`.
`--fields` matters: eval sends every field except `id` and `expect`, so a stored verdict
or old score would leak into the question.

## 14. Near-duplicate detection

Collect: a candidate pool (articles, tickets, commits, generated variants); build a cheap
shortlist of *pairs* worth comparing in code first (normalized-text similarity, shared
author or title, embeddings) — don't ask Jev to find duplicates across an unshortlisted
pool.

Template: one 3-level score per pair — "Different items: no shared wording or meaning" /
"related, but possibly not the same (a variant, a rephrasing, a partial overlap)" /
"Same item: identical meaning, only trivial wording differences" — the same shape the
entity-alignment cookbook uses for matching catalogue records.
([entity_alignment](https://docs.typesafe.ai/cookbooks/entity_alignment))
Act: merge or drop at the outer levels; send "related" pairs to a person.

## 15. Candidate filtering before an expensive step

Before an expensive step (embedding a large corpus, running every search result through
a reasoning model, opening every row of a dataset), cut the candidate set with
`jev.py rank`:
```bash
python3 "<skill-dir>/scripts/jev.py" rank --items candidates.jsonl \
  --question "Is this candidate relevant to: <task>?" --top 50 --min 0.6 \
  --out ranked.jsonl
```
It builds one noul per item (packed and cached like `batch`), sorts by the noul
descending, and writes the ranked rows. Same caveat as recipe 5: measure whether ranking
actually saves anything on your data before making it a standing habit — it pays off on
large pools, not by default.

## 16. Jev funnel inside a Claude Code Workflow

If your Claude Code has Workflows (see its `workflow-authoring` skill), keep the cheap
filtering in the main loop and spend agent budget only on what Jev can't resolve: run
`jev.py batch` over the full item set as one step, split the output rows by band in the script
itself (no LLM call for that), then pass only the `REVIEW`/`UNCERTAIN` rows — not the
whole set — as `args` to an `agent()` step that reviews them. Confident rows never reach
an agent at all. This is recipe 13's funnel, moved from an ad hoc loop into a workflow
step.

## 17. Claude Code hooks (shadow mode, fail open)

- Start in **shadow mode** (log the verdict, don't act on it yet) before gating anything,
  and **fail open on a transport error** (timeout, 5xx, no key) — tell that apart from an
  actual deny — in jev-axi, a provider 503 escalated instead of failing open.
- **Strip anything the agent fetched** (a page, an issue, a tool result) out of any state
  that authorizes an action — injected text moved a destructive-command gate from 0.76
  to 0.48 in one measured test.
- **Use a hook, not an MCP tool, for safety.** A hook runs on every call; an MCP tool
  runs only when the model decides to call it.
  ([jev-engineering](https://github.com/eugeniughelbur/jev-engineering), `recipes/README.md`)
- **Order: deny rules → read-only allowlist → Jev.** Deny first, because
  `cat ~/.ssh/id_ed25519` starts with an allowlisted `cat`. Catastrophic, well-known
  commands (`git stash clear` flipped to allow under every authority-claim injection in a
  300-call test) go in the deny regex, not the probability. (Same repo, README "How it
  decides" and `tests/test_order.py`.)
- **Gate state = the latest user message + the proposed command. Nothing else.** Leave
  out the agent's reasoning and earlier tool output, "or the agent can write its own
  permission slip" (same repo, `jev_gate.py` `build_state`). When the command runs a
  local script (`./deploy.sh`), put the script's text in state (capped) — otherwise the
  gate judges an opaque name ([jev-axi](https://github.com/CHLIN0/jev-axi), `src/safety.ts`).
- **Redacting secrets hides them from the gate too**, so detect credential reads or
  exfiltration with local pattern checks, not with Jev (jev-axi `findPossibleSecrets`).
- **"Allow" should print nothing.** Let the harness's normal permission prompt handle
  anything the gate doesn't deny or escalate; the gate never auto-approves. jev-axi's
  cutoffs, as a starting point: deny at p ≥ 0.8 on a blocking hazard, ask at ≥ 0.45 or a
  risk score ≥ 1.5 on a 0–2 scale.
- **Fail open or closed by blast radius**: fail open for a local coding agent, closed
  (escalate to a person) for money, email or production.
- **Budget the latency.** Retry once and only when `retry-after` ≤ 2 s; after 3
  consecutive 429/529s stop calling for 120 s; cache identical calls for 300 s — worst case
  ~2 × timeout + 2 s per tool call
  ([hermes-jev](https://github.com/DoGMaTiiC/hermes-jev), `plugins/jev-judge/README.md`).
- **Cap refusals** so a gate can't trap the session (jev-claude: 2 per plan, 1 per
  question set, 1 per command), and don't copy the official LangChain middleware's
  defaults without deciding them (it sends 30 messages including tool output and fails
  closed). More, including jev-claude's measured wording and threshold lessons:
  `agents.md`, "Guarding a coding agent's own decisions".
- Check which key a hook tool reads before wiring it up: most community hook tools read
  `TYPESAFE_API_KEY`, not `OPENROUTER_API_KEY`.
- Don't build a skill router this way — see SKILL.md's "where it doesn't help" (under
  Mode A).
