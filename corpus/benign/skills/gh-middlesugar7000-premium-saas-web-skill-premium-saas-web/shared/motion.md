# Motion: GSAP + Lenis setup

All five reference sites use GSAP + ScrollTrigger + SplitText. Three of them also use a smooth-scroll layer (Lenis or ScrollSmoother). Since GSAP 3.13 every plugin, including SplitText, is free and on the public CDN.

## Principles (why motion feels premium)
- **Ease out, never linear** (except scrubbed and infinite loops). `power3.out` / `expo.out` for entrances, `power2.inOut` for state changes.
- **Short distances, longer durations.** Move 24–60px over 0.8–1.2s. Big moves look cheap.
- **Stagger is the luxury.** 0.04–0.08s between words/cards creates a cascade that reads as craft.
- **One hero moment.** The headline reveal + product mockup entrance are the most choreographed thing on the page; everything else is a quiet fade-up.
- **Respect `prefers-reduced-motion`.** Skip all of it, show final states.

### Timing & easing (use these numbers, not guesses)

| Moment | Duration | Ease |
|---|---|---|
| Hover / press / focus | 120–180ms | `cubic-bezier(.2,0,0,1)` |
| Card / tab / accordion state change | 250–400ms | `power2.inOut` or the same bezier |
| Section reveal (fade-up) | 800–1000ms | `power3.out` |
| Hero cascade, counters, dramatic reveal | 1000–1400ms | `expo.out` / `power3.out` |
| Ambient (glow drift, marquee) | 20–60s | `sine.inOut` / `none` |
| Scrubbed | tied to scroll | `none` |

- Premium personality = the slow end of every range, but UI feedback stays fast: the more often something plays (hover), the shorter and subtler it is.
- Exits run 65–75% of the entrance, `ease-in`, opacity-only is fine.
- Scale distance and time together: a 24px rise is ~0.8s, an 80px rise 1.2s+.
- Roughly a third of the elements in view animate at once; stagger totals stay under ~0.5s for UI lists (the hero cascade is the one exception).
- Never `scale(0)` (start from .92–.96). Never animate `width/height/top/left`; use transforms (the Flip plugin for real layout moves).

## Boilerplate

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/SplitText.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/lenis@1.3.4/dist/lenis.min.js"></script>
<script>
gsap.registerPlugin(ScrollTrigger, SplitText);
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

if (!reduce) {
  // Smooth scroll, synced with ScrollTrigger
  const lenis = new Lenis({ lerp: 0.1, smoothWheel: true });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add(t => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}

document.fonts.ready.then(() => { if (!reduce) initMotion(); });

function initMotion() {
  // 1. Hero headline: words rise from below a mask, slight 3D tilt
  const h = SplitText.create('.hero h1', { type: 'words,lines', mask: 'lines' });
  gsap.from(h.words, { yPercent: 110, rotateX: -40, opacity: 0, transformOrigin: '50% 100%',
    duration: 1.1, ease: 'expo.out', stagger: 0.06, delay: 0.15 });
  gsap.from('.hero [data-fade]', { y: 24, opacity: 0, duration: 0.9, ease: 'power3.out', stagger: 0.08, delay: 0.5 });
  gsap.from('.mock', { y: 80, rotateX: 18, opacity: 0, transformPerspective: 1200, duration: 1.4, ease: 'power3.out', delay: 0.7 });

  // 2. Generic reveal: any [data-reveal] container fades its children up with stagger
  gsap.utils.toArray('[data-reveal]').forEach(group => {
    gsap.from(group.children, { y: 40, opacity: 0, duration: 0.9, ease: 'power3.out', stagger: 0.08,
      scrollTrigger: { trigger: group, start: 'top 82%' } });
  });

  // 3. Section headings: line-by-line mask reveal
  gsap.utils.toArray('[data-split]').forEach(el => {
    const s = SplitText.create(el, { type: 'lines', mask: 'lines' });
    gsap.from(s.lines, { yPercent: 100, duration: 1, ease: 'expo.out', stagger: 0.1,
      scrollTrigger: { trigger: el, start: 'top 85%' } });
  });

  // 4. Scroll-fill text: ONE trigger + sequential timeline, lines fill strictly one after another.
  //    (A ScrollTrigger per line overlaps and fills several lines at once - don't.) CSS in shared/typography.md.
  gsap.utils.toArray('.fill-text').forEach(el => SplitText.create(el, {
    type: 'lines', linesClass: 'line', autoSplit: true,
    onSplit: self => {
      const tl = gsap.timeline({ defaults: { ease: 'none' },
        scrollTrigger: { trigger: el, start: 'top 80%', end: 'bottom 40%', scrub: 0.5 } });
      self.lines.forEach(l => tl.to(l, { backgroundPosition: '0% 0', duration: 1 }));
      return tl;
    }
  }));

  // 5. Counters
  gsap.utils.toArray('[data-count]').forEach(el => {
    const end = +el.dataset.count, suffix = el.dataset.suffix || '';
    const o = { v: 0 };
    gsap.to(o, { v: end, duration: 2, ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 85%' },
      onUpdate: () => el.textContent = Math.round(o.v).toLocaleString() + suffix });
  });

  // 6. Parallax for decorative layers
  gsap.utils.toArray('[data-speed]').forEach(el => {
    gsap.to(el, { yPercent: -20 * +el.dataset.speed, ease: 'none',
      scrollTrigger: { trigger: el.closest('section'), start: 'top bottom', end: 'bottom top', scrub: true } });
  });
}
</script>
```

### Reduced motion + mobile in one place: `gsap.matchMedia()`

The `reduce` flag above is decided once. `gsap.matchMedia()` re-evaluates when the user flips the OS setting or rotates the phone and reverts every tween it created. Use it for the reveal layer and keep cursor effects desktop-only:

```js
document.fonts.ready.then(() => {            // tweens must be created inside the callback, so wait for fonts first
  gsap.matchMedia().add({ motion:'(prefers-reduced-motion: no-preference)', desktop:'(min-width:769px)' }, ctx => {
    const { motion, desktop } = ctx.conditions;
    if (!motion) return;                     // final states stay visible, nothing animates
    initMotion();                            // reveals, scrub, counters
    if (desktop) initCursorEffects();        // card spotlight, cursor glow (buttons never move)
  });
});
```
Add a CSS safety net as well: `@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}`, and make marquees pausable.

## Gotchas found in testing
- **Gradient text + SplitText:** `background-clip:text` on the parent stops working once SplitText wraps words/lines in their own elements, and the headline turns invisible. Apply the gradient to the split pieces instead (`wordsClass:'w'` + `.display-metal .w{background:inherit;-webkit-background-clip:text;background-clip:text;color:transparent}`), or use a plain color for split headlines. Scroll-fill text (`shared/typography.md`) already applies its gradient per line for this reason.
- **SplitText lines + responsive:** lines are measured once. Create splits with `autoSplit:true` and build the animation in `onSplit(self){ return gsap.from(self.lines, …) }` so they re-measure on resize; otherwise headings break one word per line after a width change.
- **Dimming stacked cards:** use `filter:brightness()`, never `opacity`, or the card underneath bleeds through.
- **SplitText `mask:'lines'` clips accents.** The mask is a tight overflow box, so Á/Ő/Ű and descenders get cut on non-English copy. Use `mask:'lines'` only for text without diacritics, or add vertical padding to the mask (`linesClass` with `padding-block:.15em; margin-block:-.15em`), or reveal with opacity + `y`.
- **`containerAnimation` needs `ease:'none'`** on the parent tween (horizontal-scroll sections); any ease breaks the scroll mapping.
- **One ScrollTrigger per timeline.** A ScrollTrigger on a child tween of a timeline that already has one is ignored: use one trigger on the timeline, or standalone tweens.
- **`from()` after another tween in a timeline** jumps to its start state immediately (`immediateRender:true`). Pass `immediateRender:false`.
- Scrubbed tweens use `ease:'none'`. Call `ScrollTrigger.refresh()` after fonts/images change layout.
- In React/Next use `useGSAP()` with a scoped ref, and never `setState` inside `onUpdate`; mutate a ref or the DOM.

## Signature sequences

**Stacking cards** (Davies projects, "how it works" steps):
```css
.stack-card{position:sticky;top:96px}  /* each card; give each a slightly larger top: 96px, 112px, 128px for a peek effect */
```
```js
gsap.utils.toArray('.stack-card').forEach((card, i, all) => {
  if (i === all.length - 1) return;
  // dim with brightness, NOT opacity: a semi-transparent card lets the next card's text bleed through
  // fromTo with an explicit brightness(1): tweening from the default `filter:none`, GSAP starts at brightness(0),
  // so the card snaps to near-black the moment the trigger starts.
  gsap.fromTo(card, { scale: 1, filter: 'brightness(1)' },
    { scale: 0.95, filter: 'brightness(0.7)', ease: 'power1.in',
      scrollTrigger: { trigger: all[i + 1], start: 'top 45%', end: 'top 96px', scrub: true } });
});
```
**Always tween `filter` with `fromTo` (or set `filter:'brightness(1)'` in CSS).** From `none`, GSAP interpolates from `brightness(0)`: the card goes black instantly and then *lightens* toward the target. This is the main reason stacked cards "go dark way too early".

**Don't dim too early or too hard.** The card being covered is still the one the visitor is reading. Starting the dim at `start:'top bottom'` (the moment the next card peeks in at the bottom of the screen) with `brightness(.45)` turns it dark almost as soon as it pins, so its text becomes unreadable mid-read. Start only once the next card has covered roughly half the viewport (`top 45%`), stop at its pinned top, keep brightness ≥ .65, and use an ease-in so most of the darkening happens in the last stretch, when the card is already mostly hidden.

**Tone-shifting story stack, CSS only** (Pastily "problem → fix → payoff", also good for "how it works"): no GSAP needed. Each step is a tall `<article class="story-card">` that sticks a little lower than the previous one, so the earlier cards peek out above like a deck, and each card has its own background tone.
```css
.story{display:grid;gap:40vh;padding-bottom:20vh}            /* gap = scroll distance between steps */
.story-card{position:sticky;min-height:648px;border-radius:28px;padding:40px 48px;
  box-shadow:0 1px 2px rgb(0 0 0/.04),0 24px 60px -24px rgb(0 0 0/.18)}
.story-card:nth-child(1){top:108px;background:#fff}
.story-card:nth-child(2){top:124px;background:var(--cream,#FAF6ED)}
.story-card:nth-child(3){top:140px;background:var(--mint,#F1F5EC)}
.story-card:nth-child(4){top:156px;background:#fff}
.story-meta{display:flex;justify-content:space-between;font-size:12px}   /* "● The problem" chip left, "01 / 04" right */
```
Why it works: three things change at once (position, tone, step counter), so each step feels like a new beat without any scrubbing. The 16px increment of `top` is the peek. Combine with the colored-keyword scroll-fill from `shared/typography.md` inside each card. Do not dim the covered card with opacity (see gotcha above); the tone difference is enough.

**Pinned UI-chip wall** (one dramatic black section): a full-bleed black section whose inner wrapper is `position:sticky;top:0;height:100vh;overflow:hidden`, filled with 6–8 rows of pill/chip components (clip cards with type badges, a countdown, a shortcut keycap row `⌘ ⇧ V`, color swatch, toast "Copied to clipboard", search field, toggle, counters like "1,824 clips saved", "0.7 ms search") in dark glass tones with 1px borders and a thin tinted fill per type. Rows are offset horizontally so it reads as a dense texture. Scale the wall from ~1.15 to 0.9 and translate it slightly with scroll progress while the headline ("Everything you copy. Reimagined for Mac.") rises over it in white, then release the pin. Only worth it when the product has a large vocabulary of small UI pieces; keep it to one per page, and under `prefers-reduced-motion` show it static.

**Pinned horizontal scroll** (features or case studies):
```js
const track = document.querySelector('.h-track');
gsap.to(track, { x: () => -(track.scrollWidth - innerWidth + 64), ease: 'none',
  scrollTrigger: { trigger: '.h-pin', pin: true, scrub: 1, end: () => '+=' + track.scrollWidth, invalidateOnRefresh: true } });
```

**Traveling dot on a connector** (bento workflow): SVG path + `<circle>` with CSS `offset-path: path('…'); animation: travel 3s linear infinite;` `@keyframes travel{to{offset-distance:100%}}`.

**Self-drawing line/sparkline**: `stroke-dasharray: L; stroke-dashoffset: L;` → animate to 0 on enter.

Direction-specific motion lives with its direction: logo arc in `directions/ember-dark/`, preloader and custom cursor in `directions/noir-spotlight/` (cursor also in `editorial-mono/`).

## Hover micro-interactions
- Buttons: arrow `translateX(3px)`, glow blur tightens (14→10px), tactile buttons sink 1px on `:active`.
- Cards: `translateY(-4px)` + border alpha 0.18 → 0.32 + cursor spotlight. 300ms `cubic-bezier(.2,.8,.2,1)`.
- Links: underline grows from left (`background-size: 0 1px → 100% 1px`).
- Images in cards: `scale(1.04)` over 700ms inside an `overflow:hidden` wrapper.

## Performance
- Animate only `transform` and `opacity` (and `background-position` for the fill effect).
- Big `filter: blur()` blobs are expensive. Keep them static or drift them slowly; add `will-change: transform` only to things that actually move.
- On mobile (`max-width: 768px`): halve blur radii, disable magnetic/cursor effects, keep reveals.
- Call `ScrollTrigger.refresh()` after images load if layout shifts.

## Native CSS motion (no JS, progressive enhancement)

Good for a scroll-progress bar, simple reveals on pages without GSAP, and a fallback layer. Support is uneven (Firefox has no stable scroll-driven animations, Safari only recently), so guard it with `@supports` and make the un-animated state the correct one. Pick one system per element: never GSAP and `animation-timeline` on the same node.

```css
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .reveal   { animation: rise linear both; animation-timeline: view(); animation-range: entry 10% entry 60%; }
    .progress { transform-origin: 0 50%; animation: grow linear both; animation-timeline: scroll(root block); }
  }
}
@keyframes rise { from { opacity: 0; transform: translateY(32px); } to { opacity: 1; transform: none; } }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
```
- Use `both` as the fill mode for scroll-driven animations (`forwards` can lock the end state when scrolling back).
- `@starting-style` gives a menu/dialog an enter animation from `display:none` without JS: transition `opacity, transform, display` with `allow-discrete` and put the from-state in `@starting-style{}`.
- Same-document View Transitions (`document.startViewTransition(() => update())`) suit tab and pricing-toggle swaps. Guard with `if (!document.startViewTransition)` and just update the DOM.
- Never `transition: all`; list the properties.
