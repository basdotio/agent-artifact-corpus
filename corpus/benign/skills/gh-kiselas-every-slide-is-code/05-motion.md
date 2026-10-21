# Motion: builds, easing, timing

## What motion is for on a slide

On a slide, motion has three jobs, and only three:

1. **Sequence.** Reveal the argument in the order it is spoken: the chart, then the highlight; the problem, then the answer.
2. **Relate.** Show that two things are the same object (morph), that one is inside the other (zoom), that time passes (dip), that we continue (camera, push).
3. **Emphasise.** Point at the one thing that matters now: a highlight sweep, a dim of everything else, a spring on the key number.

If a motion does none of these, remove it. A deck is not a showreel; the audience should notice the idea, not the animation.

## Easing

```js
const { ease, spring, seg } = Deck;
ease.outExpo(p)      // arrivals: fast start, soft landing
ease.inOutCubic(p)   // moves within the slide, lines drawing, camera
ease.outBack(p)      // arrival with a small overshoot
spring(t, .42, 15)   // emphasis: overshoot and settle, closed form, deterministic
```

| Situation | Curve |
|---|---|
| Element appears | outExpo, outCubic |
| Element leaves | inCubic, inExpo |
| Moves inside the slide, a line draws | inOutCubic |
| Bars grow | outExpo, staggered |
| A number counts | outExpo, so the last digits settle slowly |
| Emphasis on the key element | spring or outBack |
| Constant process (flow along an edge, a ticker) | linear, the only place for it |

## Timing

| Action | Duration |
|---|---|
| Emphasis pulse, highlight sweep | 0.3–0.6 s |
| Element appears | 0.4–0.8 s |
| Chart builds (bars, a line) | 0.8–1.8 s |
| Number counts | 1.2–1.8 s |
| Transition between slides | 0.6–1.3 s |
| Camera flight across the world | 1.1–1.6 s |

Nothing that matters should take longer than two seconds: the speaker is waiting. Step-0 builds start when the incoming transition is half-way, so the slide finishes arriving as its content does.

## Stagger

`data-stagger=".08"` on a container animates its children in order. The order carries meaning:

- left to right, top to bottom: reading order, the default;
- `data-order="center"`: from the middle out, for a burst or a grid;
- `data-order="reverse"`: towards the reader, for a countdown;
- `data-order="random"` (seeded): organic, for scatter points or a crowd.

Spread: 40–120 ms between items; the whole group under about 0.8 s.

## Builds that work

- **One point per click, the previous one dims.** `data-step="n" data-dim="n+1"` on each item.
- **Chart first, meaning second.** Step 0: the chart draws. Step 1: the highlight, the annotation, the grey-out of the rest.
- **Replace, don't stack.** `data-out="2"` removes an element when the next one takes its place.
- **Count to the number.** `data-anim="count"` counts up to the value written in the markup.
- **Strike the old, count the new.** The demo's prep ticket: `strike` on yesterday's value, `count` with `data-from` to today's.

## Kinetic text

`chars`, `tracking`, `scramble` and `flip` (split-flap, one word per step) are builds like the others: declared with `data-anim`, deterministic, with a rest frame that is the authored text. Use them for the title slide, a tagline, a word that changes per click: at most one per section, and only where the motion says something (the letters of a system settling out of noise, a state that flips). Choice, markup and limits: 09-typography.md. A statement with a small setup and an accent payoff (`data-say`) takes `rise` with `data-stagger` and needs nothing else.

## Builds that don't

- Every bullet flying in from a different direction.
- Bounce and elastic on text.
- A build for every single word.
- Animating the title of every slide (it should already be there when the slide lands; animate the content).
- Motion in the corner while the speaker explains the centre.

## Ambient motion

A still slide is fine. A deck is not a video; the speaker is the motion. Use ambient motion only where it explains a process: dots flowing along a pipeline, a pulse on the live node, a slow line on a monitor. Drive it from `st.T` or `st.life()`, so it freezes to a canonical pose in rest frames. Motion that changes only a few times a second (line boil, film grain, a blinking cursor) does not need 60 redraws: declare `ambient: 10` on the slide spec (or on the stage) and it is redrawn at most that often, while the rest of the deck idles as usual (`Deck.fx.boil`, `Deck.fx.grain`: 10-stage.md).

## Reduced motion

`prefers-reduced-motion: reduce` turns every transition into a short fade. Builds still reveal in order, so the story stays intact. Do not rely on motion alone to carry meaning (00-agent-brief.md, rules 18–19).
