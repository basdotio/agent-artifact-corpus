# Light, backgrounds and structure lines

## Sculpted glow (hero light source)

*Why:* A single radial gradient looks like a gradient. Real light has shape. OptimAI stacks pure-hue blobs and then lays **bg-colored blobs on top** (also blurred) to carve the glow into a crescent or arch. That's why it feels like an eclipse, not a wallpaper. Main use: dark heroes and final CTAs.

```html
<section class="hero">
  <div class="glow" aria-hidden="true">
    <span class="g g1"></span><span class="g g2"></span>   <!-- light -->
    <span class="g e1"></span><span class="g e2"></span>   <!-- erasers -->
    <span class="g core"></span>                            <!-- hot core -->
  </div>
  ...content (position:relative; z-index:2)...
</section>
```
```css
.hero{position:relative;overflow:hidden;background:var(--bg-0);isolation:isolate}
.glow{position:absolute;inset:0;z-index:0;pointer-events:none}
.g{position:absolute;display:block}
.g1{top:-17%;left:50%;width:812px;height:488px;translate:-80% 0;background:var(--glow);filter:blur(100px)}
.g2{top:-5%;right:-4%;width:212px;height:288px;background:var(--glow);filter:blur(120px)}
.e1{top:-22%;left:50%;width:672px;height:488px;translate:-80% 0;border-radius:200px;background:var(--bg-0);filter:blur(100px);z-index:1}
.e2{bottom:-20%;left:50%;width:min(1812px,140vw);height:1040px;translate:-50% 0;border-radius:200px;background:var(--bg-0);filter:blur(142px);z-index:1}
.core{bottom:10%;left:50%;width:150px;height:180px;translate:-50% 0;border-radius:999px;background:linear-gradient(var(--accent-deep),var(--accent));filter:blur(78px);z-index:2}
@media (max-width:768px){.g{filter:blur(60px)!important;scale:.6}}
```
Tune by moving the erasers. Rule of thumb: light blobs at 100% saturation, erasers same size or bigger, blur 80–140px. Add a slow drift (`animation: drift 18s ease-in-out infinite alternate` on `.g1`, translating ±40px) for life.

A lighter variant for sections: one blob of accent at 25% opacity behind a heading, `filter:blur(120px)`.

## Hairline grid & column guides

*Why:* Visible structure lines (Adon, OptimAI's faint verticals) make a page feel engineered. They cost nothing and instantly elevate a plain layout.

```css
.frame{border-inline:1px solid var(--line);max-width:1440px;margin-inline:auto}
.cells{display:grid;grid-template-columns:1fr 1fr}
.cells>*{border-bottom:1px solid var(--line);padding:32px}
.cells>*+*{border-left:1px solid var(--line)}
/* faint column guides on a dark hero */
.guides{position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(90deg,transparent 0 calc(25% - 1px),rgb(255 255 255/.04) calc(25% - 1px) 25%);
  mask-image:linear-gradient(to bottom,#000 30%,transparent)}
```

## Backgrounds

```css
.dots{background-image:radial-gradient(rgb(255 255 255/.12) 1px,transparent 1px);background-size:24px 24px;
  mask-image:radial-gradient(ellipse at center,#000 30%,transparent 75%)}
.grid-bg{background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);background-size:64px 64px;
  mask-image:radial-gradient(ellipse 60% 50% at 50% 0%,#000,transparent)}
.noise::after{content:"";position:absolute;inset:0;pointer-events:none;opacity:.06;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
```
Noise on top of glows removes gradient banding and adds a film-like richness. Use it on dark heroes.
Dot-matrix globe: a `<canvas>` drawing points on a sphere (lat/long loop, project with simple orthographic math, rotate slowly), or a pre-made SVG. Put it at the bottom of a dark card, half cropped.
