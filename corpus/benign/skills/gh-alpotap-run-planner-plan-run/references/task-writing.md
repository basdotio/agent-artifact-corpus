# Writing a task

## Contents

- [The template](#the-template)
- [Heading and metadata lines](#heading-and-metadata-lines)
- [Sizes](#sizes)
- [Choosing the model](#choosing-the-model)
- [Haiku-ready tasks](#haiku-ready-tasks)
- [Cheap tasks](#cheap-tasks)
- [Other rules](#other-rules)

## The template

```markdown
### Task 19.2 — Folder quotas per tenant (ATTENDED)

**Size: M** · **Model: sonnet**

- **Files:** `app/services/quotas.py` (`def check_quota`, :88), `app/api/folders.py` (`@router.post("/folders")`, :41), `tests/integration/test_quotas.py` (new).
- <behaviour, one bullet per rule>
  - In: <concrete input>. Out: <concrete result>.
- **Tests:** <what the new tests assert>.

**Accept:** <observable outcome, literal>.
**Verify:** `pytest tests/integration/test_quotas.py -q`
```

The runner sends the whole task section to the session, with the plan's `## Rules for every task` section. Write the section so that it is all the session needs. It cites another plan section by number only when it truly must.

## Heading and metadata lines

- The heading is exactly `### Task <phase>.<n> — <title>`. The runner finds tasks with that pattern, in file order.
- Add ` (ATTENDED)` when the owner should look at the result: screens, visual style, measurements.
- Metadata goes in bold `**Key: value**` pairs, on one line or several, before the first bullet:
  - `**Size: S|M|L**`, required.
  - `**Model: haiku|sonnet|opus**`, required (see [Choosing the model](#choosing-the-model)).
  - `**Effort: low|medium|high**`, optional. It overrides the model's default effort from `runs/runner.json` (Sonnet: low; Haiku: medium; Opus: the model's own default). Use `**Effort: medium**` on a Sonnet task that is tricky but does not need Opus.
  - `**Tools: default**`, optional. This gives the session every built-in tool instead of the lean set (Bash, PowerShell, Read, Edit, Write, Grep, Glob). Only for a task that really needs another tool, for example a web fetch. Each extra tool definition is re-sent on every turn.

## Sizes

|                         | **S** (small, local)                                              | **M** (one feature area)                            | **L** (cross-cutting, schema, contract)                                 |
| ----------------------- | ----------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------- |
| Typical                 | one function, a label, a CSS rule, a config value, a string fix   | one route + its UI, one migration, a contract field | a new table with its flows, a new endpoint, the gate, the adversary     |
| Coordinates in the plan | exact: file, anchor, and the new text or rule                     | files + anchors of every place to change            | files + anchors + the reference sections it relies on                   |
| Turn budget (runner)    | about 8                                                           | about 20                                            | about 50                                                                |
| Checks                  | its Verify line                                                   | its Verify line, plus isolation/security suites if routes/tables changed | the same, plus the linter on changed files                              |
| Ledger note             | 1-2 lines                                                         | up to 6 lines                                       | up to 12 lines                                                          |

- **Size honestly.** A change to one function and its test is **S**, however important it is. Task 48.1 of an earlier run (append `/v1` to a local endpoint in one function, and update one test table) was marked M. It ran 23 turns, and its context went from 36K to 60K tokens. Most of those turns went on finding its section in the plan and on re-locating a function the plan had already found.
- **If a task needs more than 12 lines to report, it is two tasks.**
- **If a task would read more than about 100K tokens of context, it is two tasks.** Every turn re-sends the whole context. A session that grows to 200K pays 200K on every later turn, and a new session starts at about 11K.

## Choosing the model

| Model                          | Use it for                                                                                                                                                                                                                                                                                   | Default effort       |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **haiku** (Haiku 5.5)          | S tasks and small M tasks whose plan spells out every file, the function to change and the expected result: the exact file, an anchor, and the exact new text or a mechanical rule. Up to about three files and one Verify command. CSS changes, labels and strings, config values, renames, adding an entry to a list or registry, updating a test table, a `.gitignore`, a single-file route or UI change with its test. No design judgement left. | **medium**           |
| **sonnet** (Sonnet 5.5)        | The default. M and most L tasks: ordinary features, migrations, tests, documentation text, the gate, the walkthrough.                                                                                                                                                                    | **low**              |
| **opus** (Opus 5.5)            | Security-critical work (auth, permissions, row-level security, tokens, secrets, tenant isolation, payments, anything with an abuse surface); cross-cutting design where the plan leaves real judgement; **the adversary check**.                                                          | model default        |

- Sonnet runs at **low** effort by default. It uses about half the tokens of high effort for a small loss in quality. That trade is right for well-specified tasks, and the planner's job is to make every task well specified.
- When in doubt between Haiku and Sonnet, ask: "Could a careful junior developer do this from the task text alone, without opening anything but the named lines?" Yes means Haiku.
- Haiku is weaker on long chains of steps. Keep these on **Sonnet**, even when each step is simple: a migration that touches several files, rebuilding containers, browser walkthroughs, the test gate, and screenshot tooling. A task with more than about three files or more than one Verify command is Sonnet's.
- When in doubt between Sonnet and Opus, ask: "Would a subtle mistake here leak data, let someone in, or corrupt stored data?" Yes means Opus.

## Haiku-ready tasks

Haiku does well when the task reads like a recipe. Write it like this:

```markdown
### Task 21.3 — The queue's "Retry" button says "Run again"

**Size: S** · **Model: haiku**

- **Edit 1:** `webapp/app.js`, in `function renderQueueRow` (about line 1840): replace the string `'Retry'` with `'Run again'`. It occurs once in that function. Leave the other `'Retry'` strings in the file alone.
- **Edit 2:** `tests/ui/test_labels.py`, the `QUEUE_LABELS` dict (about line 22): change the value `"Retry"` to `"Run again"`.
- Nothing else changes.

**Accept:** the queue row's button reads "Run again".
**Verify:** `pytest tests/ui/test_labels.py -q`
```

Rules for a Haiku task:

- One numbered **Edit** per place: file, the enclosing function or selector as the anchor, an approximate line, and the old → new text, or the exact rule ("append `/v1` unless the value already ends in `/v1`, ignoring one trailing slash").
- Say what must **not** change when the same text occurs elsewhere.
- Name the test and the exact place in it to update. Never "update the tests".
- One Verify command.
- No "decide", "choose", "consider", or "if it looks wrong". If a judgement is needed, the task is Sonnet's.

## Cheap tasks

Token cost is turns × context. These rules attack both.

**What the runner already does.** It sends the task text in the prompt, so there are no turns spent finding it. It loads only the lean tool set: context starts at about 11K instead of 35K. It writes and commits the ledger row itself, so the session never reads the ledger. With these alone, task 48.1 would have taken about 12 turns at 11K to 30K context instead of 23 turns at 36K to 60K.

**What the plan must do:**

1. **Hand over the coordinates.** For every place to change: the file, the function, selector or literal as an anchor, and an approximate line. "Look at one place, change it and its test" must be what the task literally says.
2. **Give the new text** when it is known: the string, the CSS rule, the test table row. Copying is cheaper than deriving.
3. **Name the test file and the place in it.** For a new test, name the existing test it should sit next to, so the session copies that test's fixtures instead of reading the whole file.
4. **One Verify command**, targeted. Never the full suite.
5. **No exploration words.** Avoid "investigate", "look around", "make sure everything that uses X". Name the callers if they matter. Otherwise say "callers are unchanged".
6. **State facts, don't point to history.** "`tests/x.py::test_y` fails on the dev database because of a stored row. Do not count it, and do not delete the row." Never "see run 003's ledger".
7. **Split heavy tasks by area, not by step.** A docs pass over ten pages is two or three tasks of three to five pages each. Each task gets its page list and what to change on each page. A walkthrough of 17 rows is three tasks of about six rows each. Each new session starts small again.
8. **Make tooling failures cheap.** When a task depends on a tool (a screenshot pipeline, a docs build, a container), say: "If `<command>` fails twice for a reason outside this task, record the error in NOTE and finish with RESULT: blocked. Do not debug the tool." In an earlier run, the docs task spent about 70 of its 156 turns debugging the screenshot capture, and its context grew past 200K.
9. **Prefer text over images.** Browser checks read the page's text or accessibility tree. Use a screenshot only when the question is visual (colour, spacing, layout), and then take one per screen.

## Other rules

- **Scope is what was asked.** A favicon is a favicon, not "favicon, logo in four headers, docs theme and gateway check". Anything extra is a separate task, or nothing.
- **Files.** List them. The session may also touch tests and callers that break as a direct result, and names them in its note.
- **Examples.** Every rule with a non-obvious result gets an In/Out pair.
- **No open questions.** The run is unattended. A task that meets "ask the owner" takes the option it would recommend. If a fork is plausible, decide it in the plan: "If Pillow is missing, add it to `requirements-dev.txt` and say so in NOTE." Things only the owner can do (a credential, a purchase) are not tasks.
- **Waiting is one command.** Timed steps are written as a single foreground command that does the waiting, with its timeout. Example: `1..5 | % { docker stats --no-stream; Start-Sleep 60 }`, 10-minute timeout.
- **Builds.** Say exactly what to rebuild or reload for this change (from `runs/PROJECT.md`). Never "rebuild everything".
- **Numbered artefacts** (migrations, contract versions). Assign the numbers in the phases table, in run order, from the head you found. A task that runs out of order renumbers its own and keeps the chain intact.
- **Cross-repo.** A task that edits a sibling repository commits there as `Task <id>: ...`. The runner finds its commits in every repository listed in `runner.json`.
- **No documentation inside tasks.** Documentation is written once, in the closing phase, and only if D1 is yes. A task reports the pages and screens it affects on its `DOCS:` line.
