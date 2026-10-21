---
name: bug-report-writer
description: Turns bug findings (QA notes, steps performed, screenshots, logs, payloads, failed automated tests, exploratory session notes) into a clear, reproducible, Jira-style bug report built strictly from the information provided — no invented steps, environments or impact. Use this whenever the user wants to report, log, register, document or open a ticket for a bug or defect, and also when they paste a failing test, stack trace or error log and want it written up — e.g. "write a bug report", "open a bug", "turn this into a ticket", "achei um bug", "reporta esse erro", "abre um ticket", "documenta essa falha", "escreve o bug". Returns the report in chat by default, can save it as a Markdown file, and can create the ticket through an issue-tracker MCP (Jira, Azure DevOps, GitHub, Linear…) after the user reviews it.
---

# Bug Report Writer

Turn bug findings into a report anyone (dev, PO, QA) can read once and act on. The skill **organizes and writes** — it doesn't investigate or fill in blanks. The report comes first; opening a ticket is an optional last step.

**What to read:** [references/report-template.md](references/report-template.md) always; [references/severity-guide.md](references/severity-guide.md) unless the team gave severity; [references/labels.md](references/labels.md) only when the report isn't in English. The rest only when needed: [examples.md](references/examples.md) if unsure about format, [input-checklist.md](references/input-checklist.md) if the user wants a fill-in template, [tracker-integration.md](references/tracker-integration.md) if a tracker tool is connected.

## Not a bug report?
If invoked for something else (flaky-test investigation, fixing code, test cases, a sprint report, a JQL query), say in one line what this skill does, then help with what was asked. If a real bug turns up, offer to write it up at the end.

## Language
Look for `.qa-skills.yaml` in the project root, then `~/.qa-skills.yaml`. `language` is for what you say to the user; `report_language` (default: `language`) is for the report. An explicit request overrides the file — one that targets only the report ("escreve o bug em inglês") changes only the report; any other ("responde em espanhol", "escreve tudo em inglês") changes both. Otherwise use the language of the user's message. Don't mention a missing file. Evidence (logs, payloads, on-screen text) is never translated.

## Source fidelity
Every invented detail costs a developer time: a step the tester never did sends them down the wrong path, a guessed version makes them reproduce on the wrong setup, an assumed impact skews priority. Honest gaps beat plausible fiction.

- **Sources:** what the user wrote; files they gave (logs, payloads, HAR, test code, CI output); what is visible in screenshots you can see (say "the screenshot shows…").
- **Yours, always labeled:** the title (built from sourced facts), severity/priority marked *(suggested)* when the team didn't set them, wording and structure.
- **Never add:** steps not described (not even "log in first"), preconditions, test data, environment/version/platform (browser, OS, device, DB, broker…), IDs, endpoints, status codes, messages, requirement numbers, what "correct" is, impact, frequency, root cause, scope on other platforms.

A field with no source gets `⚠️ NOT PROVIDED` and goes into **Missing information**.

## 1. Triage
Give the user something useful in this reply — don't interrogate them first.

- **A. Bug with a sourced expected behavior** — requirement, story, spec, previous behavior, a failing assertion, or the user saying what should happen ("deveria salvar", "pretty sure it should show up there" → "according to the tester"). Write the full report now, with gaps marked.
- **B. Unclear whether it's a bug** — the user is unsure and gives no expected behavior. Don't decide what's correct: ask up to 5 short questions and offer a `[SUSPECTED]` report for the PO.
- **C. Several problems** — one report each, triaged separately, plus a summary table.

## 2. Write the report
Follow the template in the report language. Mandatory sections (Where, Steps, Actual, Expected, Environment, Evidence) stay even if they only hold `⚠️ NOT PROVIDED`; drop empty optional ones.

- **Title** — `[Module] - What happens + Where + Condition`, < ~120 chars, behavior not cause. ✅ `[PIX] - App Android não solicita MFA em transferência de R$ 5.000,00` ❌ `Erro no PIX`
- **Where (interface)** — what a dev looks for first. The skill is interface-agnostic: describe the interface where the bug manifests, in that interface's own terms — UI (screen path `Menu > Extrato > Filtro`, URL), REST/SOAP/GraphQL API (method + endpoint, status, response received), database (instance/schema, table, query or procedure, ORA-/SQL error), queue/topic (name, message ID, consumer, DLQ), batch/job (name, run ID, log), integration, CLI, etc. Fill only what applies to the bug's interface; never add fields from another interface (no "Screen: NOT PROVIDED" for an API/DB/queue bug). Anything else the user mentioned (e.g. the screen that triggered an API call) goes in as context, not as a gap. Mark as missing only what that interface needs (e.g. response body for an API, message payload for a queue).
- **Steps** — one action each, exactly what the user did, data in `code`. Partial flow → partial steps. No extras the user didn't do — setup ("log in"), "observe/verify the result", "open the downloaded file": what was observed belongs in Actual result, not in a step. From a failed test: steps from the test code, actual result from the assertion/error.
- **Actual / Expected** — exact messages; expected cites its source as given ("conforme RN2", "segundo o testador").
- **Reproducibility** — as the source states it ("1 failed, retries: 2/2 failed"); don't recompute.
- **Technical data / Evidence** — payloads and logs once, in fenced blocks, trimmed but unaltered; Evidence lists attachments without re-pasting them.
- **Description** — 2–4 sentences of what the user reported; impact only if they said it. Their hypotheses go in Additional notes, labeled.
- **Severity** — team's values, or the guide's, *(suggested)* with a one-line justification from known facts. No "could be higher if…": if an unknown would change it, put it in Missing information.
- **Sensitive data** — mask passwords, tokens, `Authorization`, API keys, cookies, card numbers, CPF/SSN and real customers' data, inside logs too. Test data stays. Masking is the only allowed change to evidence.
- **Missing information** — ordered by what a dev needs to reproduce: where (path/URL or endpoint + response) → environment/version → steps/test data → evidence → reproducibility.

## 3. Check
Read it as a skeptical developer: every sentence must trace back to the input. Anything that doesn't is an invention — remove it or mark it `⚠️ NOT PROVIDED`. No secrets, one bug per report.

## 4. Deliver
Send the report, then **one short closing line**: ask for the first 1–2 items of Missing information — already in priority order, so if "where" is missing, that's what you ask for (don't re-list the rest) and offer to save it as `bug-reports/BUG-<YYYY-MM-DD>-<slug>.md` (one file per bug). If no tracker tool is connected, add that connecting its MCP lets you open the ticket. With a tracker connected, follow tracker-integration.md and only create the ticket after explicit confirmation — and not while mandatory fields are `⚠️ NOT PROVIDED`, unless the user insists.

Markdown by default; offer Jira wiki markup (`h3.`, `{code:json}`) for Jira's legacy editor.
