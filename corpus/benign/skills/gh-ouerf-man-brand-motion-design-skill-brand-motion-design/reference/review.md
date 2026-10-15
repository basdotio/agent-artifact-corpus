# Review loop: look at frames, fix, repeat

Stills are cheap; renders are not. Review in this order, every round.

## 1. Stills at the moments that matter

```bash
node <skill>/scripts/stills.mjs videos/<film> b3.1 b5.2 b6.1+0.5 12.4 --out review/v3
node <skill>/scripts/stills.mjs videos/<film> --scenes --out review/v3-scenes
node <skill>/scripts/stills.mjs videos/<film> --handoffs --out review/v3-handoffs
node <skill>/scripts/stills.mjs videos/<film> b5.4 b6.1 --debug --out review/v3-debug
```

- Times are on the grid (`b<bar>.<beat>[+fraction of a beat]`) or plain seconds. `--scenes` takes each scene's middle, `--handoffs` 8 frames 0.1 s apart around each scene change.
- `--debug` renders a copy with `PF_DEBUG` on: time, bar.beat, every `[data-target]` box and the safe zone are printed in the frame.
- The script writes a contact sheet. For small text, look at full resolution or crop the region.
- Stills do not forward console output. If a still looks wrong, print the numbers into the frame (debug) before guessing.

## 2. The HyperFrames gate

```bash
cd videos/<film> && npx hyperframes check
```

Lint, runtime errors, layout (text overlapping text, overflow), and WCAG contrast of every text sample. Read the `info` lines too: a `content_overlap` during a move means text is crossing text. It measures element boxes, not pixels, so hide a scene once its content has faded.

## 3. A draft of the whole film

```bash
node <skill>/scripts/render.mjs videos/<film> --draft
F=videos/<film>/out/<name>/draft/<name>.mp4
ffmpeg -v error -y -i $F -vf "select='not(mod(n\,15))',scale=180:320,tile=10x5:padding=4:color=0x333333" -frames:v 1 -fps_mode vfr contact.png
```

30 fps, no blur, about one minute for 25 s. The contact sheet shows pacing at a glance (one tile every 0.5 s): long runs of identical tiles are dead bars. Watch the draft once with sound.

## 4. The checklist

- **Background:** one color. No invented shades. Surfaces only where the product has them.
- **Borders:** only where the product draws them. None around floating elements.
- **Text:**
  - above everything, readable on a phone, inside the safe zone
  - never covered by a cursor, chip or texture
  - never crossing other text in a move
  - never re-centering while it builds
  - formulas in the math font, correct
- **Words:** fewer. Anything that restates the picture goes. Brand names bring their logos.
- **The one highlight:** once per scene if the brand says so, landing with the brand's curve.
- **Leaks:** nothing from one scene visible in another (a stray dot or label means a `visibility: visible`).
- **Pacing:** something happens on every beat; nothing too fast to read (a caption holds 4 beats or more).
- **Handoffs:** each traveler lands exactly on its destination (debug-measured).
- **Loop:** the last frame equals frame 0 (`verify.py --loop`).
- **Claims:** only what the product does. Human approval where the product requires it.

## 5. Show the product owner

Send stills or the draft as soon as a round is coherent. Their notes come fast and precise ("no blur", "same background", "slow here"). Fold every note into `BRAND.md` or the film prompt, so the next film starts from it.
