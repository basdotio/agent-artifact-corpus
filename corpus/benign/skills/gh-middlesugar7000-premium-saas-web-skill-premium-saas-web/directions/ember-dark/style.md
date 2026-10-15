# Ember Dark (from OptimAI)

**Why it works:** A near-black *blue-tinted* base (not pure #000) makes warm glows look like they're emitting light. The glow is carved into shape, so it reads as a light source, not a gradient. Text is one white at different opacities, so the page feels calm despite the fire.

## Tokens

```css
:root{
  --bg-0:#0D1017;   /* page base (section bg) */
  --bg-1:#11141D;   /* alt section */
  --bg-2:#191D2A;   /* cards, inputs, nav pill fill */
  --bg-3:#252A32;   /* raised chips, hover */
  --light-0:#F8F9FA; --light-1:#F1F4F6; --light-2:#E4EAEE; /* light sections */
  --line: rgb(148 163 184 / .18);   /* hairline borders (slate-ish) */
  --line-strong: rgb(148 163 184 / .32);
  --fg: #fff;  /* use with opacity: 1 / .9 / .8 / .6 / .5 */
  --accent:#FF7300; --accent-deep:#5E1818; --glow:#FF0000; /* orange/red ember */
  /* blue variant: --accent:#5A9FFF; --glow:#2F6BFF; */
  --rainbow: #30E3FF,#8765FF,#FFF181,#FF4C52,#734CFF;
}
```
- **Fonts:** Sora 400 for display (64px, −0.05em, lh 1.2); Inter Tight for body; IBM Plex Mono 500 16px for *button labels and tags*. The mono buttons are a signature: they read "technical" without trying.
- **Radii:** 6px buttons, 12px inputs/chips, 20px cards, 28px big panels, 999px pills/avatars.
- **Signature pieces:** sculpted red/orange hero glow (`shared/light.md`), prompt-box hero, rainbow-border primary button with blurred rainbow under-glow, avatar stack + rating eyebrow, AI-model logo arc (center logo enlarged, glow behind), tilted image cards on an arc, browser-frame mockup with neon edge glow, bento with corner light leaks, integration logos on a blue radial spotlight band, dark/light section alternation.
- **Light sections:** `--light-0` bg, cards white with 1px `rgb(16 24 40 / .08)` border and `0 1px 4px rgb(16 24 40 / .1)` shadow; dark CTA buttons inside them keep the rainbow glow.
- **Cards:** `background:var(--bg-2); border:1px solid var(--line); border-radius:20px;` plus an optional top hairline highlight `box-shadow: inset 0 1px 0 rgb(255 255 255/.06)`.

## Animated rainbow border + under-glow

*Why:* A moving gradient border signals "AI / live / special" and draws the eye to the one action that matters. The blurred copy underneath makes the button look like it's casting colored light onto the page. **Use it on one or two elements per page only.**

```css
.btn-rainbow{
  --fill: var(--bg-2);
  position:relative;isolation:isolate;
  display:inline-flex;align-items:center;gap:8px;
  padding:13px 24px;border-radius:6px;
  font:500 16px/1.4 "IBM Plex Mono",monospace;color:#fff;
  border:2px solid transparent;
  background:
    linear-gradient(var(--fill),var(--fill)) padding-box,
    linear-gradient(#121213 0%,rgb(18 18 19/.6) 80%,rgb(18 18 19/0)) border-box,
    linear-gradient(90deg,var(--fill),#8765FF,#FFF181,#FF4C52,#734CFF,#8765FF,#FFF181,#FF4C52,#734CFF,var(--fill)) border-box;
  background-size:400% 100%;
  animation:rainbow 15s linear infinite;
}
.btn-rainbow::before{               /* the colored light it casts */
  content:"";position:absolute;z-index:-1;
  left:50%;bottom:-25%;width:80%;height:40%;translate:-50% 0;
  background:linear-gradient(90deg,#30E3FF,#8765FF,#FFF181,#FF4C52,#734CFF,#30E3FF,#8765FF,#FFF181,#FF4C52,#734CFF,#30E3FF);
  background-size:400% 100%;animation:rainbow 15s linear infinite;
  filter:blur(14px);transition:filter .5s ease;
}
.btn-rainbow:hover::before{filter:blur(10px)}  /* light "focuses" on hover */
@keyframes rainbow{to{background-position:400% 0}}
```
The middle layer (dark→transparent, top→bottom) hides the rainbow on the top edge, so the color seems to come from *below*. For a prompt box, apply the same background stack to the input wrapper with `border-radius:999px`.

## Pill button with side glow

*Why:* A white pill on dark is the clearest CTA there is. The blurred blue-yellow blob tucked behind its right edge reads as reflected light, and the glow brightening on hover makes it feel alive. The button itself never moves.

```html
<a class="btn-pill" href="#">Get started <svg>…chevron…</svg><span class="side-glow"></span></a>
```
```css
.btn-pill{position:relative;isolation:isolate;display:inline-flex;gap:7px;align-items:center;padding:13px 24px;border-radius:999px;
  background:linear-gradient(90deg,#DBE2E6 0%,#fff 71.6%);color:#0D1017;font:500 15px "IBM Plex Mono",monospace}
.side-glow{position:absolute;z-index:-1;right:0;top:50%;translate:0 -50%;width:88px;height:56px;border-radius:999px;
  background:linear-gradient(270deg,#5A9FFF 0%,rgb(255 250 107/.2) 95%);filter:blur(12px);transition:filter .4s,opacity .4s}
.btn-pill:hover .side-glow{filter:blur(9px);opacity:1}  /* light intensifies in place, nothing slides */
```

## Prompt-box hero (AI tools)

Rounded-full input (`background:var(--bg-2)` + the rainbow border stack above at reduced opacity), icons for voice/attach, a white circular send button, and under it a row of ghost dropdown chips (`Model ▾  Deep Search ▾  Think ▾  Edit Image ▾`) with 1px `--line` borders. Above it, a row of ✓ capability checks ("Text to Image · Photo to Text · …") at 60% opacity.

## Logo arc

Place N logo tiles (real brand logos, see `shared/logos.md`) on an arc with `transform: rotate(θ) translateY(-R) rotate(-θ)`; scale the center one to 1.4 with a glow behind it; on scroll, rotate the arc container slightly (`rotate: -8 → 8deg`, scrubbed).

## Spotlight band (integrations strip)

```css
.spotlight-band{background:radial-gradient(60% 120% at 50% 100%,#3F7BFF 0%,#1B3A8F 40%,var(--bg-0) 75%)}
```
