# Motion core: rules for every sector

Read before choosing or changing any animation. Start with the budget below; it decides whether motion belongs at all. Sector files hold the individual records (ecommerce: [browse](ecommerce-motion-browse.md) M01-M19, [buy](ecommerce-motion-buy.md) M20-M36, [after purchase and promises](ecommerce-motion-after.md) M37-M49). Durations are **starting hypotheses to test on real devices with real content**, not measurements of other sites. When an immediate state change explains the result as well, choose no motion.

## Motion budget: enough to explain, never to perform

Too little motion makes an interface feel broken ("did my click work?"); too much makes it feel cheap and slow. Stay between the floor and the ceiling.

**Floor: every state change the user causes gets brief, one-shot feedback**, timed by the theme's motion roles:

| User action | Minimum feedback | Role |
| --- | --- | --- |
| Hover or keyboard focus on a control | colour, background, border or underline change | instant to quick |
| Press | pressed state at once (darker, or scale no smaller than 0.97) | instant |
| Open or close a menu, dropdown, popover or info panel | fade, with at most 4-8 px movement from its trigger; closing is quicker | quick |
| Expand or collapse (accordion, FAQ, details) | content reveal and chevron turn | quick to panel |
| Dialog, drawer, bottom sheet | backdrop fade, panel slide or scale from 0.98 | panel; exit shorter |
| Toast or inline status | fades in with minimal movement, stays long enough to read, fades out | quick |
| Tabs or segmented control | the selection indicator moves; content swaps without a jump | quick |
| Loaded content replacing a placeholder | crossfade, no layout shift | quick |
| Item added to or removed from a list or cart | the row appears or collapses; totals update at once | quick to panel |
| Confirmed success (saved, added) | one short confirmation: a check, a count or a label change | quick to panel, once |
| Validation error | the message appears in place | quick; never shake |

If the project's component library already animates these (for example data-state transitions in Radix or shadcn/ui, or Bootstrap's collapse), use that instead of adding a second system.

**Ceiling: nothing moves on its own**, with two exceptions:

- **Real progress or live data:** a loading or upload indicator, or a genuine countdown.
  - For quick actions, show a spinner only after about 300 ms. Once shown, keep it about 500 ms, so it does not flash.
  - Stop it when the work ends.
- **At most one attention moment per view:** one hero entrance on a marketing page, or one owner-chosen in-view story (such as a small group of trust cards). It plays once.

**Never:**

- decorative loops;
- scroll-triggered entrances on ordinary sections or on every card;
- staggers across more than about five items, or longer than about 300 ms in total;
- parallax, scroll-jacking, cursor followers, typing effects, animated gradient backgrounds, auto-rotating carousels;
- bounce or elastic easing in business UI;
- interface transitions longer than about 400 ms (the one story excepted);
- motion that delays reading a price, an error or an action.

**Ten-second test.**

1. Load the page and do not touch it for ten seconds. Only real progress, live data or the single attention moment may move.
2. Then walk the main task. Every click, tap and key press shows a visible response within about 100 ms.

## Runtime contract

Interaction feedback typically 100–180 ms, state changes 160–260 ms, panels 200–360 ms, optional illustrative stories 380–650 ms. Use one cohesive ease-out family for entry (for example a curve near `cubic-bezier(0.22,1,0.36,1)`), a quicker controlled exit, and almost no overshoot; tune on devices. Use transforms/opacity when useful; animate layout dimensions only for small bounded panels and profile real effects. DOM state, screen-reader text, focus and business actions update at the semantic event, never at an animation end callback. Under `prefers-reduced-motion`, show the final state directly without withholding meaning. On touch, **one-shot in-view decorative stories** can start when a compact card is about 85–95% visible; if taller than the viewport, use a visible meaningful section instead. Visibility must never gate the card's text, price or CTA. Stagger at most about 60–120 ms within an initial compact group; cap concurrent stories. On desktop hover/focus, play a narrative once per entry; sustained hover uses a still or barely shifting surface, never a full looping story. Focus triggers apply to interactive elements (links, buttons): mirror hover with `:focus-visible` there, and never add a tab stop to non-interactive content just to show an effect. Decoration on non-interactive content needs no keyboard trigger; information it reveals must be visible without hover. Fast repeated input interrupts and retargets from the current visual state. Pause/remove work on hidden or unmounted content. Check zoom, keyboard, touch, low-power devices, slow network, long locale, and reduced motion for every chosen record.

## Rules that keep motion premium instead of cheap

- **One-shot beats loops.** At most one looping animation may be visible at a time, and only when it carries live meaning (real progress, a genuinely expiring offer). A decorative loop on a badge, status dot or logo spends the user's attention for nothing.
- **Trust marks stay still.** Payment, provider and security logos are static, in one row; a hover may restore full colour. A scrolling logo marquee reads as an advert and is skipped.
- **Composite-friendly properties.** Animate `transform` and `opacity`. Avoid animating `box-shadow`, `text-shadow`, `filter: blur()` on large areas, `width`/`height`/`top` except small bounded panels; they repaint every frame and drain phones.
- **`will-change` is temporary.** Add it just before an animation that needs it and remove it when the animation ends; left on, it keeps a GPU layer alive.
- **No novelty presets.** Bounce, shake, wobble, jello, rubber-band and tada effects, mascots on purchase buttons, auto-rotating banners, parallax and scroll-jacking lower trust. Content that moves on its own for more than five seconds beside other content needs a visible pause control (WCAG 2.2.2), and it pauses while the pointer or keyboard focus is inside it.
- **One motion grammar.** Durations and easing come from the theme's motion roles (instant, quick, panel, story); the same job moves the same way on every page.
- **Truth first.** Success motion follows confirmed success only; motion never stands in for data that has not arrived, and no counter animates from zero to a real business figure for show.

## Record and release check

Write each chosen motion with `assets/templates/motion-record.md`. The record covers `owner page/component; reason; verified data prerequisite; exact trigger; initial/final state; duration/easing/delay; interrupt behavior; keyboard/touch; reduced-motion final state; screen-reader response; responsive/tall-content case; low-power result; test outcome`. A missing field keeps the entry provisional. For motion without proven benefit, mark **none** and keep the useful static UI. Numeric timing cannot compensate for unclear navigation, inaccurate product facts or inconsistent assets.
