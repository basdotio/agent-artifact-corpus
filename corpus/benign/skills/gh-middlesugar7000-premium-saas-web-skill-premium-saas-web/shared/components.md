# Components: nav, badges, cards, marquees, pricing, footer

## Glass floating nav

*Why:* A detached, centered pill that floats over content feels like an app, not a website. Glass only works when something colorful passes under it, so keep the hero glow behind it.

```css
.nav{position:fixed;top:20px;left:50%;translate:-50% 0;z-index:50;width:min(1200px,calc(100% - 32px));
  display:flex;align-items:center;justify-content:space-between;padding:10px 12px 10px 20px;border-radius:16px;
  background:rgb(255 255 255/.05);backdrop-filter:blur(25px);-webkit-backdrop-filter:blur(25px);
  border:1px solid rgb(255 255 255/.08)}
.nav.light{background:rgb(255 255 255/.5);backdrop-filter:blur(44px);border-radius:999px;border:0}
.nav a{font-size:14px;color:rgb(255 255 255/.7);transition:color .2s}.nav a:hover{color:#fff}
.nav.scrolled{background:rgb(13 16 23/.7)}  /* toggle with a scroll listener after ~40px */
```
Active link in light nav: accent color + a 1px underline offset 6px.

## Eyebrow badges & avatar stack

```html
<div class="proof"><div class="avatars"><img …><img …><img …><img …></div><p>Rated {rating} by<br>{count} users</p></div>  <!-- only with a real rating from the user -->
<span class="pill-eyebrow"><svg class="spark">…</svg> AI-Driven Agency</span>
```
The avatar-stack rating is only for numbers the user gave you. Without them, use the pill (a category, a release line like "v1.4 is out", "Made by one person in Lisbon") instead of inventing a rating.
```css
.avatars{display:flex}.avatars img{width:36px;height:36px;border-radius:50%;box-shadow:0 0 0 1.5px var(--bg-0);margin-left:-10px}.avatars img:first-child{margin-left:0}
.proof{display:inline-flex;align-items:center;gap:10px;font-size:13px;line-height:1.3;text-align:left}
.pill-eyebrow{display:inline-flex;gap:6px;align-items:center;padding:6px 12px;border-radius:8px;font-size:13px;color:var(--accent);
  background:#fff;box-shadow:inset 0 -2px 0 #ececec,0 1px 2px rgb(0 0 0/.08)}
.pill-eyebrow.dark{background:rgb(255 255 255/.05);border:1px solid var(--line);color:rgb(255 255 255/.8);backdrop-filter:blur(10px)}
```

## Cursor spotlight on cards (dark themes)

A cheap way to add life:
```css
.spot{--x:50%;--y:50%;background:radial-gradient(400px circle at var(--x) var(--y),rgb(255 255 255/.06),transparent 40%),var(--bg-2)}
```
```js
document.querySelectorAll('.spot').forEach(c=>c.addEventListener('pointermove',e=>{const r=c.getBoundingClientRect();c.style.setProperty('--x',e.clientX-r.left+'px');c.style.setProperty('--y',e.clientY-r.top+'px')}));
```

## Marquees with masked edges

```css
.marquee{overflow:hidden;mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent)}
.marquee-track{display:flex;gap:64px;width:max-content;animation:marquee 40s linear infinite}
.marquee:hover .marquee-track{animation-play-state:paused}
@keyframes marquee{to{transform:translateX(-50%)}}   /* duplicate the items once inside the track */
```
Logo strips use real brand logos, desaturated until hover (`shared/logos.md`).
Vertical testimonial columns: same idea with `flex-direction:column` and `translateY(-50%)`, two or three columns at different speeds (30s/40s/35s), the middle one reversed.

## Pricing highlight

```css
.price-card{border-radius:24px;padding:32px;background:var(--bg-2);border:1px solid var(--line)}
.price-card.featured{position:relative;background:linear-gradient(var(--bg-2),var(--bg-2)) padding-box,
  linear-gradient(160deg,var(--accent),transparent 60%) border-box;border:1px solid transparent;
  box-shadow:0 30px 80px -20px color-mix(in oklab,var(--accent) 45%,transparent);translate:0 -12px}
.price{font-size:56px;letter-spacing:-.04em}.price small{font-size:16px;color:rgb(255 255 255/.5)}
```
Use NumberFlow or a GSAP tween for the monthly/yearly switch so digits roll instead of snapping.

## Footer wordmark

A huge brand name spanning the full width at the very bottom (`font-size:20vw; line-height:.8; letter-spacing:-.06em`), partially cropped by `overflow:hidden`, filled with a vertical fade (`linear-gradient(#fff 0%, transparent 90%)` clipped to text, or `--line` color on light themes). It ends the page with a signature instead of a list of links.

Variant (Pastily): a **solid** off-white wordmark (`color:var(--page)`, ~400px at 1440 wide, weight 500, `letter-spacing:-.035em`) laid over a full-bleed photo so the photo shows through the gaps around the letters, with the link columns above it on a light fade into the photo. Cropping the bottom of the letters is intended.

## Section-aware pill nav

*Why:* A nav that tells you where you are feels like an app. On scroll the full pill shrinks into a small pill showing the current section name plus one primary action; it re-expands on hover or when scrolling up. Few templates do it, and it is cheap.

```html
<header class="di" data-state="full">
  <nav class="di-full"><a class="logo">Brand</a><a href="#overview">Overview</a>…<a class="btn-light">Download</a></nav>
  <button class="di-mini" aria-label="Open menu"><img class="di-icon" src="icon.svg" alt=""><span class="di-label">Features</span><a class="di-cta" aria-label="Download">↓</a></button>
</header>
```
```css
.di{position:fixed;top:10px;left:50%;translate:-50% 0;z-index:60;transition:translate .64s cubic-bezier(.22,1,.36,1),opacity .4s}
.di nav,.di-mini{display:flex;align-items:center;gap:20px;padding:6px;border-radius:999px;background:#0A0A0A;color:#fff;
  box-shadow:0 14px 34px -14px rgb(0 0 0/.55)}
.di-mini{display:none;gap:10px;padding:6px 6px 6px 12px;font-size:12px;font-weight:600}
.di[data-state=mini] nav{display:none}.di[data-state=mini] .di-mini{display:flex}
.di-cta{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--accent-soft,var(--accent));color:#0A0A0A}
.di-label{min-width:56px;text-align:left;transition:opacity .2s}
```
```js
const di=document.querySelector('.di'), label=di.querySelector('.di-label');
const io=new IntersectionObserver(entries=>{
  entries.forEach(e=>{ if(!e.isIntersecting) return;
    label.style.opacity=0;
    setTimeout(()=>{label.textContent=e.target.dataset.nav;label.style.opacity=1},120); });
},{rootMargin:'-45% 0px -50% 0px'});            // fires when a section crosses the viewport middle
document.querySelectorAll('section[data-nav]').forEach(s=>io.observe(s));   // data-nav="Features"
addEventListener('scroll',()=>{di.dataset.state=scrollY>120?'mini':'full'},{passive:true});
di.addEventListener('pointerenter',()=>{di.dataset.state='full'});
di.addEventListener('pointerleave',()=>{if(scrollY>120)di.dataset.state='mini'});
```
Note the label `opacity` needs `transition:opacity .2s` (set above). Keep `data-nav` names to one or two words. On mobile the mini state is the default and the full menu opens as a sheet.

## Handwritten annotation + hand-drawn arrow

*Why:* One human-made mark next to a polished UI tells the visitor a person built this. It also points at the thing you want clicked.

```html
<p class="note" style="--r:-4deg">hey, click me!<svg viewBox="0 0 60 30" aria-hidden="true"><path d="M2 20C16 4 38 2 56 14M48 8l8 6-9 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></p>
```
```css
.note{font:600 20px/1 "Caveat",cursive;color:var(--ink-3);rotate:var(--r);display:inline-flex;align-items:flex-end;gap:6px}
.note svg{width:54px;height:28px}
```
Rules: Caveat only for 2–4 word labels; max two notes per viewport; the arrow must actually end on the thing it points at; draw the stroke in on enter with `stroke-dasharray`/`stroke-dashoffset` if you want motion; hide on `max-width:768px` or move below the target.

## Soft-lift white cards (light directions)

*Why:* On a warm off-white page, borders look dated and heavy shadows look 2015. A two-layer shadow (1px contact + large, negative-spread ambient) lifts the card without a visible edge.

```css
.card-soft{background:#fff;border-radius:28px;padding:26px 26px 20px;box-shadow:0 1px 2px rgb(0 0 0/.03),0 8px 28px -12px rgb(0 0 0/.08)}
.card-soft:hover{box-shadow:0 1px 2px rgb(0 0 0/.04),0 18px 40px -14px rgb(0 0 0/.14);translate:0 -3px;transition:.3s cubic-bezier(.2,.8,.2,1)}
```
Card text: heading in all-caps 14–15px / 800 / `-0.01em`, body 11–12px `--ink-3`. Let the mini UI take most of the cell.

## Photo-backed pricing (one plan, one price)

*Why:* A calm landscape behind a single white card turns a purchase decision into a pause. It works for one-time-purchase or single-plan products, not for 3-tier SaaS tables.

```html
<section class="price-photo">
  <video autoplay muted loop playsinline poster="bg.jpg"><source src="bg.mp4"></video>  <!-- or a CSS background-image -->
  <canvas class="particles" aria-hidden="true"></canvas>
  <div class="price-card-solo">…</div>
  <a class="btn-cta-grad">Get Pastily — $8.99 →</a>
</section>
```
```css
.price-photo{position:relative;padding:160px 16px;color:#fff;isolation:isolate}
.price-photo video,.price-photo::before{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-2}
.price-photo::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(rgb(0 0 0/.35),transparent 30%,transparent 70%,var(--page))}
.price-card-solo{max-width:440px;margin:40px auto 16px;padding:28px;border-radius:28px;background:#fff;color:var(--ink)}
```
Inside the card: tiny label + "Launch price" chip, big price (`$` small, `8` huge, `.99` superscript), "one-time · per device", a **launch-slots bar** ("26 of 30 left" with filled segments in `--gold-2`), a quantity stepper, 6–7 check-listed benefits (round dark-green check icons), and the platform links. Below it the gradient CTA and one trust line ("Secure checkout · Licence key by email · One payment, no renewals"). Particles: 20–30 tiny leaf/snow/dust sprites drifting down with `translate` + `rotate`, 8–20s, `prefers-reduced-motion` off. Needs a real photo or video; if you cannot source one, skip this recipe and use the **plain single-price card** below (not the 3-tier Pricing highlight, which is for SaaS tables).

Conversion detail worth copying: real scarcity only. A launch-slots bar must reflect a real cap the owner confirms; otherwise omit it.

## Plain single-price card (no photo)

*Why:* Same calm "one product, one price" decision as the photo version, minus the photo. The card and the big gradient button carry the section on their own, so it still looks finished. Don't fake the photo with a stock image, and don't leave an empty `<video>`/`url()` behind.

```html
<section class="price-solo" id="pricing" data-nav="Pricing">
  <p class="eyebrow">Pricing</p><h2>One price. <span class="dim">Yours forever.</span></h2>
  <div class="price-card-solo">
    <div class="pc-head"><img class="pc-icon" src="…" alt=""><b>Clipnest</b><span class="chip">One-time purchase</span></div>
    <p class="pc-price"><small>$</small>9<span>once, for all your computers</span></p>
    <p class="pc-trial">Try it free for 14 days. No card needed.</p>   <!-- only if there is a trial -->
    <ul class="checks"><li>…</li><li>…</li><li>…</li><li>…</li><li>…</li></ul>
    <a class="btn-cta-grad" href="#">Get Clipnest for $9 →</a>
    <p class="pc-trust">Secure checkout · Licence key by email · One payment, no renewals</p>
  </div>
</section>
```
```css
.price-solo{padding:160px 16px;text-align:center;background:linear-gradient(var(--page),var(--cream))}
.price-solo .price-card-solo{max-width:460px;margin:48px auto 0;padding:28px;border-radius:28px;background:#fff;text-align:left;box-shadow:var(--soft-shadow)}
.pc-price{font:800 96px/.9 var(--font-display);letter-spacing:-.04em}.pc-price small{font-size:32px;vertical-align:top}
.pc-price span{display:inline-block;margin-left:10px;font:500 14px/1.3 var(--font-body);color:var(--ink-3);letter-spacing:0}
.btn-cta-grad{display:flex;justify-content:center;gap:10px;margin-top:24px;padding:20px;border-radius:24px;background:var(--cta-grad);color:#fff;font-size:19px;font-weight:700;
  box-shadow:inset 0 1px 0 rgb(255 255 255/.12),0 18px 40px -16px rgb(0 0 0/.6)}
```
Rules:
- **One card.** A free trial is a sentence inside the card (plus, if you like, a quiet text link "or download the free trial" under the button), never a second "$0" card next to it.
- **Chip:** "Launch price" only if the brief gives a launch price or a regular price it will rise to; then show the regular price struck through next to it. Otherwise use "One-time purchase". Never invent a discount or a deadline.
- 5–7 check items with round dark-green check icons, the platform links, one trust line. Side notes (a subscription comparison, a Caveat note) may sit outside the card, at most one per side.

## FAQ with tabs and sticky side

Two columns: left `position:sticky;top:96px` with the "Questions, answered." H2, one line of subcopy and a small card ("Still have questions?" + the support email and a Copy button that swaps to "Copied" for 1.5s); right: filter tabs (All / Privacy / Pricing / Features, active = white pill with soft shadow) above an accordion of rows separated by hairlines, the open row lifted onto a white 20px card, a round +/− button at the right. Animate height with `grid-template-rows:0fr→1fr`.
