# Design Tokens

Kompletne tokeny design systemu dla portfolio Pawla Lipowczana.

## Colors

### Primary Palette

| Token | Hex | RGB | Tailwind | Usage |
|-------|-----|-----|----------|-------|
| Primary Accent | `#00ff9d` | rgb(0, 255, 157) | `green-400` (approx) | Buttons, CTAs, highlights |
| Accent Hover | `#00ffa3` | rgb(0, 255, 163) | - | Hover states |
| Cyan | `#00b8ff` | rgb(0, 184, 255) | `cyan-400` (approx) | Gradient secondary |
| Background Dark | `#0a0e1a` | rgb(10, 14, 26) | - | Main background |
| Background Darker | `#050810` | rgb(5, 8, 16) | - | Deep sections |

### Text Colors

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| Text Primary | `#ffffff` | `text-white` | Headings, important |
| Text Secondary | `#e5e7eb` | `text-gray-200` | Body text |
| Text Muted | `#9ca3af` | `text-gray-400` | Descriptions |
| Text Subtle | `#6b7280` | `text-gray-500` | Less important |

### Semantic Colors

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| Success | `#10b981` | `text-emerald-500` | Success states |
| Error | `#ef4444` | `text-red-500` | Error states |
| Warning | `#f59e0b` | `text-amber-500` | Warning states |
| Info | `#3b82f6` | `text-blue-500` | Info states |

### Transparency Variants

```css
/* Card backgrounds */
--bg-card: rgba(255, 255, 255, 0.05);        /* bg-white/5 */
--bg-card-hover: rgba(255, 255, 255, 0.08);  /* bg-white/[0.08] */

/* Border colors */
--border-default: rgba(255, 255, 255, 0.1);  /* border-white/10 */
--border-hover: rgba(0, 255, 157, 0.3);      /* border-green-500/30 */

/* Accent transparency */
--accent-10: rgba(0, 255, 157, 0.1);         /* bg-green-500/10 */
--accent-20: rgba(0, 255, 157, 0.2);         /* bg-green-500/20 */
--accent-30: rgba(0, 255, 157, 0.3);         /* bg-green-500/30 */
```

## Gradients

### Text Gradient (Primary)

```css
.gradient-text {
  background: linear-gradient(to right, #00ff9d, #00b8ff, #00ffa3);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* Tailwind */
className="bg-gradient-to-r from-green-400 via-cyan-400 to-green-300 bg-clip-text text-transparent"
```

### Background Gradient

```css
.gradient-bg {
  background: linear-gradient(to bottom, #0a0e1a, #050810);
}
```

### Decorative Blur Gradients

```jsx
{/* Green blur */}
<div className="absolute w-72 h-72 bg-green-500/10 rounded-full blur-3xl" />

{/* Cyan blur */}
<div className="absolute w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
```

## Typography

### Font Families

```css
--font-heading: 'Inter', 'Poppins', system-ui, sans-serif;
--font-body: 'Inter', system-ui, sans-serif;
--font-mono: 'Fira Code', 'JetBrains Mono', monospace;
```

### Font Sizes (Tailwind Scale)

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| `text-xs` | 12px | 16px | Tags, badges |
| `text-sm` | 14px | 20px | Small text, captions |
| `text-base` | 16px | 24px | Body text |
| `text-lg` | 18px | 28px | Large body, descriptions |
| `text-xl` | 20px | 28px | Card titles |
| `text-2xl` | 24px | 32px | Section subtitles |
| `text-3xl` | 30px | 36px | Small headings |
| `text-4xl` | 36px | 40px | Section headings (mobile) |
| `text-5xl` | 48px | 48px | Section headings (tablet) |
| `text-6xl` | 60px | 60px | Section headings (desktop) |
| `text-7xl` | 72px | 72px | Hero title |
| `text-8xl` | 96px | 96px | Hero title (desktop) |

### Heading Hierarchy

```jsx
// H1 - Hero only (one per page)
<h1 className="text-6xl md:text-8xl font-bold uppercase tracking-tight">

// H2 - Section titles
<h2 className="text-4xl md:text-5xl lg:text-6xl font-bold">

// H3 - Card titles, subsections
<h3 className="text-xl md:text-2xl font-semibold">

// H4 - Minor headings
<h4 className="text-lg font-semibold">
```

### Font Weights

| Weight | Tailwind | Usage |
|--------|----------|-------|
| 400 | `font-normal` | Body text |
| 500 | `font-medium` | Emphasized body |
| 600 | `font-semibold` | Card titles, buttons |
| 700 | `font-bold` | Headings |

## Spacing

### Base Scale (Tailwind)

| Token | Value | Usage |
|-------|-------|-------|
| `p-1` | 4px | Minimal |
| `p-2` | 8px | Tags, badges |
| `p-3` | 12px | Small buttons |
| `p-4` | 16px | Card padding, standard |
| `p-6` | 24px | Card content |
| `p-8` | 32px | Section inner |
| `p-12` | 48px | Large spacing |
| `p-16` | 64px | Section padding |
| `p-20` | 80px | Section padding (py) |

### Section Spacing

```jsx
// Standard section
className="py-20 px-4 md:px-8 lg:px-16"

// Container max width
className="max-w-7xl mx-auto"

// Section header margin
className="mb-12 md:mb-16"

// Grid gaps
className="gap-6 md:gap-8"
```

### Component Spacing

```jsx
// Card inner padding
className="p-6"

// Button padding
className="px-6 py-3"

// Tag padding
className="px-2 py-1"

// Input padding
className="px-4 py-3"
```

## Shadows & Glows

### Green Glow Effect

```css
/* Standard glow */
box-shadow: 0 0 30px rgba(0, 255, 157, 0.3);

/* Subtle glow */
box-shadow: 0 0 30px rgba(0, 255, 157, 0.15);

/* Intense glow */
box-shadow: 0 0 50px rgba(0, 255, 157, 0.4);
```

### Tailwind Custom Shadows

```jsx
// Hover glow
className="hover:shadow-[0_0_30px_rgba(0,255,157,0.3)]"

// Card hover glow
className="hover:shadow-[0_0_30px_rgba(0,255,157,0.15)]"
```

### Standard Shadows

```css
/* Card shadow */
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

/* Elevated shadow */
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
```

## Border Radius

| Token | Value | Tailwind | Usage |
|-------|-------|----------|-------|
| Small | 4px | `rounded` | Tags, badges |
| Medium | 8px | `rounded-lg` | Buttons, inputs |
| Large | 12px | `rounded-xl` | Cards |
| Full | 9999px | `rounded-full` | Avatars, pills |

## Backdrop Blur

```jsx
// Navigation blur
className="backdrop-blur-md"  // 12px blur

// Card blur
className="backdrop-blur-sm"  // 4px blur
```

## Z-Index Scale

| Layer | Value | Usage |
|-------|-------|-------|
| Base | 0 | Content |
| Elevated | 10 | Cards, dropdowns |
| Sticky | 20 | Sticky elements |
| Fixed | 30 | Fixed elements |
| Modal Backdrop | 40 | Modal overlays |
| Modal | 50 | Modal content |
| Navigation | 50 | Header nav |
| Toast | 60 | Notifications |

## Breakpoints (Tailwind)

| Name | Min Width | Usage |
|------|-----------|-------|
| `sm` | 640px | Large phones |
| `md` | 768px | Tablets |
| `lg` | 1024px | Small laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large screens |

### Responsive Pattern

```jsx
// Mobile-first responsive
className="
  text-4xl        /* mobile */
  md:text-5xl     /* tablet */
  lg:text-6xl     /* desktop */
"

// Grid columns
className="
  grid-cols-1     /* mobile */
  md:grid-cols-2  /* tablet */
  lg:grid-cols-3  /* desktop */
"
```

## CSS Variables Template

```css
:root {
  /* Colors */
  --color-accent: #00ff9d;
  --color-accent-hover: #00ffa3;
  --color-cyan: #00b8ff;
  --color-bg-dark: #0a0e1a;
  --color-bg-darker: #050810;
  --color-text: #ffffff;
  --color-text-secondary: #e5e7eb;
  --color-text-muted: #9ca3af;

  /* Shadows */
  --shadow-glow: 0 0 30px rgba(0, 255, 157, 0.3);
  --shadow-glow-subtle: 0 0 30px rgba(0, 255, 157, 0.15);

  /* Transitions */
  --transition-default: all 0.3s ease;
  --transition-slow: all 0.5s ease;
}
```
