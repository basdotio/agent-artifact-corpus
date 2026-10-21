# Presenting

## Running the deck

Open the HTML file in Chrome, Edge or Firefox. It scales to any screen and letterboxes to 16:9.

| Key | |
|---|---|
| → ↓ Space PgDn Enter, click | next step |
| ← ↑ PgUp Backspace | previous (lands on the finished state, no replay) |
| Home / End | first / last slide |
| digits, Enter | go to that slide |
| O | overview grid; arrows and Enter to jump |
| P | presenter view in a new window |
| F | fullscreen |
| B or . | black screen, press again to return |
| ? | key help (`H` is the highlighter now; `H` opens the help only when annotation is off) |
| D / H / L | pen / highlighter / laser pointer (below) |
| E | erase the marks of the current slide |
| 1–4 | pen colour while a drawing mode is on (otherwise digits go to a slide number) |
| Esc | leaves a drawing mode; otherwise closes help or black screen; otherwise opens the overview |

**With the mouse**, move it and the control bar appears at the bottom: back and next buttons, the slide number and title, dots for the steps of the slide (filled up to the current one), a scrubber with one segment per slide (hover shows the title, click jumps), and buttons for the overview, presenter view, fullscreen and help. It hides after a few seconds of stillness, so it never sits on the projected slide. Clicking the slide itself goes forward; clicking its left fifth goes back, and an arrow at the edge shows which way a click will go.

**On touch screens**, swipe or tap the sides.

The first seconds show a hint with the main keys. Typing a number shows "Go to slide 12 · Enter". Reaching the last step shows "End of the deck".

Presentation clickers send PgUp/PgDn or arrows, so they work as they are. Links, buttons and anything with `data-no-advance` do not advance on click, so a slide can hold an interactive demo. For a kiosk or an embedded deck, `data-controls="off"` on `.deck` removes the on-screen controls; keys still work.

## Presenter view

**P** (or the button in the control bar) opens a second window. Move it to your laptop screen and put the deck window fullscreen on the projector. Either window drives both.

| Where | What |
|---|---|
| left, top | the current state of the slide (live, with animations; your marks appear on it) |
| left, bottom | the next state as a rest frame: the next click of this slide, or the next slide. The label says which |
| right, big pane | the notes of this slide, split by click. The part you are speaking is lit and scrolled into view, what you have said is dimmed, what is ahead stays readable |
| right, small pane | the notes of the next slide, under its title, so you can plan the hand-over |
| header | timer (click to reset), position and title, dots for the clicks of the slide, `A−` `A+` for the size of the notes (remembered), back and next, the clock. It wraps on a narrow window instead of clipping |

Under 900 px the panes stack and scroll. Labels follow `<html lang>` (English and Russian).

**Notes by click.** Notes come from `<aside class="notes">` inside each slide and can hold HTML: paragraphs, a bold number, a list of beats. To tie a passage to a click, start it with one of:

```html
<aside class="notes">
  <p>Said when the slide appears: the setup.</p>
  <p data-step="1">Said on the first click.</p>      <!-- explicit: works for any number -->
  <p>Still the first click: blocks belong to the marker above them.</p>
  <p class="click">Said on the second click.</p>       <!-- the click after the previous marker -->
  <p><b>▸ click.</b> Said on the third click.</p>      <!-- a block that starts with ▸ is a marker too -->
</aside>
```

Blocks before the first marker belong to the slide itself (click 0). Markers beyond the number of clicks the slide really has merge into the last one, and a slide without markers shows one lit block. The PPTX export puts the whole text into the slide notes as before.

## Drawing on the slides

For the moment in a talk where you want to circle a number, underline a word or just point.

| Key | Mode |
|---|---|
| **D** | pen. Press again (or **Esc**) to stop |
| **H** | highlighter: a wide translucent stroke |
| **L** | laser pointer: a soft red dot that follows the pointer and fades 1.5 s after it stops |
| **1**–**4** | colour of the pen or highlighter. Each one reads a CSS variable, see below |
| **E** | erases the marks of the current slide (all its steps), with or without a mode on |
| **Esc** | leaves the mode |

A drawing mode catches the pointer, so **clicks and swipes do not advance the slide** while it is on (arrows, PgDn and the clicker still do). Marks belong to the slide and step they were drawn on, stay when you go away and come back during the session, and are gone after a reload. They sit on a canvas above the slide and below the control bar and the black screen. On a tablet, or without a keyboard, use the pen button in the control bar: it opens a palette with the three tools, the four colours, erase and done.

**Presenter view.** What you draw in the audience window appears in the presenter's preview of the current slide, live (a presenter view opened later gets everything drawn so far). The other way, only the laser is supported: press **L** in the presenter window and move the pointer over the current-slide preview; the dot shows in the audience window (and in the preview). Pen and highlighter work in the audience window only.

**Never in exports.** The layer is created on first use and only in the live and presenter windows: `?render`, the PDF, PPTX, PNG, GIF and MP4 exports, the "next" preview and the print layout cannot contain a mark. Nothing exists (no element, listener or timer) until you press a key, and a slide that is idle stays idle (`?perf` still says "idle" after you draw).

Theme it from the deck's own CSS:

```css
.deck { --dk-pen-1: #e5322d; --dk-pen-2: #16161a; --dk-pen-3: #ffd23f; --dk-pen-4: #fff; --dk-laser: #ff2b2b; }
```

Without them: colour 1 is `--accent`, 2 is `--ink`, 3 is yellow, 4 is white (so there is always a colour that reads on a dark and on a light slide). The pen starts on colour 1, the highlighter on colour 3.

Turn it off for a kiosk or an embedded deck with `<div class="deck" data-annotate="off">`: no keys, no bar button, no layer, and **H** opens the help again. Annotation ignores pen pressure and works with touch and stylus (pointer events).

## Before the talk

- Run it on the presentation machine and screen. Check that fonts loaded (the deck waits for them; if it is offline, bundle first).
- For offline or locked-down laptops: `node export/deck.mjs bundle deck.html deck.offline.html` inlines Google Fonts and CDN scripts into one file.
- Export a PDF as a backup and for people who ask for "the slides" (`node export/deck.mjs pdf deck.html`).
- Rehearse with presenter view and the timer. If a slide takes more than two minutes, split it.
- Open the deck once with `?perf` on the presentation laptop with presenter view open: every still slide should say "idle", and transitions should hold 60 fps (13-performance.md).
- Turn off notifications, set the display to never sleep, and close other windows that might steal focus.

## In the room

- Projectors lower contrast and saturation. Thin grey lines and light-grey text may vanish; the `muted` and `rule` colours need to survive that.
- Big rooms: the back row sees your 24 px as 12 px on a laptop. When in doubt, go bigger and say less.
- Use **L** to point and **D** to circle, instead of waving at the screen; **E** wipes the slide before you move on if you want it clean when you come back.
- Use **B** during a discussion so the room looks at people, not at the slide.
- Jump with digits + Enter during Q&A instead of clicking through; keep an appendix after the close for expected questions.

## Sharing

| They need | Send |
|---|---|
| to present it themselves, or see the motion | the HTML (bundled for offline) |
| to read it or print it | PDF, one page per slide (`--steps` for one page per build step) |
| to put it into their own deck | PPTX: static slides with your notes |
| a clip for social media or a README | GIF or MP4 of the timeline (12-export-qa.md) |
