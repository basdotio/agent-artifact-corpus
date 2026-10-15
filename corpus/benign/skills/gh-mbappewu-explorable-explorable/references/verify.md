# Verify

A page that looks right in your head is not done. Check it the way a reader will use it.

## 1. Static check

```bash
node <skill-dir>/scripts/check.mjs path/to/page.html
```

It fails on: script syntax errors, external requests other than Google Fonts, color tokens missing from the dark scheme, missing `<title>`/viewport, figures without a caption, and figure ids referenced in JS that don't exist. Fix everything it reports.

## 2. Open it in a real browser

Serve the file over http (`python3 -m http.server`), then either run `python3 <skill-dir>/scripts/shoot.py http://localhost:8000/page.html shots/` (add `--dark`, `--width 375`, `--lang zh`) and look at every PNG it writes, or use whatever browser tool you have (a built-in browser pane, Playwright, Chrome automation).

For **every figure**:
1. Scroll it into view and take a screenshot. (If a screenshot comes back blank, take it again: some tools capture before the first paint.)
2. Check the console for errors.
3. Drive it to its interesting state: move each slider to both ends and to the key value the caption mentions; click every button; drag every draggable thing. Screenshot the key state.
4. Confirm the readout text matches what the figure shows.
5. For challenges (games, puzzles), **play it to the end programmatically**: dispatch pointer events or set inputs in a loop until the success message appears. Also trigger the failure path (overshoot, divergence, jam) and the reset.

Then:
- Check light **and** dark (`prefers-color-scheme` emulation), and both languages if the page is bilingual (switch and confirm canvas labels and readouts change too).
- Check a 375×812 viewport: no horizontal scroll (`document.documentElement.scrollWidth <= innerWidth`), no clipped labels, controls wrap cleanly.

## 3. Check facts against a reference, not against yourself

The model on the page can be internally consistent and still wrong about the world. Before you finish:

- **Pick at least one number the page shows that a published table or standard also gives**, and compare. A refrigerant's saturation temperature at a pressure, a gear ratio from real tooth counts, a standard's codeword count. If they differ by more than a few percent, fix the model or say on the page how far off it is and why.
- **When you draw a standardized object** (a QR code, a DNA base pair, a circuit symbol, a road sign), place its parts where the standard puts them, or label the figure "not to the standard's layout" in the caption itself.
- **Words match the model.** Don't call an approximation "exact" or a stylized figure "real". Say "approximate", "simplified", "illustrative", right where the claim is made, not only in the footer.

## 4. Common bugs (look for these specifically)

- Labels overlapping each other or the drawing, especially when the state changes (a label that follows a moving part).
- Text or ticks cut off at the canvas edge (negative signs, the last axis label).
- Prose that names a color that isn't true in dark mode ("the black curve").
- A figure that animates once on load and is already finished when the reader scrolls to it. Start processes when the figure becomes visible, or slow them down.
- Thresholds that fast input can skip: a fast drag jumps many pixels per event. Detect *crossing* a threshold, not landing inside a narrow window.
- Pointer handlers that keep acting after the state changed mid-drag (e.g. an item was completed); guard against a stale "active" index.
- Physically wrong resting states: things floating where gravity or a spring would push them.
- Readout and drawing disagreeing because they compute the same thing twice. Compute once in the model and use it for both.
- Audio that starts without a click, or keeps playing after Stop.
- A default state that is degenerate: all speeds equal, everything at zero, a figure that looks empty until clicked. Pick defaults that show the phenomenon.
- Labels drawn over parts of the same color. Put a soft plate behind labels that sit on top of drawings.
- A callback parameter named `t` that shadows the `t(en, zh)` translation helper.

## 5. Report

Say what you verified and how, in one or two lines (e.g. "Checked all 6 figures in light/dark and at 375px; played the lock-picking figure to Open 5 times programmatically"). If something could not be verified (no browser available), say that plainly instead of claiming it works.
