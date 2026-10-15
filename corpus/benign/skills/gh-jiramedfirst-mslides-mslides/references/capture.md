# Capture — environment, sessions, shot order, marks

Every screenshot comes from an app instance **you control**: a local dev server or a disposable test
environment, with test accounts and sample data. Output lands in the workspace (`<ws>/shots/`).

## Why local / test, never production

- Capturing walks records through their whole lifecycle (create, reject, send back, approve). That writes data;
  a shared environment's users would see it, and production must never carry sample records.
- You may need data tweaks no UI allows (a failed background job, an expired date). Only a private copy can take them.
- `cap.mjs` types passwords into the login form. It refuses any `base_url` that is not loopback unless that host
  is listed in `capture.allow_hosts` — add a host there only when it really is a test environment.

## 1. Environment

1. Start the app the way its README says (dev server, docker compose, …) and seed test accounts — one per role
   in the manual. Prefer the app's own seed/fixture mechanism over hand-made accounts.
2. Put the base URL and the accounts in `manual.json` → `capture` (content.md). Point `capture.login` at the
   login form's selectors; read them from the app's code, not by guessing.
3. Install Playwright where `cap.mjs` can resolve it: the app repo (`"repo"` in manual.json), the workspace
   (`cd <ws> && npm i -D playwright`), or any `node_modules` on `NODE_PATH`. Then `npx playwright install chromium`.
4. Give it the passwords through the environment, never a file:
   ```bash
   export MANUAL_PW_VIEWER=…  MANUAL_PW_EDITOR=…     # one per role key (uppercased, non-alnum → _)
   export MANUAL_PW=…                                # or one shared fallback
   ```
   PowerShell: `$env:MANUAL_PW_VIEWER='…'`, `$env:MANUAL_PW='…'`.
   Ask the user to set them in their own shell. Never type, echo, print or paste a password into the chat, a file
   or a command line that ends up in shell history.

## 2. Sessions

- `session(role)` opens a fresh browser context (viewport, locale, timezone from `capture`), logs in as
  `capture.users[role]` and then verifies who it is:
  - with `capture.login.whoami` (a URL returning JSON) it asserts the email at `whoami_email` (dot path, default
    `email` / `user.email`) equals the role's account — a stale cookie or a wrong account throws instead of
    silently shooting the wrong role;
  - without it, it asserts the URL left the login page.
- A role with no test account: add it to the app's seed, not to the chat.

## 3. Plan the lifecycle before the first shot

States exist only in order: you cannot shoot "returned by the reviewer" before something was sent for review.

1. Read the app's workflow/transition code and list every state a role sees.
2. Write a capture order per phase (role A creates → role B reviews → role A fixes → …) in the workspace plan.
3. Name every created record `MANUAL-<letter> <realistic title>` (or another obvious sample-data prefix) so it is
   findable and clearly not real data.
4. Keep **one record per flow**: a multi-slide flow that switches records halfway (the toast names a different
   record than the previous slide submitted) is a QA blocker.
5. Log every data tweak (table, id, column, old → new, why) in `<ws>/PROGRESS.md`. Ask the user before any
   direct SQL; prefer the UI.

## 4. Capture REPL

```bash
MANUAL_CONFIG=<ws>/manual.json node $S/scripts/repl.mjs          # 127.0.0.1:9555, keeps pages alive between steps
curl -s -H "x-repl-token: $(cat <ws>/.repl-token)" --data-binary @<ws>/steps/00-lib.js localhost:9555   # helpers
curl -s -H "x-repl-token: $(cat <ws>/.repl-token)" --data-binary @<ws>/steps/20-edit.js localhost:9555  # one step
```
PowerShell: `$env:MANUAL_CONFIG="<ws>\manual.json"; node $S\scripts\repl.mjs`, then
`curl.exe -s -H "x-repl-token: $(Get-Content <ws>\.repl-token)" --data-binary "@<ws>\steps\20-edit.js" localhost:9555`
(`curl.exe`, not the `curl` alias of `Invoke-WebRequest`).

Each body runs as an async function with `{P, session, shot, aria, cap, slide}`. `P` persists across calls.
Run `return await aria(p)` first and build locators from the role/name tree it prints. The token file is 0600
and deleted when the REPL exits; the REPL refuses requests without it.

`shot(page, name, marks, opts)`:
- Viewport screenshot (`capture.viewport`, default 1600×900) → `shots/NAME.png` + `NAME.json`
  `{w, h, marks:[{x,y,w,h,badge?}]}`. Marks are locators or CSS strings, numbered 1..n in order.
- Waits for network idle and, if `capture.loading_selector` is set, for that element (skeleton/spinner) to go.
- Throws if a mark's locator is not found, or if a mark is entirely outside the viewport after scrolling
  (both axes). A mark only partly visible is clamped with a warning — keep a slide's marks within one viewport.
- Removes toasts matching `capture.toast_selector` unless `opts.keepToasts: true`. Pass it when a step points at the toast.
- `opts.badges: [null, 'left', 'above', …]` sets a per-mark badge hint: `left`, `right`, `above` or `below`. Keep hints in
  the step, not in a hand-edited `shots/*.json`: a replay rewrites that file from the step, and `diff_shots.py` reports
  a differing hint as `changed`.
- A mark touching the screenshot frame (a drawer header at the right edge) is drawn inside the picture at build time.

`slide({...})` upserts the manifest entry with the same `shot`. A full `replay.mjs` does the same for every step
and also puts `manifest.json` in step-file order (see 4b).

```js
// steps/00-lib.js — helpers live on P so later steps reuse them
P.dismissBanner = async (p) => {
  const b = p.getByRole('button', { name: 'Dismiss', exact: true });
  if (await b.count()) { await b.click(); await p.waitForTimeout(300); }
};
return 'lib ok';
```

```js
// steps/21-editor-form.js — act, mark, shot, slide
const p = P.editor ??= await session('editor');
await p.getByRole('link', { name: 'New item' }).click();
await p.getByLabel('Name').fill('Wireless keyboard');
await shot(p, 'editor-02-form', [
  p.locator('#f-name'),                       // label + control, not the bare input
  p.locator('#f-category'),
  p.getByRole('button', { name: 'Save' }),
]);
slide({ chapter: 'editor', task: 'Fill in and save the item', kicker: 'EDITOR · New item',
  shot: 'editor-02-form',
  steps: ['Type the "Name" (**required**)', 'Pick a "Category"', 'Click "Save"'],
  tip: '"Notes" is optional.' });
return 'ok';
```

- **The steps are the source of wording and order.** A full `replay.mjs` upserts every `slide({...})` into
  `manifest.json` (steps, tips, task, kicker…) and orders it the way the steps ran, so a slide captured out of order
  while exploring lands where its step file puts it. It lists what changed and keeps the old file as
  `manifest.json.bak`. Wording polished only in `manifest.json` is reverted — change the step too, or replay with
  `--no-sync-manifest` for pictures only. Entries no step produces (hand-added) are kept after the others, with a
  warning; `--only` runs upsert in place and never reorder.

The demo in the plugin repo (`examples/demo/steps/`) is a complete, replayable set.

## 4b. Write every step so it can be replayed

The manual will need refreshing when the UI changes (SKILL.md "Refresh"). `replay.mjs` re-runs `steps/` against
freshly reset test data in one go, so write each step from the start as if it will be replayed:

- **`steps/NN-name.js`, numbered in capture order** (`00-lib.js`, `10-list.js`, `20-create.js` …; leave gaps).
  Only `NN-*.js` files replay. Exploration (`return await aria(p)` probes, one-off checks, retakes) goes in
  `<ws>/scratch/`, never in `steps/`.
- **One state path.** The steps, run in order on fresh data, must produce every state the shots need. A retake is
  an edit of the original step, not a new `NN` file that repeats half of it.
- **Find records by name, never by id.** `goto('/records/8f3a…')` breaks on the next seed. Search for the
  `MANUAL-…` title and click it.
- **No hand SQL.** A data tweak a shot depends on is a step too — via the UI, or a database call inside the step —
  so replay reproduces it. Log it in PROGRESS.md as usual.
- **No wall-clock assumptions.** Dates typed into forms must be computed from today.
- Session per role once (`P.s ??= await session('viewer')`), reused by later steps.

## 5. Mark rules

| Rule | Why |
|---|---|
| One box per step, in step order; step count == mark count (`manual.py` refuses otherwise) | a step without a box was the most common QA blocker |
| A field mark covers **label + control** (a wrapper locator, not the input) | a bare input box leaves the reader guessing which field |
| Adjacent boxes need a visible gap; never share an edge | touching boxes read as one, and the badge lands on the shared edge |
| A grouped control (two linked selects) gets one box around the group | two boxes for one decision confuse the step count |
| A box must enclose its text fully — make it taller rather than cut through a value | an outline through "40,000.00" hides the value |
| A badge hint (`left`/`right`/`above`/`below`) when the placer keeps landing on text or between boxes; the build warns about an ambiguous spot | badges on labels are unreadable; one between two boxes reads as the neighbour's |
| Mark the content area when the crop would be mostly empty — the crop tightens around marks | a small dialog floating in a blank picture |
| Widen marks when the crop cuts a label or column | the crop is derived from the marks' bounding box |
| Keep a slide's marks within one 16:9 window | the builder refuses marks that span more than one |

Preview before building: `$PY $S/scripts/overlay.py <ws> <shot>…` → `<ws>/preview/<shot>.png`.

## 6. Keep noise out of the shot

- **Developer text** (debug banners, mock-service messages, raw ids): hide it in the DOM before the shot
  (`p.evaluate(() => el.remove())`), and reword any tip that refers to it.
- **Stale / retired data** (deactivated options, leftover test records in a queue): clean it up via the UI,
  then re-capture the whole flow on fresh data.
- **Placeholder text in the wrong language**: craft a realistic value in the manual's language, logged in PROGRESS.md.
- **Generic bars** (an empty "0 selected" bulk-action bar) — keep them below the marks so the crop drops them.
- **Open menu hides the page:** while a dropdown/menu/modal is open the rest of the page is `aria-hidden`, so
  `getByRole(...)` marks for elements outside it fail with "callout target not found". Use CSS/text locators for
  those marks: `p.locator('button').filter({ hasText: 'Save' })`.
- **Popover cut off:** widen the viewport first. If it is still clipped, the clip is app-side — mark differently
  and report it as a bug.

## 7. Bugs found while capturing

1. Triage: app bug, seed-data gap, or an artefact of your local setup?
2. App bug → note it in PROGRESS.md and report it through the project's normal flow. Data/setup artefact → fix the
   data, log it. Never ship a shot that shows a bug as intended behaviour.
3. After the fix lands, re-capture every affected shot.
