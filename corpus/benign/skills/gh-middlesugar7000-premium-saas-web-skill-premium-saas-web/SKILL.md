---
name: premium-saas-web
description: Build premium, ThemeForest-top-seller-grade websites for SaaS, AI products, agencies, startups and tech portfolios — sculpted color glows, animated gradient borders, tactile glossy buttons, glass navs, bento grids with mini product UIs, giant tight-tracked headlines, scroll-scrubbed text reveals, smooth scroll and GSAP motion. Use this skill whenever the user asks for a landing page, homepage, marketing site, pricing page, waitlist page, product page or portfolio for a SaaS / AI / tech / agency / startup brand, or says things like "make it look premium / expensive / modern / like a top template", "Vercel/Linear/Framer style", "dark glowing hero", "glassmorphism", or asks for a friendly, warm, indie-style landing for a desktop/menu-bar/mobile app or utility — in any language, and even if they don't name a style. Also use it when redesigning an existing tech/SaaS page to look higher-end.
license: MIT
metadata:
  author: MiddleSugar7000
  homepage: https://github.com/MiddleSugar7000/premium-saas-web-skill
  version: "1.3.0"
---

# Premium SaaS Web

This skill encodes what makes the best-selling SaaS/AI/agency templates feel expensive. It was distilled by inspecting six reference sites at the CSS level (OptimAI, Aigocy, Adon, Davies, Pastily, an AI image generator demo) and measuring the actual values they use. The recipes are the real techniques, not guesses.

**File layout.** Load only what the task needs:
- `directions/<name>/style.md`: one file per visual direction (tokens, fonts, signature pieces, techniques only that direction uses). Read **only the one you pick**.
- `shared/*.md`: techniques every direction uses, split by topic. Read the ones for the sections you are building (map in step 3).

## The core insight: premium = controlled light + restraint + motion

Cheap pages and premium pages often use the *same* components (hero, logos, features, pricing, FAQ, CTA). The difference is in four layers of finish:

1. **Light** — surfaces look lit, not filled. Glows are sculpted from blurred shapes; cards have a top-left sheen; buttons have an inner highlight and an inner bottom edge; borders are hairlines at 6–20% opacity. Real light falls off, so nothing is a flat block of color.
2. **Restraint** — one accent color, used on ≤5% of the page. Text hierarchy comes from *opacity of one color* (100 / 80 / 60 / 50%), not from many grays. Two fonts max (+ an optional mono for labels). Zero decoration that doesn't carry meaning.
3. **Typography with tension** — display type is big and *tightly tracked* (letter-spacing −2% to −7%), line-height ≈ 1.0–1.2. Half of a headline is often dimmed (`opacity .5` or a lighter gradient) so the eye reads the strong half first.
4. **Motion with weight** — smooth scroll (Lenis), headlines that rise word-by-word, text that fills as you scroll, counters that roll, marquees that never stop, cards that stack. Everything eases out (no linear), nothing bounces, and it all respects `prefers-reduced-motion`.

If an output only has the components but not these four layers, it will look like a free Bootstrap theme no matter how many sections it has.

## Workflow

### 1. Read the brief, pick ONE direction

Choose a direction from this table, then read its `directions/<folder>/style.md` (full token set + its signature techniques). Don't read the other directions.

| Direction (folder) | Feel | Best for | Source |
|---|---|---|---|
| **Ember Dark** (`ember-dark`) | Deep navy-black, sculpted orange/red or blue glow, rainbow-border CTA, mono button labels | AI tools, dev tools, SaaS apps | OptimAI |
| **Tactile Light** (`tactile-light`) | Zinc/off-white, glossy skeuomorphic buttons, sheen cards, one hot accent (red), framed hero with 3D render | AI agencies, B2B SaaS, consultancies | Aigocy |
| **Editorial Mono** (`editorial-mono`) | Pure #111 on #F0F0F0, 140px grotesk at −7% tracking, hairline grid, scroll-fill text, no shadows | Agencies, studios, premium services | Adon |
| **Noir Spotlight** (`noir-spotlight`) | Black, one neon accent, giant word interacting with a photo, shader/WebGL bg, stacking project cards | Personal brands, portfolios, creative tech | Davies |
| **Warm Playful** (`warm-playful`) | Warm off-white paper, near-black ink, muted green→gold, 28px white cards, handwritten notes, device bleeding off the edge, photo-backed pricing | Desktop/menu-bar apps, utilities, indie & consumer tools, one-time-purchase software | Pastily |

If the user didn't specify and it's SaaS/AI, default to **Ember Dark**. Switch to **Warm Playful** when the product is a native/desktop/mobile utility, an indie or solo-founder tool, or the brief says friendly, approachable, cozy, "not corporate" (even if it never says "SaaS"). Ember Dark would make a $9 clipboard app feel like enterprise infrastructure. Mixing directions is how pages get muddy. Borrowing one *technique* from another direction is fine, as long as the palette and type stay coherent.

Tell the user in one line which direction you picked and why, so they can redirect early. Keep the direction's accent unless the brand has its own color (the user names one, or the product already uses one); mood words like "cozy" or "dusk" are not a brand color. For a real brand color, see "Swapping the accent" in `directions/README.md`.

### 2. Plan the page as a rhythm, not a list

Premium pages alternate density and tone. A typical SaaS home that works:

1. **Hero**: eyebrow badge (a pill like "✦ AI-Driven Agency" or a real fact such as "v1.4 is out"; an avatar stack + rating only when the user gave you a real rating), 2-line headline with a dimmed half, 1–2 line subcopy at 60% opacity, primary + secondary CTA, then **the product itself** (browser-framed mockup or an interactive prompt box) bleeding into the next section via a gradient fade.
2. **Logo strip**: grayscale logos, infinite marquee, masked edges.
3. **Bento feature grid**: 5–7 cells of unequal size, each with a *mini UI illustration* built in HTML/CSS (workflow nodes, chat bubbles, toggles, charts, color chips), not stock icons.
4. **Scroll-fill statement**: one big sentence that fills from 30% → 100% as you scroll. The fill runs strictly line by line (one scrubbed timeline per block, lines back-to-back), never several lines at once. See `shared/typography.md`.
5. **Numbers**: 3–4 stats with rolling counters; one giant faded number as decoration.
6. **How it works / tabs** or **stacking cards**.
7. **Testimonials**: only quotes the user supplied, avatar + name + role, maybe a vertical marquee of cards. If there are none, leave the section out (or swap it for a trust/privacy band or a short note from the maker). Invented reviews, ratings and user counts are fake social proof: they mislead buyers and the owner may ship them by accident.
8. **Pricing**: 3 tiers, middle one lifted with the accent border/glow, monthly/yearly toggle.
9. **FAQ** accordion.
10. **Final CTA** with the strongest glow on the page, then a calm footer with a huge wordmark.

Alternate dark/light (or bg-1/bg-2) section backgrounds to create rhythm. Section padding is generous: 120–176px vertical on desktop.

### 3. Build with the recipes

The recipes are copy-ready CSS/HTML/JS. Your direction's `style.md` already holds its signature techniques (e.g. rainbow border for Ember, tactile buttons and sheen cards for Tactile). For everything else, read the shared file that matches what you are building:

| Building… | Read |
|---|---|
| Hero light, glows, dot/grid/noise backgrounds, hairline grid & column guides | `shared/light.md` |
| Headlines (tight tracking, dimmed half, metallic gradient), scroll-fill statement (line-by-line GSAP, or word-by-word with colored keywords) | `shared/typography.md` |
| Product mockup in the hero (browser frame **or desktop-app device with OS chrome**), screenshot gallery, bento grid with mini-UIs | `shared/product-proof.md` |
| Glass nav, section-aware pill nav, eyebrow badge & avatar stack, handwritten annotations, soft white cards, card spotlight, marquees, pricing (3-tier, **photo-backed single price, or plain single-price card**), FAQ, footer wordmark | `shared/components.md` |
| Any named brand with an icon (integrations, logo strip, orbit, "works with") | `shared/logos.md` |
| GSAP + Lenis boilerplate, timing/easing table, `gsap.matchMedia()` reduced-motion pattern, reveals, counters, stacking cards, CSS-only tone-shifting story stack, pinned UI-chip wall, pinned scroll, hover, gotchas, native CSS scroll-driven motion | `shared/motion.md` |
| Shader/WebGL background, particle field, bloom (Three.js, with CSS fallback and mobile gate) | `shared/webgl.md` |

A full landing page usually needs all of them; a single section or a small edit needs only its row. All GSAP plugins incl. SplitText are free since 3.13, load them from jsDelivr.

### 4. Tech defaults

- Single-file HTML with Tailwind CDN (or the project's existing stack — follow it if there is one). Put design tokens in CSS custom properties on `:root` so a palette swap is one edit.
- Fonts from Google Fonts. Proven pairings from the references: **Sora + Inter Tight + IBM Plex Mono** (Ember), **Urbanist** (Tactile), **a grotesk like "Inter Tight"/"Schibsted Grotesk"/"Familjen Grotesk" + DM Sans** (Editorial), **Figtree/"Outfit"** (Noir).
- Icons: inline SVG (Lucide-style 1.5px stroke). Never emoji as icons.
- Images: if image generation is available, generate on-brand 3D renders / abstract objects; otherwise build visuals with CSS/SVG (glows, mini UIs, dot globes). Use `https://images.unsplash.com/...` photos only for people/portraits. A page with no visual anchor in the hero looks unfinished.
- **Real brand logos, never letter placeholders.** Whenever the page names an existing company, product or SaaS (integration chips, logo arcs/strips, "works with" bands, testimonials, comparison tables) and you show an icon next to it, use that brand's actual logo. A colored square with the initial ("F" for Figma, "S" for Slack) reads as a cheap template and breaks trust. Details and sources in `shared/logos.md`. If no real logo can be sourced, show the name as plain text with no icon at all; a fake icon is worse than none.
- Mobile: everything collapses to one column at <768px; display type scales with `clamp()`; glows shrink (big blurs are expensive on phones); disable cursor effects on touch.

### 5. Self-review before handing over

Open the page in a browser and screenshot at 1440px and 390px, if you can. Check against this list. These are the things that separate "AI-generated" from "top seller":

- [ ] Only one accent hue (plus neutrals). Gradients stay inside that hue family, except an intentional rainbow border.
- [ ] Display headline has negative letter-spacing and a dimmed half or gradient.
- [ ] Body/secondary text uses opacity steps of one color, and contrast still passes (≥4.5:1 for body).
- [ ] Hero shows the product (mockup, prompt box, UI), not just text over a gradient.
- [ ] At least one sculpted light source per dark section; no flat rectangles of pure color.
- [ ] Borders are hairlines (1px, 6–20% alpha), radii are consistent (pick a scale: 8/12/20/28/999).
- [ ] Buttons have hover states that change *light* (glow tightens, sheen shifts, arrow nudges 2–4px), not just color.
- [ ] Motion: hero text reveal, scroll-triggered fades with stagger, at least one scrubbed effect, marquee. All disabled under `prefers-reduced-motion` (via `gsap.matchMedia()`), durations taken from the timing table in `shared/motion.md`, nothing animates width/height/top/left.
- [ ] If WebGL is used: CSS glow underneath as fallback, DPR capped, renders only while visible, skipped on mobile/low-core devices, text stays in HTML.
- [ ] Every real brand named on the page has its real logo (or no icon). No initial-letter squares.
- [ ] If Warm Playful: the hero device is a real-looking OS (menubar, dock, app menu) built in HTML, bleeds off one edge, and has at most two Caveat notes; story cards stick with a 16px `top` step and a tone change per card; keyword colors appear on single words only and pass 4.5:1; the accent is still the green (unless the user gave a brand color) and gold appears only at the end of the CTA gradient; one-time pricing is a single white card (photo-backed if you have a photo, plain otherwise), with any free trial as a line inside it.
- [ ] No lorem ipsum. Copy is specific to the product: concrete numbers, real-sounding features.
- [ ] No invented social proof: no made-up ratings, user counts, testimonials or press logos. Product details you had to assume are listed for the user to confirm.
- [ ] Nothing overflows horizontally at 390px.

## What to avoid (the "cheap template" tells)

- **Buttons that move on hover. Hard rule, no exceptions.** No magnetic/cursor-following buttons, no `translate`/`scale`/`rotate` on a button or its label/icon on `:hover`, no arrows sliding out, no lift-on-hover. Layout stays still under the cursor, so the click target never dodges. Show hover with color, brightness, glow, border or shadow changes only. (Cards may still lift; buttons and links styled as buttons may not.)
- Purple-to-blue gradient on everything; multiple competing accent colors.
- Drop shadows like `0 4px 6px rgba(0,0,0,.3)` on dark backgrounds (shadows don't read on dark; use glows and borders instead).
- Centered everything with identical card grids of 3 icons + title + text.
- Glassmorphism without anything behind the glass to blur.
- Fake brand icons: a colored rounded square with a letter standing in for Figma, Slack, GitHub, etc.
- Bouncy/elastic easing, fade-ins that take >1s, animations on every element at once.
- Gradient text on body copy; more than one gradient-text phrase per viewport.
- Stock "AI brain" imagery. Show the product or an abstract render instead.
- Low-contrast body text on dark: keep body copy at least ~70% white so it stays readable against glows.
