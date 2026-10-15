# Product proof: mockups and bento mini-UIs

## Browser-frame mockup fading into the page

*Why:* Every top SaaS template puts the actual product in the hero. Buyers trust what they can see. Build it in HTML so it's crisp and can be animated.

```html
<div class="mock-wrap">
  <div class="mock">
    <div class="mock-bar"><i></i><i></i><i></i><span class="mock-url">app.yourproduct.com</span></div>
    <div class="mock-body">…sidebar + chat/dashboard built in HTML…</div>
  </div>
  <div class="mock-fade"></div>
</div>
```
```css
.mock-wrap{position:relative;max-width:1288px;margin:64px auto 0}
.mock{border-radius:14px;overflow:hidden;background:#0B0E14;border:1px solid rgb(90 159 255/.5);
  box-shadow:0 0 0 1px rgb(90 159 255/.15),0 0 40px rgb(47 107 255/.45),0 0 120px rgb(47 107 255/.25)}
.mock-bar{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line)}
.mock-bar i{width:11px;height:11px;border-radius:50%;background:#FF5F57}.mock-bar i:nth-child(2){background:#FEBC2E}.mock-bar i:nth-child(3){background:#28C840}
.mock-url{margin-inline:auto;padding:4px 80px;border-radius:6px;background:var(--bg-2);font-size:12px;color:rgb(255 255 255/.5)}
.mock-fade{position:absolute;inset:auto 0 -2% 0;height:min(465px,45%);background:linear-gradient(180deg,transparent,var(--bg-0) 94%);pointer-events:none}
```
Animate it in with a slight 3D tilt: `gsap.from('.mock',{rotateX:18,y:80,opacity:0,duration:1.4,ease:'power3.out',transformPerspective:1200})`. On light directions, swap the neon edge glow for a soft layered shadow and a 1px `--line` border.

## Desktop-app hero: device bleeding off the edge, real OS chrome

*Why:* For a menu-bar or desktop app, a centered browser frame says "web app" and hides the thing people buy. Show the actual OS: a laptop whose menubar has the app's tray icon, the open menu, and a dock with the app icon. Letting the device run off the viewport edge makes the hero feel larger than the screen.

```html
<section class="hero-split">
  <div class="hero-device"><div class="laptop">
    <div class="menubar"><i class="mb-dot"></i>…<img class="tray" src="icon.svg" alt=""></div>
    <div class="desk" style="background:url(wallpaper.jpg) center/cover">
      <div class="app-menu">…dark popover with grouped rows, colored 16px icons, shortcuts at right…</div>
      <div class="dock">…4–5 icons incl. the app…</div>
    </div></div></div>
  <div class="hero-copy">…badge, status line, app icon, H1, subcopy, CTA, price, "Also on" chips…</div>
</section>
```
```css
.hero-split{display:grid;grid-template-columns:1.25fr 1fr;align-items:center;min-height:100svh;overflow:hidden}
.hero-device{margin-left:-14vw;justify-self:start}             /* the bleed */
.laptop{width:min(860px,62vw);aspect-ratio:16/10;border:10px solid #17181A;border-radius:22px 22px 6px 6px;position:relative;
  box-shadow:0 40px 80px -30px rgb(0 0 0/.45)}
.laptop::after{content:"";position:absolute;left:-4%;right:-4%;bottom:-18px;height:14px;border-radius:0 0 18px 18px;background:linear-gradient(#2a2b2e,#111)}
.app-menu{position:absolute;right:6%;top:9%;width:min(240px,28%);padding:8px;border-radius:12px;background:rgb(24 24 27/.96);color:#fff;font-size:11px}
```
The wallpaper should be a calm soft-gradient landscape (a few overlapping hills in the brand green works) so the dark menu pops. Build the menubar and menu in HTML, not a screenshot, so it stays crisp and can animate (menu rows fade in one by one; cursor SVG glides to "Open Dashboard"). Put the handwritten notes from `shared/components.md` beside the tray icon and the app icon. Under 900px, stack: copy first, device below at full width, no negative margin.

**Showcase video card:** after the hero, a white 28px card with a short H2 and a screen recording in the same laptop frame (autoplay, muted, loop, `playsinline`, a `poster`). Add a pause button and a sound toggle at the bottom-right as 40px dark circles; users notice the controls and trust the video more. Never autoplay with sound.

**Screenshot gallery (feature tour):** a rounded dark container (`#101012`, radius 28px) holding a 3-column masonry of real UI screenshots, each in a 16px-radius tile with a one-line caption below in 11px grey ("Auto-disappear counts down in a tiny island"). Captions must say what the screenshot proves.

## Bento grid with mini-UIs and corner light leaks

*Why:* Feature icons are interchangeable; a tiny working-looking UI proves the feature exists. Unequal cell sizes create a magazine rhythm.

```css
.bento{display:grid;gap:16px;grid-template-columns:repeat(6,1fr);grid-auto-rows:minmax(220px,auto)}
.bento>.c1{grid-column:span 2;grid-row:span 2}.bento>.c2{grid-column:span 4}.bento>.c3{grid-column:span 2}.bento>.c4{grid-column:span 2}
.cell{position:relative;overflow:hidden;border-radius:20px;background:var(--bg-2);border:1px solid var(--line);padding:28px;display:flex;flex-direction:column;justify-content:flex-end}
.cell::before{content:"";position:absolute;top:-30%;right:-20%;width:60%;height:60%;border-radius:50%;
  background:radial-gradient(circle,rgb(90 159 255/.55),transparent 70%);filter:blur(40px);opacity:.7}   /* corner light leak */
.cell h3{font-size:20px;letter-spacing:-.02em}.cell p{color:rgb(255 255 255/.6);font-size:14px}
@media(max-width:900px){.bento{grid-template-columns:1fr}.bento>*{grid-column:auto!important;grid-row:auto!important}}
```
Mini-UI ideas (build each in ~10–20 lines of HTML): workflow nodes connected by a dashed SVG path with a dot traveling along it (`offset-path`, see `shared/motion.md`), chat bubbles typing, toggle switches flipping on a loop, a sparkline drawing itself (SVG `stroke-dashoffset`), color chips, a "Process → Sync → Grow" pill flow, a notification stack, a code snippet with a blinking cursor, a radial progress ring, an integrations orbit (real logos, `shared/logos.md`). Give the mini-UI its own muted panel (`background:rgb(255 255 255/.03); border:1px solid var(--line); border-radius:12px`).

Highlighted card among equals (e.g. 1 of 4 services): `background:linear-gradient(160deg,#3B5BFF,#1C2A8C)`, others stay neutral.
