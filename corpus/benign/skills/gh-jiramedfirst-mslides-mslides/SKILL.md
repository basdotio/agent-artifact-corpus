---
name: mslides
description: Build, edit by chat, and refresh after UI changes — a step-by-step, per-role user manual for any web app as an editable PowerPoint deck + PDF, made from real Playwright screenshots with numbered callout boxes (step N = box N). Use whenever someone asks for a user manual, user guide, how-to slides, training deck, onboarding guide, SOP walkthrough or "slides showing users how to do X" for a web app, screen, feature or role (admin, editor, viewer, approver…), wants one edition per role, wants to update/refresh/re-QA an existing manual because the screens changed, or asks to change a slide's wording, tip, order or table — including in Thai — คู่มือการใช้งาน, คู่มือผู้ใช้, ทำคู่มือ, สไลด์สอนใช้งาน, สไลด์สอนการใช้ระบบ, อัปเดตคู่มือ, หน้าจอเปลี่ยนแล้ว, แก้คู่มือ, แก้ slide — even if they only say "make a manual for this app".
---

# MSlides — user manuals from real screenshots

Builds a deck like this: cover → overview tables → one chapter per role (divider + **one slide per task**:
numbered steps left, cropped screenshot right with matching numbered boxes, a tip) → reference tables → Q&A.
Every element is a native PowerPoint shape, so anyone can edit the deck afterwards. `assets/example/` holds a
complete `manual.json` + `manifest.json`; the plugin repository's `examples/demo/` is the same manual with real
screenshots, replayable capture steps and the tiny app it was captured from — read one before starting.

## Ground rules

- **Capture only against a local or test environment** you control — never production. Capturing writes sample
  data, and `cap.mjs` refuses non-loopback hosts unless `capture.allow_hosts` lists them on purpose.
- **Never handle passwords in the chat.** The user sets them as environment variables (`MANUAL_PW_<ROLE>` or
  `MANUAL_PW`) in their own shell; the scripts read them at runtime and never write or print them. Never type,
  echo, store or ask for a password in plain text.
- **The app's code is the source of truth for wording.** Button names, statuses, field rules and error texts come
  from its i18n message files and source (workflow code, validation schemas) — note `file:line` in the workspace.
  A manual that describes behaviour the code does not have is a defect.
- **Step N points at box N.** Step count must equal mark count (`manual.py` refuses otherwise). A step that
  names a control with no box goes in the tip instead.
- **Output may be confidential.** Screenshots show internal screens and data. Keep the workspace and decks out of
  public repositories and public links unless the user says the app is public.
- **Name everything you create `MANUAL-…`** and log every data tweak in `<ws>/PROGRESS.md` — the next session
  (or teammate) resumes from that file.

## Workflow

Set two variables once per shell: `S=<this skill's directory>` (the folder holding this SKILL.md) and
`WS=<workspace>`; `PY` is the workspace venv's interpreter — `$WS/venv/bin/python` on macOS/Linux,
`$WS\venv\Scripts\python.exe` on Windows (PowerShell: `$S`, `$WS`, `$PY` work the same way).

### 1. Ask (one round)
Ask what you cannot read from the code: which **app / area**, which **roles/chapters** (one edition per role?),
which **template .pptx** (default: the bundled `$S/templates/plain.pptx`), the **workspace folder** (default
`~/Documents/<App>-Manual/`), the **language** (default English), and **how to run the app** locally with test
accounts. Skip anything the user already said. Ask them to export `MANUAL_PW_<ROLE>` themselves.

### 2. Set up the workspace
```
<ws>/manual.json   config (schema: references/content.md) — start from $S/assets/example/manual.json
<ws>/manifest.json one entry per task slide (written during capture)
<ws>/shots/        NAME.png + NAME.json (marks) from cap.mjs
<ws>/steps/        capture step scripts (NN-name.js, one per screen/state)
<ws>/out/          built editions
<ws>/PROGRESS.md   resume notes: chapter status, MANUAL-… records and their state, data tweaks
```
`python3 $S/scripts/setup.py $WS` does the tooling in one go (idempotent): the venv with `requirements.txt`,
Playwright + chromium in the workspace unless node already resolves it (the app's own install via `"repo"` in
manual.json, or `NODE_PATH`), and it names the PDF renderer it found. By hand instead:
`python3 -m venv $WS/venv && $PY -m pip install -r $S/requirements.txt && cd $WS && npm i -D playwright && npx playwright install chromium`.

### 3. Template → `manual.json` "template"
Run `$PY $S/scripts/inspect_template.py <template.pptx> --suggest --render $WS/tpl`: `--suggest` prints a
`"template"` block to start from (layouts by placeholder type, measured `area`, dark colours for a dark theme);
look at the rendered pages and adjust cover/divider/content layouts, the content `area`, colours (dark template ⇒
light text), fonts (`script_font: "Tahoma"` for Thai) and `tip_label`. A dark unbranded template ships too:
`$S/templates/dark.pptx`. Details and worked configs: **references/template.md**.

### 4. Plan the manual from the code
Read the app's routes, i18n message files, workflow transitions and permission checks; write the role list, the
task list per role, and the **capture order** (states only exist in order — a "sent back" banner needs a record
that was submitted and then sent back). If product docs/specs exist, read them too: the manual documents
**current behaviour (code)**; where docs say otherwise, note the discrepancy in PROGRESS.md and tell the user.
Fill `manual.json` chapters, intro tables (who does what, statuses) and reference tables (fields, error → fix).
Rules: **references/content.md**. Show the user the task list before capturing — the cheapest point to change scope.

### 5. Run the app + capture
Start the app with test data (its README). Then the capture REPL
`MANUAL_CONFIG=$WS/manual.json node $S/scripts/repl.mjs` and one `steps/NN-*.js` per screen, each ending in
`shot(page, name, marks)` + `slide({...})`. Check marks with `$PY $S/scripts/overlay.py $WS <shot>` as you go.
Write steps so they replay from fresh data. Procedure, mark rules and traps: **references/capture.md**.
Shrink shots before keeping them: `$PY $S/scripts/optimize_shots.py $WS/shots`.

### 6. Build
```
$PY $S/scripts/manual.py $WS/manual.json --all --pdf --md
```
→ `<ws>/out/<out_name>-ALL.pptx` + one per chapter edition, each with a PDF (Keynote on macOS, PowerPoint on
Windows, LibreOffice anywhere; none installed ⇒ PPTX only, say so) and, with `--md`, a Markdown edition
(`<out_name>-<Edition>.md` + `out/md-images/`, the shots cropped like the slides with the boxes drawn — for a wiki
or a repo). Editions build into `out/.staging/` and replace `out/` only when
every edition and PDF succeeded. A chapter with no task slides fails the build — add `--draft` for a mid-capture
preview. The build refuses overflowing steps/tips/tables and step/mark mismatches — fix the content, don't bypass.

### 7. Visual QA loop (do not skip)
Render pages, hand them to a **fresh** subagent with the QA prompt in **references/qa.md**, fix what it returns
(re-capture or re-mark; placer changes need a full re-QA because badges move on every slide), rebuild, repeat
until it answers SHIP. Report the edition paths and how many QA rounds it took.

## Edit an existing manual by chat

Most requests are content edits typed in plain language — "slide editor-02 step 2 should say …", "add a tip to
viewer-03", "swap these two slides", "split this slide in two", "add a row to the status table".

1. Find the slide by its `shot` name or task title in `manifest.json`; tables, chapters and cover text are in
   `manual.json`.
2. Edit only what was asked. Keep the rules: step count = mark count (a new step needs a new box — that means a
   re-capture, so say so instead of faking it), on-screen text in quotes, tip ≤ ~120 chars. Wording about
   behaviour is checked against the app's code and messages, not invented.
3. Rebuild (`manual.py --all`, plus `--pdf` where a renderer exists) and show the changed slide(s).
   If the workspace has replayable `steps/`, make the same wording change in the step too: a full `replay.mjs`
   rewrites `manifest.json` from the steps (`--no-sync-manifest` skips that).

## Refresh an existing manual (UI changed)

The workspace is the manual's source: `manual.json` + `manifest.json` (polished wording) + `steps/` (replayable
capture) + `shots/` (accepted pictures). A refresh re-takes pictures and keeps wording.

1. **What changed:** `git log <captured_sha>..HEAD --oneline -- <code_paths>` in the app repo → affected chapters.
2. **Fresh data:** reset the app's test data the way its README says, start it.
3. **Replay:** `MANUAL_CONFIG=$WS/manual.json node $S/scripts/replay.mjs` → `shots-new/`. It stops at the first
   step that no longer works — fix that step (the UI moved), reset, replay again. A successful full replay also
   syncs `manifest.json` from the steps' `slide()` calls (wording and step-file order; old file kept as
   `manifest.json.bak`; `--no-sync-manifest` for pictures only).
4. **Diff:** `$PY $S/scripts/diff_shots.py $WS` → `refresh-report.md`: broken · changed · new · unchanged.
   Look at every changed slide's new shot; `--accept <shot…>` / `--accept-changed`.
   A changed mark count means the steps must be re-counted.
5. **Wording:** `$PY $S/scripts/check_copy.py $WS/manual.json` lists quoted labels no longer in the app's
   messages (`copy.messages` in manual.json) — fix those steps/tips in the step files (the replay copies them into
   `manifest.json`; with `--no-sync-manifest` edit `manifest.json` directly) and re-read the code for changed
   rules/tables.
6. **Release:** bump `version`, set `captured_at` / `captured_sha`, `manual.py --all --pdf` (the previous version
   is archived), QA the changed slides (qa.md §4), note the refresh in PROGRESS.md.

## Files

| Path | Use |
|---|---|
| `scripts/setup.py` | one-shot workspace tooling: venv + requirements, Playwright + chromium, names the PDF renderer |
| `scripts/manual.py` | composer + edition loop + staging/publish + PDF export (`--pdf`) + Markdown export (`--md`) |
| `scripts/export_md.py` | Markdown edition: tables, steps, cropped shots with boxes, tips (`manual.py --md` calls it) |
| `scripts/build_manual.py` | slide primitives: task slide (steps, tip slot, crop-to-marks, badge placer), tables, cover, dividers |
| `scripts/inspect_template.py` | template facts (layouts, placeholders, colours), `--suggest` config block, `--render` preview |
| `scripts/cap.mjs`, `scripts/repl.mjs` | Playwright session (configurable login, env-var passwords, identity check), `shot()` with marks, REPL that keeps pages alive |
| `scripts/overlay.py` | preview a shot's marks before building |
| `scripts/qa_render.py` | QA pages from the PDF at ~200 dpi (pdftoppm) |
| `scripts/manifest.mjs` | manifest upsert/sync shared by `repl.mjs` and `replay.mjs` |
| `scripts/replay.mjs`, `scripts/diff_shots.py`, `scripts/check_copy.py` | refresh: replay steps → shots-new, per-slide diff + accept, stale-label check |
| `scripts/optimize_shots.py`, `scripts/slim_template.py` | shrink shots and a large template before keeping them |
| `scripts/make_plain_template.py`, `templates/plain.pptx` · `dark.pptx` | the bundled unbranded 16:9 templates (light / dark) and their generator |
| `scripts/render.applescript` · `render.ps1` · `renderers.py` | Keynote (macOS) / PowerPoint (Windows) PDF+PNG export; renderer detection incl. LibreOffice |
| `references/capture.md` · `content.md` · `template.md` · `qa.md` | read at steps 5 · 4 · 3 · 7 |
| `assets/example/` | `manual.json` + `manifest.json` of the demo manual — the reference implementation |
