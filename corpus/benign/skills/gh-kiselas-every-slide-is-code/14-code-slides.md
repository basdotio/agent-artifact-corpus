# Code slides (optional plugin)

For technical talks. `runtime/code.js` + `runtime/code.css` add code blocks with Shiki highlighting, magic-move between code states, line focus per step, diffs and typing, and five slide layouts (`code-full`, `code-side`, `code-over`, `terminal`, `filetree`) that make the code as large as the slide allows. The core stays as it is; a deck without the two slots is unchanged. The example is `examples/code/deck.html` (10 slides, every layout once).

## When code earns a slide

- Show **8–15 lines**, never a whole file. The plugin warns above 18. Cut to the lines the sentence in the title is about; the rest goes in notes or a link.
- The title states what the code proves ("The fix lives in the writer, not in the reader"), not what it is ("import.ts").
- One idea per state. If a click changes four things, split it into two clicks or use line focus.
- Code that changes shape between clicks: **states** (morph). Code that stays and gets explained: **line focus**, with a **note** on the line or a **claim** beside it. A patch: **diff**. Building something up on stage: **cursor**. A command line: **terminal**. "Where is this?": **filetree**.
- Prefer the deck's own light palette. A dark block inside a light deck is a deliberate contrast (`data-code-theme="dark"`), used once, and under a third of the slide (see Gotchas).

## Enable

Two slots, in this order (the plugin must come before the deck script that calls `Deck.slide`):

```html
<style id="deck-kit-css"></style>
<style id="deck-kit-code-css"></style>          <!-- plugin CSS, right after the runtime CSS -->
...
<script id="deck-kit-js"></script>
<script id="deck-kit-code-js"></script>         <!-- plugin JS, right after the runtime JS -->
<script>Deck.slide(...)</script>
```

`node scripts/sync-runtime.mjs deck.html` fills the slots, like the runtime's. Slides with code and no `id` get one (`code-slide-N`); give slides real ids anyway. A setup mistake (plugin after the deck script, missing CSS slot, unknown layout, a bad `data-note`) shows as a **red bar over the deck** as well as in the console, so it cannot be missed in rehearsal.

## Layouts

Set on the slide, as `data-layout="code-side"` or as a class (`class="slide code-side"`). Without one, a slide with a single code block gets `code-full`, one with `.dk-claims` gets `code-side`, one with `data-note` gets `code-over`; `data-layout="none"` keeps the plain block (28 px, no fitting to the slide). Every layout keeps the kit's rules: the rest frame of every step carries the message, the block is sized once to the maximum over its steps (rows, columns), nothing has a fixed height.

**The size rule** (measured once in `setup`): the block takes the largest font size, at most the layout's cap, for which (a) the longest line of every state fits the width, and (b) every row fits the free height, from the block's top to the bottom margin (`--dk-code-bottom`, 90 px) minus whatever stands below it in the same column. Never below `data-code-min` (24 px): then lines wrap, and the plugin warns. Then the panel is stretched towards the free height (at most 1.25–1.4 times the content) and the code sits in the middle of it; in `code-side`, `code-over` and `filetree` the whole row also moves down by half the spare height (at most 96 px), so a short state does not leave the bottom of the slide empty and does not float away from its title. `data-code-max="40"` changes the cap, `data-code-size="30"` pins a size (shrink-to-fit only, the older behaviour).

| Layout | Cap | Free height | What it is |
|---|---|---|---|
| `code-full` | 44 px | to the bottom margin, minus captions under the block | one block, full width: 8–12 lines come out at 32–40 px |
| `code-side` | 36 px | to the bottom margin, panel centred | code left, `.dk-claims` or `.dk-companion` right (520 px, `--dk-side-w`) |
| `code-over` | 36 px | same | code 1080 px wide (`--dk-over-w`), callouts in the column on its right |
| `terminal` | 40 px | as `code-full` | a shell session, one step per command |
| `filetree` | 40 px | as `code-side` | a directory tree, `.dk-claims` on the right |

Keep titles to two lines: the free height is measured before `data-fit` shrinks a long title.

### `code-full`

```html
<section class="slide" data-layout="code-full">
  <h2 data-fit="2">Every price read trusts the cache for sixty seconds</h2>
  <pre data-code="ts" data-file="price-cache.ts" data-numbers data-lines="*|5-6|8-10"> ... </pre>
</section>
```

A caption under the block is fine (it is subtracted from the free height); the block then takes what is left.

### `code-side`: claims in step with the code

```html
<section class="slide" data-layout="code-side">
  <h2 data-fit="2">The fix lives in the writer, not in the reader</h2>
  <div data-code="ts" data-numbers> <pre data-code-step>...</pre> <pre data-code-step>...</pre> <pre data-code-step>...</pre> </div>
  <div class="dk-claims">
    <p><b>The bug</b>The loop writes and forgets.</p>
    <p><b>The obvious fix</b>Delete the key.<small>It works on one node only.</small></p>
    <p><b>The real fix</b>Write once, publish once, every node evicts.</p>
  </div>
</section>
```

Claim *k* goes with code step *k* (`from + k`): it fades in as the state changes and the previous one fades out, in the same grid cell, so the column is as tall as the tallest claim and nothing jumps. `data-claims="stack"` on `.dk-claims` keeps the earlier claims and steps them back instead. `<b>` is the small caps label, `<small>` the muted second line; keep a claim under 20 words. The plugin warns if the claims and the steps differ in number. Claims are ordinary builds (`data-step`, `data-anim`, `data-out` are set for you and can be overridden per claim).

### `code-over`: a callout on a line

```html
<section class="slide" data-layout="code-over">
  <pre data-code="ts" data-diff data-lines="*|2-4|5-6|8-9"> ... </pre>
  <div data-note="2-4" data-step="1"><b>Goes</b>One database round trip per row.</div>
  <div data-note="5-6" data-step="2"><b>Comes</b>One batch write, then one event.</div>
</section>
```

`data-note="5-6"` (or `"5"`) names lines of the state shown at the note's `data-step` (lines are counted per state, like `data-lines`). Setup measures the rows once and draws a bracket after the longest of those lines, an elbow arrow, and a card in the column right of the block; nothing is measured in `frame`. A note leaves when the next one appears (`data-note-keep` keeps it). Put the target lines in that step's `data-lines`, so they are the lit ones (the plugin warns if they are dimmed). Notes need at least 300 px right of the code; narrow the block with `--dk-over-w` if the plugin says so. A note's default step is the first step whose focus covers its lines.

### `terminal`

```html
<pre data-terminal data-file="zsh · shop">
$ npm test -- price-cache
! FAIL  price-cache.test.ts
! expected 9, received 7
$ git apply fix.patch
$ npm test -- price-cache
PASS  price-cache.test.ts
</pre>
```

A line that starts with `$ ` is a command and starts a **step**; the lines after it are its output (`! ` marks an error line, drawn in the "removed" colour, the `!` itself is not shown). `data-prompt="~/shop $"` changes the prompt string. No syntax highlighting: the prompt is accent-coloured, the command bold, the output a little quieter. Each step types its command character by character and then shows its output line by line, all a function of the step's progress (a jump, the rest frame, PDF and video agree, the caret shows only while typing). A step lasts at most 2.8 s, so it is finished inside the default 3 s hold of the video timeline (longer transcripts: give the slide `data-hold`). The block is sized to the whole transcript, so the last step fills it; keep it to 12 lines. It takes the deck's palette; `data-code-theme="dark"` gives the dark window.

### `filetree`

```html
<section class="slide" data-layout="filetree">
<pre data-filetree>
shop/
  src/
    cache/
      price-cache.ts       # reads
    import/
      import-prices.ts     # writes
  package.json
</pre>
<div class="dk-claims"><p>...</p><p>...</p></div>
</section>
<section class="slide"> <pre data-code="ts" data-file="import-prices.ts"> ...
```

Two spaces per level, a trailing `/` for a directory, `  # text` for a comment; the connectors are drawn for you. Step 0 shows the tree; step 1 marks **the file the next slide's code belongs to** (the `data-file` of the next slide's first block; `data-focus="src/import/import-prices.ts"` names it explicitly, a path suffix or a bare name) and dims the rest except its directories. `data-filetree-static` marks it from the start (one step). If the file is not in the tree, nothing is marked and the console says so.

## Code and a chart or table beside it

The code block owns the step numbers (state *k* is step `from + k`); a companion reads the same numbers, so one click moves both. Put the companion in `.dk-companion` on a `code-side` slide and drive it from the slide's `frame` with `st.p(step, delay, dur, curve)` (07-charts.md), or with `data-step` on plain markup:

```html
<section class="slide" id="bench" data-layout="code-side">
  <h2>One batch write is thirteen times faster than the loop</h2>
  <div data-code="ts" data-file="bench.ts">
    <pre data-code-step> ...the loop... </pre>          <!-- step 0 -->
    <pre data-code-step> ...one batch... </pre>         <!-- step 1 -->
  </div>
  <div class="dk-companion"><svg class="chart" width="520" height="400" viewBox="0 0 520 400"></svg></div>
</section>
```

```js
Deck.slide('bench', {                    // no `steps`: the code block already counts them
  setup(el) { /* build the bars once: el._rows = [{ v, w, rect, val, step: 0 }, { ..., step: 1 }] */ },
  frame(el, st) {
    for (const r of el._rows) {
      const p = st.p(r.step, .1, .9, Deck.ease.outExpo);      // bar k grows at step k
      r.rect.setAttribute('width', +(r.w * p).toFixed(2));
    }
  },
});
```

Rules that keep it honest: bars start at zero and share one scale; the state that introduces a bar is the state that shows the code producing it; the comparison ("13× faster") is written on the chart at the step it becomes true, not left to the eye; label the unit and mark invented figures as illustrative. A table works the same way: `<table class="dk-companion">` with `data-step="k" data-anim="fade"` on each `<tr>` (a row appears at the step of the code that produced it), and the row that matters in the accent colour. Width of the column is 520 px: use 3 columns at most, 26 px text. The code slide's `Deck.slide` call goes after the plugin script like every other (the plugin merges its own `setup`).

## Markup

```html
<pre data-code="ts" data-file="cache.ts" data-numbers data-lines="*|5-6|8-10">
const TTL = 60_000;
...
</pre>
```

Escape `<` and `&` as in any HTML. Each state is dedented on its own.

| Attribute | Meaning |
|---|---|
| `data-code="ts"` | language. `ts js python go rust sql json yaml bash html css java c cpp ...` (any Shiki language id; aliases `py rs sh yml`); `text` for none |
| `data-file="cache.ts"` | filename chip above the code |
| `data-numbers`, `data-numbers="12"` | line-number gutter, from 1 or from 12 |
| `data-lines="1-3\|5\|7-"` | line focus, one spec per step (below) |
| `data-diff` | diff mode (below) |
| `data-code-cursor` | new code types itself in (below) |
| `data-terminal`, `data-prompt` | a shell session (Layouts) |
| `data-filetree`, `data-focus`, `data-filetree-static` | a directory tree (Layouts) |
| `data-code-theme="light\|dark"` | palette preset for this block; also allowed on `.deck` |
| `data-step`, `data-anim` | the block's own entrance, like any element (`rise`, `fade`) |
| `data-code-from="n"` | step at which the first state is shown (default: the block's `data-step`, else 0) |
| `data-code-dur=".9"` | seconds per state change |
| `data-code-dim=".38"` | opacity of lines outside the focus |
| `data-code-size="34"`, `data-code-min="24"`, `data-code-max="40"` | pinned size; floor for shrinking; cap for a layout's auto size |

**Steps and states.** Every step changes one thing: state *k* appears at step `from + k`. The slide's step count grows to fit.

```html
<div data-code="ts" data-file="import.ts" data-numbers>       <!-- states as children -->
<pre data-code-step>...first state...</pre>
<pre data-code-step data-lines="4-5">...second state, lines 4-5 in focus...</pre>
</div>

<pre data-code="ts">                                           <!-- or one source, states split by --- -->
...first state...
---
...second state...
--- 2-3|5
...third state, two steps: lines 2-3, then 5...
</pre>
```

`---` is taken as a separator; for YAML use `data-code-step` children, or `data-code-sep="off"`. A separator may carry a focus spec (`--- 2-3|5`).

**Line focus.** `data-lines="*|5-6|8-10"`: `*` (or empty) is every line, numbers are 1-based lines of that state, `,` joins ranges (`1,3-4`), `7-` runs to the end. On a single-state block each part is one step. On a multi-state block, parts go to steps in order (their count must match), or put `data-lines` on each state (`4-5|6` on a state gives it two steps). Focused lines stay at full strength, the rest dims; the rest frame of every step shows its focus without motion.

**Diff.** With `data-diff`, every line starts with `+ `, `- ` or two spaces (marker, then one space). The marker moves into a sign column and the line gets a tint and a bar. The sign carries the meaning, so the block reads in greyscale and for colour-blind viewers: `+` and `-` are different glyphs in a fixed column, the bars sit at the left edge, and the two colours are blue-ish and amber-ish (`--dk-code-ins` from the accent, `--dk-code-del` from the second accent), never red and green alone. Diff plus `data-lines` walks through a patch: what goes, what comes, what ties it together.

**Cursor.** `data-code-cursor`: at each state change removed code fades, moved code glides, and new code types in character by character in reading order, with a caret. The first state types in on the block's step. Typing is a function of the step's progress, so a jump, the rest frame and the video all agree; the caret shows only while typing. Duration follows the amount of new text (0.7–2 s).

## Magic move, and why it is our own

Between two states, lines are matched first (longest common subsequence of trimmed lines), then the words and punctuation marks inside the changed hunks. Matched tokens glide to their new place (0.1–0.8 of the step), removed ones fade out first (0–0.35), new ones fade in last (0.45–1); colours switch half-way. A lone punctuation mark that matched far from any matched neighbour is not matched, so it does not fly across the block. Line numbers, signs and tints move the same way.

We did not wrap `shiki-magic-move`: as far as its docs show it animates by time (duration, stagger), and the kit needs the state as a pure function of the step's progress (00-agent-brief.md rule 2): that is what gives rest frames, jumps, PDF and video. The plugin does the diff once, in `setup`, and every frame is `paint(frame a, frame b, progress)`. Each state change is a hidden marker element with `data-step` and `data-anim="code-step"`, so the runtime counts the steps, reads the timing and knows when the slide goes idle.

## Highlighting and themes

Shiki 3 loads lazily from a CDN: core, the JavaScript regex engine and one grammar per language, each requested from jsDelivr and esm.sh at once, the first answer wins. Version and hosts: `Deck.code.config({ shiki: '3.13.0', hosts: ['jsdelivr', 'esm'] })`, before the deck script ends. While it loads, the block shows the same tokens uncoloured with identical metrics, so nothing jumps; `__ready` waits for it (10 s, then the built-in highlighter takes over with a console warning; in a live deck a slow CDN still upgrades the colours later, exports never do).

The Shiki theme is made of CSS variables, so code matches the deck without re-highlighting. `runtime/code.css` derives them from the deck's own `--bg --ink --muted --accent` and an optional `--accent-2`. Override any of them in the deck's `<style>`:

`--dk-code-fg bg line comment keyword string number const function type prop punct param tag attr out ins del`, plus `--dk-code-size` (28px for a plain block; layouts choose their own), `--dk-code-lh` (1.5), `--dk-code-pad-x/-y`, `--dk-code-radius`, `--dk-code-font`, `--dk-code-tint` (strength of the diff and mark tints, 10%), `--dk-code-bottom` (90px), `--dk-side-w`, `--dk-over-w`.

Presets `light` and `dark` set all of them. Keep the palette to what the deck already has: keyword = accent, everything else quiet. Code font: a local monospace stack by default; for a webfont put it in the Google Fonts link and in `--dk-code-font`.

### Palette guarantees

Every text role is at least **4.5:1** on the block background *and* on the diff and mark tints in both presets (the tints are 10%, not 15%, and the signs and the diff colours are the same dark or light values as the text). Measured with `node export/deck.mjs check` on real diff blocks, and with the WCAG formula for every role on the three backgrounds (block, `+` tint, `-` tint):

| Role | light preset (block `#f4f4f1`) | dark preset (block `#16181d`) |
|---|---|---|
| fg / out | 12.3 / 7.5 | 11.9 / 9.2 |
| comment, line numbers | 4.85 | 5.66 |
| keyword, attr | 6.45 | 7.54 |
| string | 6.22 | 8.94 |
| number, const, `-` sign | 5.53 | 8.54 |
| function, tag, `+` sign | 6.08 | 7.07 |
| type | 5.59 | 9.23 |
| punct | 5.70 | 6.74 |

The numbers are the worst of the three backgrounds. Before this version the same measurement gave: `+` `#1d4ed8` on its tint 4.29, `-` `#b45309` 3.31, punctuation `#666665` 3.68, and the deck's own amber annotation 4.49; the light preset's comment, number, type and punctuation colours were 3.6–4.4 on the tints. The derived palette (no preset) mixes every accent towards `--ink` (comment 80% of `--muted`, keyword 88% and `+` 84% of the accent, `-` 80% of the second accent, punctuation 80% of the text colour), so the same holds for any deck whose `--accent`, `--accent-2` and `--muted` reach about 5.5:1 on `--bg`: the example deck (`#f4f2ec` background) measures 5.02:1 at worst across all its blocks, and its amber (`--accent-2: #a04505`, 5.6:1) also passes for its own diagram labels. If `check` reports `low-contrast` on code, darken the deck's accent or set the `--dk-code-*` role it names.

## Size and containment

- Code is at least 24 px on the 1080 canvas (a plain block 28 by default; layouts 24–44 by the rule above). The gutter, signs and filename chip are 22–28 px, above the `check` floor of 20.
- Rule for long lines, applied once in `setup`: the block shrinks its font to fit the longest line of any state, never below `data-code-min` (24 px); a line still too long **wraps** at token boundaries with a hanging indent of two columns, and the plugin warns. There is no horizontal scroll and no clipping.
- A block is sized once: its height is the maximum over all its states (in wrapped rows), so nothing jumps between steps. Width comes from CSS (`width`, or the parent's grid column); no height is fixed in CSS.
- Layout is a monospace grid: the character width is measured once after fonts load and every token sits on a whole pixel. ASCII code only (the filetree's box-drawing characters are the exception); wide glyphs (CJK, emoji) break the grid.

## Offline

`bundle` inlines fonts and `<script src>`, but not the ES modules Shiki is made of. Store the highlighted tokens in the deck instead. Two commands, in this order (the first needs the network once and `export/` installed; the second is then offline with the same colours):

```bash
node scripts/sync-runtime.mjs --code-cache deck.html
node export/deck.mjs bundle deck.html deck.offline.html
```

The first writes `<script type="application/json" id="deck-kit-code-cache">` (a few KB); blocks whose text is in it never touch the network. Re-run it after editing code (unknown text falls back to Shiki, then to the built-in highlighter: coloured, less precise). Without the cache an offline deck still works and warns once in the console. `bundle` does not run the first command itself: it belongs to another tool, so for now a script or CI job runs both.

**One command, no Node:** open the deck once as `deck.html?code-cache` in Chrome (network for Shiki). A panel offers "Store in the deck file…" (Chrome's file picker: choose the deck itself; the highlighted tokens are written into it) and "Copy the `<script>` tag" (paste above `<script id="deck-kit-code-js">`). Same result as the command above; `Deck.code.inject(html)` and `Deck.code.cacheTag()` are the functions behind it. Terminal and filetree blocks are not highlighted and need no cache.

## Checks

```bash
node export/deck.mjs check deck.html               # 24+ px, containment, contrast, escapes-box on every step
node export/deck.mjs check deck.html --timeline    # atoms mid-glide stay inside the block
node export/deck.mjs check deck.html --no-webfonts # fallback monospace: wrap points move, nothing spills
node export/deck.mjs sheet deck.html               # look at every state and every focus
node export/deck.mjs pdf deck.html --steps         # one page per step, code is selectable text
npm run test:browser -- --only code                # determinism, transitions, idle, on Linux Chrome too
```

- `check` counts every token as a word, so code slides get a `density` warning; that is expected. Keep the number of *lines* low instead.
- `perf` is 1–3 ms per frame for 15 lines; a slide with three states holds about 120 nodes.
- Look at a morph live, once (open `deck.html#4`, press next): tokens crossing for a moment is normal; a mess for over half a second is not, so shorten the change or split it into two states.

## Gotchas

- The plugin script goes before the deck script that calls `Deck.slide`; it wraps `Deck.slide` so your `setup` still runs. If the order is wrong, a red bar says so and the `Deck.slide` hooks of the code slides do not run.
- Keep indentation identical between states for lines that should stay put. A state that shows only an inner fragment slides left, usually what you want.
- Line numbers in `data-lines` and `data-note` are relative to the state's first line, not to `data-numbers="12"`.
- The plugin owns the block's content: do not put your own children inside it, only `data-code-step` states. Notes, claims and companions are its siblings.
- Layout sizing needs a real title height: two lines at most, and the block's siblings after it in the same column count against the free height.
- Every step of a slide must fit the video timeline's hold (3 s by default; terminal steps are capped at 2.8 s, cursor steps at 2 s). A longer step is not at rest when the next transition starts.
- A dark block on a light deck changes how Chrome rasterises text while a transition layer is up (light-on-dark text is a little heavier in the page than in the layer); a large one (over a third of the slide) can exceed the tolerance of `npm run test:browser`. Use it once, small, or stay with the deck's palette.
- `data-lint-skip` on a block silences its tiny-text check too; do not use it.
- Different machines have different monospace fonts; wrap points differ unless the webfont is loaded (it is, with `display=block`).
- Do not animate the block with `data-anim="type"` or `count`; use `data-code-cursor` (or a terminal).
