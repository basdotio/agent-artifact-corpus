---
name: brand-guidelines
description: Apply the 100 Hours Tracker "Lazy Lofi" brand styling to UI components, pages, and design elements. Use when creating or modifying any visual elements in the application.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: ui-development
---

# Brand Guidelines: Lazy Lofi

This skill ensures consistent visual styling across all UI components and pages in the 100 Hours Tracker application.

---

## Design Philosophy

**"Lazy Lofi"** - Like studying in a cozy café with lo-fi beats playing. Warm, soft, approachable, and unhurried.

### Core Principles

1. **Warmth over coldness**: Cream backgrounds, coral accents, sage greens - never sterile whites or harsh blues
2. **Playful but purposeful**: Bouncy animations and rounded corners that delight without distracting
3. **Cozy atmosphere**: Soft shadows, generous spacing, comfortable typography
4. **Encouraging tone**: Celebrate progress, make the grind feel pleasant

### Visual Keywords

- Warm sunset tones
- Soft, rounded shapes
- Gentle motion
- Inviting textures
- Friendly typography

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| **SvelteKit** | Framework (Svelte 5) |
| **Tailwind CSS 4** | Utility-first styling |
| **DaisyUI 5** | Component library with custom theme |
| **Svelte Motion** | `svelte/motion` for springs/tweens |
| **Svelte Transitions** | `svelte/transition` for enter/exit animations |
| **Google Fonts** | Fredoka + Outfit |

---

## Typography

### Font Families

| Role | Font | Weights | Usage |
|------|------|---------|-------|
| **Display** | Fredoka | 400, 500, 600, 700 | Headings, buttons, emphasis |
| **Body** | Outfit | 300, 400, 500, 600 | Body text, labels, inputs |

### Implementation

Fonts are loaded via Google Fonts in `layout.css`. Use these CSS variables:

```css
font-family: var(--font-display); /* Fredoka */
font-family: var(--font-body);    /* Outfit */
```

Or Tailwind utility classes:

```svelte
<h1 class="font-display">Welcome back!</h1>
<p>Your progress is looking great.</p> <!-- Uses body font by default -->
```

### Text Hierarchy

| Element | Classes | Example |
|---------|---------|---------|
| Page Title | `text-3xl font-display font-bold` | "Dashboard" |
| Section Heading | `text-xl font-display font-semibold` | "This Week" |
| Card Title | `text-lg font-display font-medium` | "Weekly Goal" |
| Body Text | `text-base` | Regular content |
| Small/Caption | `text-sm text-neutral` | "Updated 2 hours ago" |
| Label | `text-sm font-medium` | Form labels |

---

## Color Palette

### Theme Colors (DaisyUI)

The custom "lazylofi" theme is defined in `layout.css`. Use DaisyUI's semantic color classes:

| Role | Class | OKLCH Value | Usage |
|------|-------|-------------|-------|
| **Base 100** | `bg-base-100` | `oklch(98.5% 0.015 75)` | Cards, surfaces |
| **Base 200** | `bg-base-200` | `oklch(96.5% 0.02 70)` | Page background |
| **Base 300** | `bg-base-300` | `oklch(91% 0.025 65)` | Borders, dividers |
| **Base Content** | `text-base-content` | `oklch(35% 0.03 300)` | Primary text |
| **Primary** | `bg-primary` | `oklch(68% 0.14 35)` | Main actions (coral) |
| **Secondary** | `bg-secondary` | `oklch(68% 0.12 155)` | Success, completion (sage) |
| **Accent** | `bg-accent` | `oklch(82% 0.12 85)` | Highlights, celebrations (amber) |
| **Neutral** | `text-neutral` | `oklch(55% 0.025 300)` | Muted text |
| **Error** | `bg-error` | `oklch(62% 0.16 25)` | Errors (soft coral red) |
| **Success** | `bg-success` | `oklch(68% 0.12 155)` | Success states (sage) |
| **Warning** | `bg-warning` | `oklch(80% 0.13 85)` | Warnings (amber) |

### Color Usage Guidelines

```svelte
<!-- Primary action -->
<button class="btn btn-primary">Log Hours</button>

<!-- Success/completion -->
<div class="badge badge-secondary">Completed</div>

<!-- Celebration/milestone -->
<div class="badge badge-accent">50 Hours!</div>

<!-- Muted text -->
<span class="text-neutral">Last updated 2h ago</span>

<!-- Error state -->
<p class="text-error">Please enter a valid number</p>
```

### Gradients

For progress bars and special moments, use warm gradients:

```svelte
<!-- Progress gradient (coral to amber) -->
<div class="bg-gradient-to-r from-primary to-accent h-2 rounded-full"></div>

<!-- Celebration gradient (amber to sage) -->
<div class="bg-gradient-to-r from-accent to-secondary"></div>
```

---

## Motion & Animation

### Philosophy

Animations should feel **organic and playful** - like a friendly bounce, not mechanical precision. Use spring physics for natural movement.

### Svelte Motion (Springs & Tweens)

```svelte
<script>
  import { spring, tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  
  // Bouncy spring for interactive elements
  const scale = spring(1, { stiffness: 0.3, damping: 0.6 });
  
  // Smooth spring for progress
  const progress = spring(0, { stiffness: 0.05, damping: 0.5 });
  
  // Tweened for smooth number counting
  const hours = tweened(0, { duration: 800, easing: cubicOut });
</script>

<!-- Bouncy button -->
<button
  class="btn btn-primary"
  style="transform: scale({$scale})"
  onmouseenter={() => scale.set(1.05)}
  onmouseleave={() => scale.set(1)}
  onmousedown={() => scale.set(0.95)}
  onmouseup={() => scale.set(1.05)}
>
  Log Hours
</button>

<!-- Animated counter -->
<span class="text-4xl font-display">{Math.round($hours)}</span>
```

### Svelte Transitions

```svelte
<script>
  import { fade, fly, scale, slide } from 'svelte/transition';
  import { cubicOut, backOut } from 'svelte/easing';
</script>

<!-- Page content fade in -->
<div in:fade={{ duration: 300 }}>
  ...
</div>

<!-- Card fly up with stagger -->
{#each cards as card, i}
  <div 
    in:fly={{ y: 20, duration: 400, delay: i * 80, easing: cubicOut }}
    class="card bg-base-100"
  >
    ...
  </div>
{/each}

<!-- Modal pop in -->
<div in:scale={{ start: 0.9, duration: 200, easing: backOut }}>
  ...
</div>

<!-- Toast slide in -->
<div in:fly={{ x: 100, duration: 300 }} out:fade={{ duration: 200 }}>
  ...
</div>
```

### CSS Animations (Defined in layout.css)

```svelte
<!-- Floating effect -->
<div class="animate-float">...</div>

<!-- Wiggle for attention -->
<div class="animate-wiggle">...</div>

<!-- Soft pulse -->
<div class="animate-pulse-soft">...</div>

<!-- Pop in entrance -->
<div class="animate-pop-in">...</div>
```

### Hover & Press States

Buttons have built-in playful hover (lift + scale) defined in `layout.css`. For custom elements:

```svelte
<div class="transition-transform duration-200 hover:-translate-y-1 hover:shadow-soft-lg active:translate-y-0 active:scale-[0.98]">
  Hoverable card
</div>
```

### Recommended Easing

| Effect | Easing | Svelte Import |
|--------|--------|---------------|
| Entrances | `cubicOut` | `svelte/easing` |
| Bouncy pop | `backOut` | `svelte/easing` |
| Smooth | `cubicInOut` | `svelte/easing` |
| Elastic | `elasticOut` | `svelte/easing` |

---

## Component Patterns

### Buttons

```svelte
<!-- Primary - main actions -->
<button class="btn btn-primary">Log Hours</button>

<!-- Secondary - alternative actions -->
<button class="btn btn-secondary">View History</button>

<!-- Ghost - subtle actions -->
<button class="btn btn-ghost">Cancel</button>

<!-- Outline - secondary emphasis -->
<button class="btn btn-outline btn-primary">Edit</button>

<!-- With icon -->
<button class="btn btn-primary gap-2">
  <svg>...</svg>
  Log Hours
</button>

<!-- Loading state -->
<button class="btn btn-primary" disabled>
  <span class="loading loading-spinner loading-sm"></span>
  Saving...
</button>

<!-- Sizes -->
<button class="btn btn-primary btn-sm">Small</button>
<button class="btn btn-primary">Default</button>
<button class="btn btn-primary btn-lg">Large</button>
```

### Cards

```svelte
<!-- Basic card -->
<div class="card bg-base-100">
  <div class="card-body">
    <h2 class="card-title font-display">Card Title</h2>
    <p>Card content goes here.</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary btn-sm">Action</button>
    </div>
  </div>
</div>

<!-- Stat card -->
<div class="card bg-base-100">
  <div class="card-body">
    <p class="text-sm text-neutral">Hours This Week</p>
    <p class="text-4xl font-display font-bold text-primary">12.5</p>
    <p class="text-sm text-secondary">+3.5 from last week</p>
  </div>
</div>

<!-- Elevated card (more shadow) -->
<div class="card bg-base-100 shadow-soft-lg">
  ...
</div>
```

### Form Inputs

```svelte
<!-- Text input with label -->
<fieldset class="fieldset">
  <legend class="fieldset-legend">Hours</legend>
  <input type="number" class="input w-full" placeholder="0.0" />
</fieldset>

<!-- With validation error -->
<fieldset class="fieldset">
  <legend class="fieldset-legend">Hours</legend>
  <input type="number" class="input input-error w-full" />
  <p class="fieldset-label text-error">Please enter a valid number</p>
</fieldset>

<!-- Textarea -->
<fieldset class="fieldset">
  <legend class="fieldset-legend">Notes</legend>
  <textarea class="textarea w-full" rows="3" placeholder="What did you work on?"></textarea>
</fieldset>

<!-- Select -->
<fieldset class="fieldset">
  <legend class="fieldset-legend">Category</legend>
  <select class="select w-full">
    <option>Learning</option>
    <option>Practice</option>
    <option>Project</option>
  </select>
</fieldset>
```

### Progress Indicators

```svelte
<!-- Basic progress bar -->
<progress class="progress progress-primary w-full" value="75" max="100"></progress>

<!-- With label -->
<div>
  <div class="flex justify-between text-sm mb-2">
    <span class="font-medium">Weekly Goal</span>
    <span class="text-neutral">75/100 hours</span>
  </div>
  <progress class="progress progress-primary w-full" value="75" max="100"></progress>
</div>

<!-- Radial progress (for milestones) -->
<div class="radial-progress text-primary" style="--value:75; --size:8rem;">
  <span class="text-2xl font-display font-bold">75%</span>
</div>

<!-- Animated progress with Svelte -->
<script>
  import { spring } from 'svelte/motion';
  const progress = spring(0, { stiffness: 0.05, damping: 0.5 });
  
  // When data loads:
  progress.set(75);
</script>

<div class="w-full bg-base-300 rounded-full h-3 overflow-hidden">
  <div 
    class="bg-gradient-to-r from-primary to-accent h-full rounded-full"
    style="width: {$progress}%"
  ></div>
</div>
```

### Navigation

```svelte
<!-- Navbar -->
<nav class="navbar bg-base-100 shadow-soft">
  <div class="flex-1">
    <a href="/" class="text-xl font-display font-bold text-primary">100 Hours</a>
  </div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1">
      <li><a href="/">Dashboard</a></li>
      <li><a href="/log">Log Hours</a></li>
      <li><a href="/history">History</a></li>
    </ul>
  </div>
</nav>

<!-- Bottom navigation (mobile) -->
<div class="dock dock-bottom bg-base-100">
  <a href="/" class="dock-item dock-active">
    <svg>...</svg>
    <span class="dock-label">Home</span>
  </a>
  <a href="/log" class="dock-item">
    <svg>...</svg>
    <span class="dock-label">Log</span>
  </a>
</div>
```

### Badges & Status

```svelte
<!-- Status badges -->
<span class="badge badge-primary">In Progress</span>
<span class="badge badge-secondary">Completed</span>
<span class="badge badge-accent">Milestone!</span>
<span class="badge badge-neutral">Archived</span>

<!-- With glow for celebrations -->
<span class="badge badge-accent glow-accent animate-pulse-soft">
  50 Hours!
</span>

<!-- Status indicators -->
<span class="status status-success"></span>
<span class="status status-warning"></span>
<span class="status status-error"></span>
```

### Alerts & Toasts

```svelte
<!-- Success alert -->
<div class="alert alert-success">
  <svg>...</svg>
  <span>Hours logged successfully!</span>
</div>

<!-- Info alert -->
<div class="alert alert-info">
  <svg>...</svg>
  <span>You're 5 hours away from your weekly goal.</span>
</div>

<!-- Toast container -->
<div class="toast toast-end">
  <div class="alert alert-success" in:fly={{ x: 100 }} out:fade>
    <span>Saved!</span>
  </div>
</div>
```

---

## Layout Guidelines

### Page Structure

```svelte
<div class="min-h-screen bg-base-200">
  <!-- Navigation -->
  <nav class="navbar bg-base-100 shadow-soft sticky top-0 z-50">
    ...
  </nav>

  <!-- Main Content -->
  <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-3xl font-display font-bold mb-8">Page Title</h1>
    
    <div class="space-y-6">
      <!-- Content sections -->
    </div>
  </main>
</div>
```

### Spacing System

Use Tailwind's spacing scale consistently:

| Purpose | Class | Value |
|---------|-------|-------|
| Between form fields | `space-y-4` / `gap-4` | 1rem |
| Between sections | `space-y-6` / `gap-6` | 1.5rem |
| Card padding | `p-6` | 1.5rem |
| Page padding (vertical) | `py-8` | 2rem |
| Page padding (horizontal) | `px-4 sm:px-6 lg:px-8` | responsive |

### Responsive Breakpoints

Mobile-first approach using Tailwind breakpoints:

| Prefix | Min Width | Usage |
|--------|-----------|-------|
| (none) | 0px | Mobile default |
| `sm:` | 640px | Large phones, small tablets |
| `md:` | 768px | Tablets |
| `lg:` | 1024px | Desktops |
| `xl:` | 1280px | Large desktops |

```svelte
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  ...
</div>
```

---

## State Indicators

### Loading States

```svelte
<!-- Skeleton loader -->
<div class="animate-pulse space-y-4">
  <div class="h-4 bg-base-300 rounded w-3/4"></div>
  <div class="h-4 bg-base-300 rounded w-1/2"></div>
  <div class="h-32 bg-base-300 rounded"></div>
</div>

<!-- DaisyUI skeleton -->
<div class="skeleton h-32 w-full"></div>

<!-- Spinner -->
<span class="loading loading-spinner loading-lg text-primary"></span>
```

### Empty States

```svelte
<div class="text-center py-16">
  <div class="text-6xl mb-4">
    <!-- Friendly illustration or emoji -->
  </div>
  <h3 class="text-lg font-display font-medium mb-2">No hours logged yet</h3>
  <p class="text-neutral mb-6">Start tracking your progress today!</p>
  <button class="btn btn-primary">Log Your First Hour</button>
</div>
```

### Success States

```svelte
<div class="text-center py-8">
  <div class="text-6xl mb-4 animate-pop-in">
  </div>
  <h3 class="text-xl font-display font-bold text-secondary mb-2">
    Hours Logged!
  </h3>
  <p class="text-neutral">Keep up the great work.</p>
</div>
```

---

## Shadows

Custom soft shadow utilities defined in `layout.css`:

| Class | Usage |
|-------|-------|
| `shadow-soft-sm` | Subtle elevation (inputs on focus) |
| `shadow-soft` | Default card elevation |
| `shadow-soft-lg` | High elevation (modals, dropdowns) |
| `glow-primary` | Celebration glow (coral) |
| `glow-accent` | Celebration glow (amber) |
| `glow-success` | Celebration glow (sage) |

---

## Accessibility

### Color Contrast

All color combinations meet WCAG AA standards:

| Combination | Contrast Ratio | Status |
|-------------|---------------|--------|
| Base content on Base 100 | 7.2:1 | AAA |
| Primary on Primary content | 4.8:1 | AA |
| Neutral on Base 100 | 4.5:1 | AA |
| Error on Base 100 | 4.6:1 | AA |

### Focus States

All interactive elements include visible focus rings:

```svelte
<button class="btn btn-primary focus:ring-2 focus:ring-primary focus:ring-offset-2">
  ...
</button>
```

DaisyUI components have focus states built-in.

### Motion Preferences

Respect `prefers-reduced-motion`:

```svelte
<script>
  import { spring } from 'svelte/motion';
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  const scale = spring(1, prefersReducedMotion 
    ? { stiffness: 1, damping: 1 } 
    : { stiffness: 0.3, damping: 0.6 }
  );
</script>
```

### Semantic HTML

- Use proper heading hierarchy (`h1` > `h2` > `h3`)
- Use `<button>` for actions, `<a>` for navigation
- Include `aria-label` for icon-only buttons
- Use `<fieldset>` and `<legend>` for form groups

---

## Do's and Don'ts

### Do

- Use the warm "lazylofi" color palette consistently
- Apply `font-display` (Fredoka) to headings
- Use soft shadows (`shadow-soft`) on cards
- Add playful animations for feedback (springs, bounces)
- Include generous padding and spacing
- Use DaisyUI component classes for consistency
- Celebrate milestones with accent colors and glow effects

### Don't

- Use cold blues, grays, or stark whites
- Use sharp/hard shadows
- Skip hover and focus states
- Use generic system fonts
- Create harsh, jarring animations
- Use inline styles (prefer Tailwind/DaisyUI classes)
- Forget to test on mobile viewports
