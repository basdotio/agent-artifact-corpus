# Content — manual.json, manifest.json, writing rules

Two files in the workspace drive the deck. `manual.json` holds everything app-specific that is not a task
slide; `manifest.json` holds one entry per task slide. `scripts/` carry no app knowledge.
Worked example: `assets/example/manual.json` + `manifest.json` (the plugin repo's `examples/demo/` is the same
manual with real screenshots and replayable steps).

Deck order: cover · TOC · `intro[]` · per chapter (divider + its manifest items) · `reference[]` · `closing`.

## manual.json — top level

| Key | Type | Default | Use |
|---|---|---|---|
| `title` | str | required | cover title, e.g. `Demo Inventory — user manual` |
| `subtitle` | str | `""` | cover subtitle; the edition name and version are appended (`… · Viewer edition · v2 · 2026-01-31`) |
| `cover_note` | str | `""` | cover speaker notes (e.g. "screenshots use sample data") |
| `out_name` | str | `User-Manual` | output stem → `<ws>/out/<out_name>-ALL.pptx`, `-<edition>.pptx` |
| `module` | str | — | informational only; nothing reads it |
| `repo` | path | — | the app's checkout; `cap.mjs` tries to resolve Playwright from it first |
| `manifest` / `shots` | path | `manifest.json` / `shots` | builder only — `repl.mjs` and `cap.mjs` always write `manifest.json` and `shots/`; leave at defaults |
| `capture` | obj | — | see below |
| `copy` | obj | — | `{"messages": "<path>" \| ["<path>", …]}` — the app's i18n JSON for `check_copy.py`, relative to the workspace or absolute |
| `template` | obj | required | see template.md |
| `chapters` | list | required | one per role edition |
| `intro` / `reference` | list | `[]` | table/bullet slides before / after the chapters |
| `closing` | obj | none | `{title, subtitle, notes}` final slide (e.g. `Questions?`) |
| `edition_all` | str | `All roles` | edition label of the combined deck |
| `edition_one` | str | `{name} edition` | edition label per role; `{name}` = chapter name |
| `toc_title` / `toc_intro` / `toc_reference` | str | `Contents` / `Overview and terms` / `Reference` | TOC wording |
| `more_topics` | str | `and {n} more topics` | divider overflow line |
| `version` | int | — | manual version shown on the cover ("v2"); bump it for every refresh. A full build of a new version moves the previous decks to `out/archive/v<old>/` |
| `captured_at` | date | — | date the shots were taken, shown on the cover next to the version |
| `captured_sha` | sha | — | the app commit the shots were taken from — the base for "what changed since" |
| `code_paths` | [glob] | — | the app code the manual covers, for `git log <captured_sha>..HEAD -- <code_paths>` |
| `copy_ignore` | [str] | — | quoted strings `check_copy.py` should not look up (data values, prose quotes) |

For a non-English manual, set the label keys (`edition_all`, `edition_one`, `toc_*`, `more_topics`,
`template.tip_label`) in that language. Thai example: `"edition_all": "ฉบับผู้ใช้งาน"`, `"edition_one": "ฉบับ {name}"`,
`"toc_title": "สารบัญ"`, `"toc_intro": "ภาพรวมและคำศัพท์"`, `"toc_reference": "ข้อมูลอ้างอิง"`,
`"more_topics": "และอีก {n} หัวข้อ"`, `"tip_label": "เคล็ดลับ: "`, plus `"script_font": "Tahoma"` in `template`.

### capture

```json
"capture": {
  "base_url": "http://localhost:3000",
  "locale": "en", "timezone": "UTC", "viewport": [1600, 900],
  "login": { "url": "/login", "email": "#email", "password": "#password", "submit": "button[type=submit]",
             "whoami": "/api/me", "whoami_email": "user.email" },
  "users": { "viewer": "viewer@example.com", "editor": "editor@example.com" },
  "loading_selector": ".skeleton", "toast_selector": "[role=status]",
  "allow_hosts": []
}
```

| Key | Default | Meaning |
|---|---|---|
| `base_url` | `http://localhost:3000` | app root; `MANUAL_BASE_URL` overrides it (handy for a random test port) |
| `locale` | `en` | browser locale (`th-TH`, `en-GB`, …) — the app's language detection sees it |
| `timezone` | the machine's | browser timezone, e.g. `Asia/Bangkok`; pin it so dates in shots do not depend on who captured |
| `viewport` | `[1600, 900]` | CSS px; keep 16:9 |
| `login` | see above | login page URL (relative to `base_url`) + selectors. `whoami`/`whoami_email` optional (capture.md §2) |
| `users` | — | role key → test account email; `session(<key>)` logs in as it. Password from `MANUAL_PW_<KEY>` / `MANUAL_PW` |
| `loading_selector` | none | `shot()` waits until no element matches (skeletons, spinners) |
| `toast_selector` | none | `shot()` removes matching elements unless `keepToasts` |
| `allow_hosts` | `[]` | non-loopback hosts that may receive the login (test environments only) |

### chapters

`{"code": "viewer", "no": "Chapter 1", "name": "Viewer", "edition": "Viewer"}`

- `code` matches `manifest[].chapter` and `--role <code>`; `edition` is the file suffix.
- The TOC shows the last word of `no` as the chapter number.
- The divider lists the chapter's first 6 distinct task names (any ` (…)` suffix folded), then `more_topics`.

### intro[] and reference[] entries

```json
{ "type": "table", "kicker": "3 · Reference", "title": "Messages you may see, and what to do",
  "header": ["Message on screen", "When", "Fix"], "rows": [["…", "…", "…"]],
  "widths": [4.6, 3.6, 3.9], "size": 14, "notes": "…", "skip_roles": ["viewer"] }
```

| Key | Meaning |
|---|---|
| `type` | `table` (default) or `bullets` |
| `kicker`, `title` | small accent line + slide title; a trailing `:` on the kicker is stripped |
| `header`, `rows`, `widths` | table only; `widths` in inches, summing to ≤ the area width |
| `lines` | bullets only |
| `size` | table font pt, default 11 (14–16 reads well) |
| `notes` | speaker notes |
| `roles` | show only in these editions (and in ALL) |
| `skip_roles` | hide in these role editions; never hidden in ALL |

Rule: an entry shows when the edition is ALL, or it has no `roles`, or the role is in `roles` — and the role
is not in `skip_roles`. Cells and lines accept `**bold**`. The builder refuses a table or bullet list that would
overflow the content area — split it into `… (1/2)`, `… (2/2)`.

## manifest.json — one entry per task slide

```json
{ "chapter": "editor", "task": "Fill in and save the item", "kicker": "EDITOR · New item",
  "shot": "editor-02-form",
  "steps": ["Type the \"Name\" (**required**)", "Pick a \"Category\"", "Enter the \"Quantity\" on hand", "Click \"Save\""],
  "tip": "\"Notes\" is optional." }
```

- `shot` names `shots/<shot>.png` + `.json`. Prefix with the chapter code and a sortable number (`editor-02-…`).
- `task` = slide title (an imperative: what the user wants done). `kicker` = `ROLE · area`.
- `tip` is optional; it also becomes the slide's speaker notes.
- Entries are built in file order within each chapter — order the manifest like the user's workflow. With
  replayable `steps/`, a full `replay.mjs` writes this file for you, in step-file order: order the step files like
  the workflow.

## Writing rules

- **One language** for steps, tips and tables — the manual's language. Keep other-language words only where the
  UI shows them.
- **Quote on-screen text exactly** in “ ” or `\"…\"` (inside JSON): copy it from the app's message catalogue
  (i18n JSON) or source, not from memory. If the shot shows different text than the catalogue, the shot wins —
  then check the app you captured is current.
- **`**bold**`** marks the one word the reader must not miss (a limit, a status, "never …").
- **Step N ↔ box N.** `manual.py` refuses a slide whose step count ≠ its shot's mark count. A step that
  names a control without a box is a QA blocker: give it a box, or move the sentence into the tip.
- **One action per step**, starting with the verb or the place (`Click “Next”`, `In “Region”, pick…`).
- **Tip ≤ 120 characters.** Longer drops to 11pt and risks overflowing its fixed slot (the build refuses a tip
  that cannot fit). The tip says what happens next, a limit, or a consequence — never "ignore the warning".
- **Terminology:** use the product's own glossary if it has one. When the UI uses a different word, quote the
  UI and keep the glossary word in your own prose.
- **No internal names** in user copy: no env vars, table names, interface ids, ticket numbers.
- **Facts, not memory.** Every rule in a step, tip or table must trace to the app's code.

## Deriving intro and reference tables from code

Write each table from a code read and keep a `file:line` per row in the workspace (e.g. `<ws>/facts.md`);
a fresh session re-verifies from there.

| Table | Where to read |
|---|---|
| Roles — who does what | the permission/role checks (guards, policies, route middleware) |
| Variants (who can start a record) | the create handler / DTO enums |
| Status table (label each role sees, who acts next, allowed actions) | the workflow/state-machine code + the status labels in the i18n catalogue |
| Fields (required, limits) | validation schemas (Zod, Yup, JSON Schema, model validators) |
| Error messages → cause → fix | the i18n error keys + where they are raised |
| Emails / notifications | notification templates and their triggers |

- State what does **not** happen too ("no email when a reviewer sends a record back").
- Reference tables a role never needs go to `skip_roles`.
- Before shipping, a separate fact-QA pass re-checks every table row against code (qa.md).
