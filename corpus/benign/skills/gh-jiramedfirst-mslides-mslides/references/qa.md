# QA — the visual review loop

A manual is done when a **fresh reviewer** has looked at every rendered slide and answered SHIP. The author
never approves their own deck: the same context that placed a box will read it as correct. Real manuals have
needed several rounds; most blockers were invisible in the JSON and obvious on the page.

## 1. Before the reviewer: mechanical checks

1. **Marks preview** while capturing: `$PY $S/scripts/overlay.py <ws> <shot>…` → `<ws>/preview/`.
2. **Build every edition with PDFs:** `$PY $S/scripts/manual.py <ws>/manual.json --all --pdf`.
   - `manual.py` refuses a slide whose step count ≠ mark count — fix the manifest or the marks, never the check.
   - macOS renders through Keynote. Before the first export, `open -ga Keynote` and give it a few seconds.
3. **Validate the package** if you have an OOXML validator (e.g. a pptx skill's `validate.py`). It catches broken
   XML and repair prompts, not visual faults: invisible text passes.
4. **Render pages for review** (one PNG per slide, ~200 dpi, into `<ws>/qa<N>/`) from the PDF built in step 2:
   ```bash
   $PY $S/scripts/qa_render.py <ws>/manual.json <ws>/qa<N>            # pdftoppm -r 200 (poppler); --dpi N, --edition <code>
   ```
   Judging 1–4 px gaps and badge overlaps needs this resolution; Keynote's PNG export is fixed at 960×540 and
   PowerPoint's at 1920×1080, so the direct exports are a fallback for a quick look only:
   ```bash
   osascript $S/scripts/render.applescript <ws>/out/<out_name>-ALL.pptx <ws>/qa<N>          # macOS: Keynote (960×540)
   powershell -NoProfile -ExecutionPolicy Bypass -File $S\scripts\render.ps1 <ws>\out\<out_name>-ALL.pptx <ws>\qa<N> png   # Windows: PowerPoint
   ```
   Review the ALL edition; role editions are subsets built by the same code.

## 2. The reviewer pass

Dispatch a **fresh subagent** (no capture or build history in its context). It reads every PNG and reports.

### Prompt template

```
You are the visual QA reviewer for a <language> user manual deck. Do not edit any file. Report only.

Pages: <ws>/qa<N>/s-*.png (one PNG per slide, in order). Read EVERY page; do not sample.
Slide map (ALL edition): 1 cover, 2 table of contents, 3–<k> intro tables, then for each chapter a divider
followed by its task slides (<chapter list with slide ranges>), then reference tables, then the closing slide.

A task slide has: numbered steps on the left, a screenshot on the right with outline boxes in the accent colour,
each with a numbered badge, and an optional tip box bottom-left. Step N must point at box N.

For every slide check:
1. Every step has exactly one box, and box N surrounds the control step N names.
2. Boxes do not overlap or share an edge; each box fully encloses its text (no line cuts through a value).
3. Each badge sits outside its own box, covers no text, and is unambiguously nearer its own box than any other.
4. The crop shows what the steps mention: no cut labels, columns or popovers; not mostly empty.
5. No developer text in the UI (env-var names, mock/debug messages, text in the wrong language, raw ids).
6. No stale or retired data (options marked retired/deprecated, leftover test records).
7. A multi-slide flow shows the same record throughout (number, title, amount).
8. No irrelevant UI noise in the crop (e.g. an empty "0 selected" bulk bar).
9. Text is readable: no text the same colour as its background, nothing overflowing its box, the tip fits its
   slot, no clipped glyphs.
10. Tables and dividers: no clipped cells, no tiny auto-shrunk text.

Output exactly one of:
- SHIP
- A numbered list of blockers, each: slide number · shot name if visible · what is wrong · suggested fix ·
  class = capture | marks | build | content.
Group by HIGH (wrong or misleading), MED (confusing), LOW (cosmetic). Do not list things that are fine.
```

## 3. Blocker classes seen in practice

| Class | What it looks like | Fix lane |
|---|---|---|
| Overlapping boxes | two buttons boxed edge-to-edge; badge on the shared edge | marks: inset/separate, leave a gap |
| Badge on text / ambiguous badge | badge covers a label, or sits between two boxes | marks: `badge` hint (`left`/`right`/`above`/`below`); build: placer |
| Step without box | step names a control nothing surrounds | marks: add a box, or move the sentence to the tip |
| Two badges, one box | marks 2 and 3 on the same element | marks |
| Cut popover | legend/tooltip clipped at the right | capture: wider viewport; if still clipped, app bug |
| Crop cuts labels | left labels or right columns missing | marks: widen the mark, scroll before the shot |
| Empty crop | a small dialog floating in a mostly blank picture | marks: box the content area |
| Developer / mock text | a debug banner, "answered from MOCK…" | capture: hide in DOM / realistic value |
| Stale / retired data | a "(retired)" option, old records in the queue | capture: clean the data, re-capture the flow |
| Inconsistent record | slide 23 submits MANUAL-A, slide 24's toast says MANUAL-B | capture: one record per flow |
| Generic bulk bar | "0 selected" at the bottom of the crop | marks: keep marks higher so the crop drops it |
| Invisible text | light-template colours on a dark template (or the reverse) | build: `template.colors` |
| Text overflowing the tip slot | tip > 3 lines | content: tip ≤ 120 chars |
| Box cuts a value | outline runs through "40,000.00" | marks: taller box |
| Step text ≠ screen | step says a field auto-fills; the shot shows "—" | capture after the action, or reword |

**capture** and **marks** fixes touch `shots/` (re-capture, or edit `shots/<name>.json`).
**content** fixes touch `manifest.json` / `manual.json`. **build** fixes touch `scripts/build_manual.py`.

## 4. Fix → rebuild → re-QA the whole deck

**Refresh exception:** after a refresh where `build_manual.py` did not change, only slides whose shot was
accepted as changed/new (refresh-report.md) or whose text was edited can differ — QA those, plus the cover.
Anything that touched `build_manual.py` or the template is a full re-QA as below.

- Apply all blockers of a round, rebuild all editions, re-render, and send the **whole** deck to a new
  fresh reviewer. Never re-check only the slides you touched:
  - a placer or layout change in `build_manual.py` moves badges on every slide;
  - a re-capture changes the crop, which moves every badge on that slide.
- Record per round what changed (re-captured / re-marked / reworded / data tweaks) in `<ws>/PROGRESS.md`.
- Repeat until a reviewer returns SHIP. For a fact-heavy deck (status tables, rules), run a second reviewer
  that re-checks each table row against the app's code, also returning SHIP or blockers.

## 5. Debugging badge placement

The placer scores each candidate position by `(geometric hits, ink under the badge, order)`; lowest wins.

```bash
BADGE_DEBUG=<shot> $PY $S/scripts/manual.py <ws>/manual.json --role <code>
```

prints, per mark, every candidate's cost and ink share. Use it when a badge keeps landing on text:
- ink cannot tell a text label from UI chrome → give that mark a badge hint: `left`, `right`, `above` or `below`
  (`opts.badges` in the capture step — a hint typed into `shots/<shot>.json` is lost on the next replay);
- the build prints `warning: <shot>: badge N is about as close to box M as to its own` when the chosen spot is
  still ambiguous → add a hint that puts the badge on the far side from the neighbour, or separate the boxes.

The debug build overwrites that edition's output — rebuild it afterwards.

## 6. Keynote trouble

`Keynote cannot export while the screen is locked or asleep (… -1712)`: Keynote only answers while the display is
unlocked and awake. Unlock the Mac, run `caffeinate -d` in another terminal for the length of the build, rebuild.

- "Keynote did not open <deck>": Keynote may be showing a dialog (an import error, an open panel). Look at it —
  "invalid file format" means the PPTX itself is the problem; anything else, dismiss it and rebuild.
- Export fails with `-609`, `-1708` or an "unmerge id" error after an earlier crash: **quit Keynote from its
  menu** (Keynote › Quit), then rebuild. `pkill Keynote` does not clear it.
- No Keynote: on Windows `manual.py --pdf` uses PowerPoint (`render.ps1`, COM) when it is installed, else
  LibreOffice `soffice --headless` anywhere (`MSLIDES_SOFFICE=<path>` if it is not on PATH or in the stock
  install folder); with none, it writes the PPTX only and says so.

## 7. Release

- Output may be **confidential** (screenshots of internal systems): keep it in the workspace, outside any public
  repository. Do not commit decks or publish them on a public host; hand the files over directly.
- Ship the PPTX (editable) and the PDF together.
