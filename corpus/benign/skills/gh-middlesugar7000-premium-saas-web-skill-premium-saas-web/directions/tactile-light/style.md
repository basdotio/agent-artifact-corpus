# Tactile Light (from Aigocy)

**Why it works:** Everything looks physically pressable: a lit top edge, a darker bottom lip and a soft multi-layer shadow mimic real objects under a softbox. A single hot red against zinc grays is confident and expensive. The hero sits in an inset rounded "frame", like a product on a plinth.

## Tokens

```css
:root{
  --page:#EDECEC;       /* body behind the framed hero */
  --surface:#F4F4F5;    /* zinc-100: sections, cards */
  --surface-2:#FAFAFA;
  --ink:#09090B;        /* zinc-950 */
  --ink-2:#3F3F46; --ink-3:#52525B; --ink-4:#A1A1AA;
  --line:#D4D4D8;       /* zinc-300 */
  --dark-card:#272727; --dark-card-2:#18181B;
  --accent:#FD3A25; --accent-grad: linear-gradient(#EA2B16,#FF3B26);
  --heading-grad: linear-gradient(132deg,#43484D 11%,#292C2E 79%);
}
```
- **Fonts:** Urbanist (display 96px/600, −0.03em, lh 1.0; body 16–18px).
- **Radii:** 99px buttons/pills, 40px big cards & framed hero, 24px cards, 16/12/8 inner.
- **Signature pieces:** framed hero with a 3D abstract render (glossy ribbon/glass) bleeding off one side; floating glass nav pill (white/50, blur 44px, `shared/components.md`); eyebrow pill with accent icon; headline with an *inline pill shape* in accent color carrying 2–3 floating app icons (gently bobbing); tactile dark primary + tactile light secondary buttons; "Scroll for more" notch tab cut into the bottom of the hero frame; dark sheen card next to light sheen card; giant pale number (e.g. "120+" in zinc-300) as decoration; dot-matrix globe; grayscale logo marquee.
- **Headline gradient:** apply `--heading-grad` with `background-clip:text` on the strong line; the second line uses a lighter variant (`#9a9a9a → #d4d4d8`) so it fades away.

## Tactile glossy buttons

*Why:* These buttons look like physical keys: a 1px inner highlight on top (light from above), a 3px darker inner lip at the bottom (thickness), and a 5-step shadow stack whose blur grows geometrically (a realistic contact shadow, not one blurry smudge).

```css
.btn-tactile-dark{
  padding:14px 26px;border-radius:99px;color:#fff;font-weight:500;
  background:
    radial-gradient(62.56% 62.56% at 28.14% -10.42%,rgb(255 255 255/.2) 0%,rgb(255 255 255/0) 100%),
    #272727;
  box-shadow:
    inset 0 -3px 0 #080808,
    inset 0 1px 0 rgb(255 255 255/.3),
    0 2.77px 2.21px rgb(0 0 0/.12),
    0 6.65px 5.32px rgb(0 0 0/.13),
    0 12.52px 10.02px rgb(0 0 0/.133),
    0 22.34px 17.87px rgb(0 0 0/.14),
    0 41.78px 33.42px rgb(0 0 0/.15);
  transition:transform .2s,box-shadow .2s;
}
.btn-tactile-dark:active{transform:translateY(1px);box-shadow:inset 0 -1px 0 #080808,inset 0 1px 0 rgb(255 255 255/.3),0 2px 3px rgb(0 0 0/.2)}
.btn-tactile-light{
  padding:14px 26px;border-radius:99px;color:#09090B;font-weight:500;
  background:radial-gradient(62.56% 62.56% at 28.14% -10.42%,rgb(255 255 255/.2),transparent),#F5F5F5;
  box-shadow:inset 0 -3px 0 #E9E9E9,inset 0 1px 0 rgb(255 255 255/.7),0 2.77px 2.21px rgb(0 0 0/.12),0 3px 3px rgb(0 0 0/.14);
}
.btn-accent{ /* hot accent version */
  background:linear-gradient(#EA2B16,#FF3B26);color:#fff;border-radius:99px;
  box-shadow:inset 0 -3px 0 rgb(0 0 0/.18),inset 0 1px 0 rgb(255 255 255/.35),0 8px 20px -6px rgb(253 58 37/.55);
}
```

## Sheen cards

*Why:* The same radial highlight at the top-left corner on every card makes the whole page feel lit by one consistent light source. Consistency of light direction is what reads as "designed".

```css
.card-sheen{border-radius:24px;padding:28px;
  background:radial-gradient(62.56% 62.56% at 28.14% -10.42%,rgb(255 255 255/.2),transparent),var(--surface);
  box-shadow:0 7.77px 16px rgb(0 0 0/.06),0 3px 3px rgb(0 0 0/.1),inset 0 -8px 0 rgb(0 0 0/.05),inset 0 4px 0 rgb(255 255 255/.6);}
.card-sheen.dark{background:radial-gradient(62.56% 62.56% at 28.14% -10.42%,rgb(255 255 255/.1),transparent),#18181B;color:#fff;
  box-shadow:0 7.77px 2.21px rgb(0 0 0/.06),0 3px 3px rgb(0 0 0/.1),inset 0 -8px 0 #111,inset 0 4px 0 rgb(255 255 255/.1);}
```

## Framed hero with notch tab

```css
.hero-frame{margin:12px;border-radius:40px;overflow:hidden;position:relative;min-height:calc(100svh - 24px);
  background:radial-gradient(120% 80% at 70% 30%,#fff 0%,#E4E4E7 60%,#D4D4D8 100%)}
.notch{position:absolute;bottom:0;left:50%;translate:-50% 0;padding:14px 48px 12px;background:var(--page);
  border-radius:24px 24px 0 0;font-size:14px}
.notch::before,.notch::after{content:"";position:absolute;bottom:0;width:24px;height:24px;
  background:radial-gradient(circle at 0 0,transparent 23.5px,var(--page) 24px)}
.notch::before{left:-24px}
.notch::after{right:-24px;transform:scaleX(-1)}
```
The inverse-radius corners make the tab look *cut* into the frame. Put a 3D render (glossy ribbon, glass shape, chrome object) bleeding off the right side of the frame.

**Inline pill in headline** with bobbing icons: `<span class="h-pill"><img …><img …><img …></span>` with `display:inline-block;width:2.2em;height:.8em;border-radius:999px;background:var(--accent-grad);vertical-align:middle;position:relative` and the icons absolutely positioned, rotated ±12°, white rounded squares with shadow, `animation:bob 3s ease-in-out infinite` with staggered delays. If the icons stand for real products, they are those products' real logos (`shared/logos.md`).
