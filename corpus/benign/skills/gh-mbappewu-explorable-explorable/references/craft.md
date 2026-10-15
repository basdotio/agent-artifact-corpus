# Craft

What separates a page people share from a page people skim.

## Story

- **Start from a question a normal person has asked.** "How do noise-cancelling headphones work?" beats "Active noise control". The title is that question answered: "How X Works".
- **Build to one insight.** Every good page has a moment where the reader goes "oh, *that's* why". For headphones: a fixed delay ruins high frequencies, so the electronics handle drones and the cushions handle hiss. For locks: the plug checks one pin at a time, so it can be solved one pin at a time. Find yours before writing, and put it in the second half.
- **Zero to insight in 4–7 steps.** First figure: the most basic physical picture (air moving, pins stacked). Each next figure adds exactly one idea. The last figure is the richest: often a small game or a "real world" mixture.
- **Prose explains what the figure shows, then moves on.** Before a figure: why we need it. After: what the reader should have noticed, in one or two sentences. Never make the reader read a paragraph to find out how to use a figure: that goes in the caption.

## Figure patterns

Pick the smallest pattern that makes the idea discoverable.

| Pattern | Use when | Example |
|---|---|---|
| **Scrub a parameter** | The idea is "how does the output change as X changes" | Delay slider → cancellation curve moves |
| **Toggle a component** | The idea is "what does this part contribute" | Cushions on/off, electronics on/off |
| **Direct manipulation** | The reader should feel the mechanism with their hands | Drag the key in; drag a cut deeper |
| **Run over time** | The idea is a process, feedback loop or learning | An adaptive filter converging; waves travelling |
| **Two views, one state** | The idea needs two perspectives at once | Waveform on top + frequency response below, both driven by the same sliders |
| **Challenge** | The last step, to prove understanding | "Pick the lock", "cut a key that opens this lock" |
| **Calculator** | Scale or combinatorics | Number of possible keys vs pins, depths, rules |

Rules for every figure:
- One or two controls. A third only if it is a reset or a preset.
- The interesting state is reachable within a few seconds of play, and the caption says how ("Slide the copy by half a cycle (180°) and the two cancel").
- A **readout** line turns the state into a plain-language sentence with a number: "What reaches the ear: 8% of the original (−21 dB)". It also announces states: blocked, set, open, blew up.
- Visible feedback for every input within one frame. Subtle events get emphasis: a flash, a shake, a tiny click sound.
- Anything that can break (divergence, jammed state) has a way back: a Reset button or a toggle, mentioned in the readout.
- Exaggerate what is too small to see, and say so.

## Drawing

- **Logical coordinates.** Draw in a fixed 680-unit-wide space via `surface()`; it scales to any screen. Pick `data-aspect` so nothing is cramped at 375px wide.
- **Schematic, not photographic.** Flat shapes, 1–3px lines, rounded corners. Cross-sections beat perspective when showing insides. A small inset (e.g. a face-on view of the plug turning) can show a second dimension.
- **Color = meaning.** Assign c1–c4 to concepts and never reuse a concept color for decoration. Mention the color in prose (`<span class="c1">noise</span>`). Neutral structure uses `--grid`, `--muted`, `--fg`. Results that are good/bad use `--good`/`--bad`.
- **Words in the figure are short labels**, 12px Inter, placed where they cannot collide. Use `spreadLabels()` for leader-line labels. Never write "black curve" in prose: in dark mode it's white. Say "thick curve" or use a concept color.
- **Motion is information.** Animate only what carries meaning (a wave travelling, a filter learning). Static figures redraw on input only.
- Axis ticks: few, round numbers, with units. Log scales for frequency or anything spanning decades.

## Prose

- Plain words, short sentences, second person. Explain each term the first time, with a picture if possible.
- Concrete numbers the reader can check in the figure ("with 60 µs of delay, anything above about 2.8 kHz is made worse").
- No filler openings ("In today's world…"), no hype, no emoji. End with a short section that connects to the wider world (other uses, limits, what real devices add).
- Numbers you state must come from the model on the page, a derivation, or a well-known constant. Label illustrative data as illustrative.

## Examples of the level to aim for

- `examples/noise-cancelling.html`: two views driven by one state (waveform + frequency response), a real LMS adaptive filter that can diverge, a WebAudio tone that actually cancels.
- `examples/pin-tumbler-lock.html`: direct manipulation (drag the key, drag cuts), a combinatorics calculator, and a picking game with binding order, setting and oversetting.
- `examples/planetary-gears.html`: WebGL 3D with exact tooth phasing, a lever diagram driven by the same state, and a real-world payoff (the Prius power split). Bilingual.
