---
name: prez
description: Create beautiful presentations from any codebase. Zero-opinion slide engine — you have full React/HTML/CSS freedom inside each slide.
metadata:
  author: Enriquefft
  version: "0.1.0"
  argument-hint: "describe the presentation you want"
---

# prez — Presentation Engine

Create presentations from any codebase. Users describe what they want, you build the slides.

## When to use

When the user asks you to create a presentation, pitch deck, slide deck, or any visual slide-based content from their project.

## Setup

If no `deck/` folder exists in the project, scaffold one:

```bash
curl -fsSL https://raw.githubusercontent.com/Enriquefft/prez/main/setup.sh | sh
```

Then `cd deck && bun install && bun run dev` to start the dev server at localhost:5173.

## API

Three components. That's it.

### `<Deck>` — Root container

```tsx
import { Deck, Slide, Notes } from '@enriquefft/prez'

<Deck>
  <Slide>...</Slide>
  <Slide>...</Slide>
</Deck>
```

Props:
- `aspectRatio?: string` — default `"16/9"`
- `transition?: 'none' | 'fade' | 'slide'` — default `'none'`
- `className?: string`
- `style?: CSSProperties`

### `<Slide>` — One slide

Full creative freedom inside. Use any HTML, CSS, Tailwind, React components, animations.

```tsx
<Slide>
  <div className="flex items-center justify-center h-full bg-black text-white">
    <h1 className="text-8xl font-bold">Anything goes</h1>
  </div>
</Slide>
```

Props: `className`, `style`, `children`

### `<Notes>` — Presenter notes

Renders nothing in normal view. Shown in presenter mode (Alt+Shift+P).

```tsx
<Slide>
  <h1>Revenue</h1>
  <Notes>Talk about Q3 growth. Mention 180% YoY.</Notes>
</Slide>
```

### `useDeck()` hook

Access deck state from inside a slide:

```tsx
const { currentSlide, totalSlides, next, prev, goTo } = useDeck()
```

## How to build slides

1. Read the user's codebase to understand their project, product, data, and brand
2. Edit `deck/src/slides.tsx` — this is the ONLY file you need to touch
3. Export a default **Fragment variable** (not a component) containing `<Slide>` children:
   ```tsx
   const slides = (
     <>
       <Slide>...</Slide>
       {/* JSX comments work here */}
       <Slide>...</Slide>
     </>
   )
   export default slides
   ```
4. In `main.tsx`, use `{slides}` (not `<Slides />`):
   ```tsx
   import slides from './slides'
   <Deck>{slides}</Deck>
   ```
5. Each `<Slide>` is 1280x720 and can contain anything — full React/HTML/CSS freedom
6. Use Tailwind classes (included by default) or inline styles
7. Import components from the parent project via relative paths (e.g., `../../src/components/Chart`)

## Design guidelines

- Each slide should have ONE clear message
- Use large text (text-5xl to text-8xl for titles)
- High contrast — dark backgrounds with light text, or vice versa
- Generous whitespace and padding (p-16 to p-24)
- Consistent color palette across the deck
- Use gradients, subtle animations, and visual hierarchy
- Add `<Notes>` for speaker talking points

## File structure

```
deck/
├── src/
│   ├── main.tsx      # Entry point (don't edit)
│   ├── slides.tsx    # YOUR SLIDES — edit this file
│   └── styles.css    # Tailwind + custom CSS
├── package.json
├── vite.config.ts
└── index.html
```

## Navigation (built-in, no code needed)

- Arrow keys, spacebar, Page Up/Down — navigate slides
- Home/End — first/last slide
- F — toggle fullscreen
- Alt+Shift+P — open presenter mode (separate window with notes + timer)
- Touch swipe on mobile
- URL hash sync (#/3 = slide 3)

## Export

```bash
bun run build          # Static SPA, deploy anywhere
bun run export:pdf     # PDF via system Chrome
bun run export:pptx    # PPTX via system Chrome + pptxgenjs
```

## Image tools

prez includes `prez-image` for getting images into slides. See `skills/prez-image/SKILL.md` for full docs.

```bash
bunx prez-image gen "prompt" -o deck/public/hero.png       # AI-generated image (free)
bunx prez-image search "query" -o deck/public/photo.jpg    # Royalty-free photo search
bunx prez-image render diagram.svg -o deck/public/out.png  # SVG to PNG
```

Save images to `deck/public/` and reference as `<img src="/hero.png" />`.
