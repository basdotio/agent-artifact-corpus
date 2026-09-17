---
name: ui-ux-design
description: UI/UX design principles, design systems, accessibility, responsive design, and user experience best practices. Activates when discussing layouts, styling, design decisions, user flows, or visual design.
---

# UI/UX Design Principles

This skill provides expert guidance on user interface and user experience design, applicable across all frontend frameworks.

## When to Apply This Skill

Use these principles when:
- Designing component layouts and visual hierarchy
- Creating or improving user flows
- Making design system decisions
- Implementing responsive designs
- Ensuring accessibility compliance
- Discussing color, typography, or spacing

## Core Design Principles

### 1. Visual Hierarchy

**Establish Clear Information Architecture**
- Use size, color, and spacing to indicate importance
- Guide user attention to primary actions
- Group related elements visually

```css
/* Good: Clear hierarchy */
.card-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.card-description {
  font-size: 1rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
}

.card-metadata {
  font-size: 0.875rem;
  color: var(--text-tertiary);
}
```

### 2. Consistency

**Design System Tokens**
- Define colors, spacing, typography centrally
- Use CSS variables or design tokens
- Maintain consistency across components

```css
:root {
  /* Spacing scale (4px base) */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */

  /* Color palette */
  --primary: #3b82f6;
  --primary-hover: #2563eb;
  --danger: #ef4444;
  --success: #10b981;

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Code', monospace;
}
```

### 3. Responsive Design

**Mobile-First Approach**
- Design for smallest screen first
- Progressively enhance for larger screens
- Use fluid typography and spacing

```css
/* Mobile-first */
.container {
  padding: var(--space-4);
  max-width: 100%;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    padding: var(--space-6);
    max-width: 720px;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    padding: var(--space-8);
    max-width: 1200px;
  }
}
```

**Fluid Typography**
```css
/* Responsive font sizing */
h1 {
  font-size: clamp(1.75rem, 5vw, 3rem);
}

p {
  font-size: clamp(1rem, 2.5vw, 1.125rem);
  line-height: 1.6;
}
```

### 4. Accessibility (a11y)

**WCAG 2.1 AA Compliance**

**Color Contrast**
- Text: 4.5:1 minimum contrast ratio
- Large text (18pt+): 3:1 minimum
- Interactive elements: Clear focus states

```css
/* Good: Sufficient contrast */
.button-primary {
  background: #2563eb;  /* Contrast with white text: 8.6:1 */
  color: #ffffff;
}

/* Focus states for keyboard navigation */
.button:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
```

**Semantic HTML**
```html
<!-- Good: Semantic and accessible -->
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
  </ul>
</nav>

<main>
  <article>
    <h1>Page Title</h1>
    <section>
      <h2>Section Title</h2>
      <p>Content...</p>
    </section>
  </article>
</main>

<!-- Bad: Divitis and non-semantic -->
<div class="navigation">
  <div class="nav-item">Home</div>
</div>
```

**ARIA Attributes**
```html
<!-- Loading state -->
<button aria-busy="true" aria-live="polite">
  <span aria-hidden="true">⏳</span>
  Loading...
</button>

<!-- Error message -->
<input
  type="email"
  aria-describedby="email-error"
  aria-invalid="true"
/>
<span id="email-error" role="alert">
  Please enter a valid email address
</span>
```

### 5. User Feedback

**Loading States**
```jsx
// Skeleton screens for content loading
function UserCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-12 w-12 bg-gray-300 rounded-full" />
      <div className="h-4 bg-gray-300 rounded w-3/4 mt-2" />
      <div className="h-4 bg-gray-300 rounded w-1/2 mt-2" />
    </div>
  );
}
```

**Error States**
```jsx
// Clear, actionable error messages
function ErrorMessage({ error, retry }) {
  return (
    <div role="alert" className="error-banner">
      <svg aria-hidden="true">⚠️</svg>
      <div>
        <h3>Something went wrong</h3>
        <p>{error.message}</p>
      </div>
      <button onClick={retry}>Try Again</button>
    </div>
  );
}
```

**Success Feedback**
- Provide immediate visual confirmation
- Use toast notifications for non-blocking feedback
- Maintain context (don't navigate away immediately)

### 6. Interaction Design

**Button States**
```css
.button {
  /* Default state */
  background: var(--primary);
  color: white;
  transition: all 150ms ease;

  /* Hover state */
  &:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }

  /* Active state */
  &:active {
    transform: translateY(0);
  }

  /* Disabled state */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Loading state */
  &[aria-busy="true"] {
    position: relative;
    color: transparent;
  }
}
```

**Microinteractions**
- Provide subtle feedback for user actions
- Use transitions for state changes
- Keep animations under 300ms for responsiveness

```css
/* Card hover effect */
.card {
  transition: transform 200ms ease, box-shadow 200ms ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}
```

### 7. Form Design

**User-Friendly Forms**
```html
<form>
  <!-- Label association -->
  <label for="email">
    Email Address
    <span aria-label="required">*</span>
  </label>
  <input
    id="email"
    type="email"
    required
    autocomplete="email"
    placeholder="you@example.com"
    aria-describedby="email-hint"
  />
  <small id="email-hint">We'll never share your email</small>

  <!-- Inline validation -->
  <div role="alert" id="email-error" class="hidden">
    Please enter a valid email address
  </div>
</form>
```

**Form Best Practices**
- One column layout on mobile
- Group related fields
- Show validation inline and on submit
- Disable submit button during processing
- Preserve user input on errors

### 8. Color Theory

**Color Palette Structure**
```css
:root {
  /* Primary palette (brand) */
  --primary-50: #eff6ff;
  --primary-500: #3b82f6;  /* Main brand color */
  --primary-900: #1e3a8a;

  /* Semantic colors */
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;

  /* Neutral palette */
  --gray-50: #f9fafb;
  --gray-500: #6b7280;
  --gray-900: #111827;

  /* Text colors */
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-600);
  --text-tertiary: var(--gray-400);
}
```

**Dark Mode Support**
```css
@media (prefers-color-scheme: dark) {
  :root {
    --text-primary: var(--gray-50);
    --text-secondary: var(--gray-400);
    --bg-primary: var(--gray-900);
    --bg-secondary: var(--gray-800);
  }
}
```

### 9. Typography

**Typographic Scale**
```css
:root {
  /* Type scale (1.25 ratio) */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.25rem;    /* 20px */
  --text-xl: 1.5rem;     /* 24px */
  --text-2xl: 1.875rem;  /* 30px */
  --text-3xl: 2.25rem;   /* 36px */

  /* Line heights */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;
}
```

**Readable Text**
- Optimal line length: 50-75 characters
- Line height: 1.5-1.75 for body text
- Sufficient contrast (4.5:1 minimum)

## Design Patterns

### Card Pattern
```jsx
function Card({ title, description, action, image }) {
  return (
    <article className="card">
      {image && <img src={image} alt="" className="card-image" />}
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-description">{description}</p>
      </div>
      {action && (
        <footer className="card-footer">
          <button>{action.label}</button>
        </footer>
      )}
    </article>
  );
}
```

### Modal Pattern
```jsx
function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
```

## UX Best Practices

1. **Progressive Disclosure** - Show only what's necessary, reveal details on demand
2. **Consistent Navigation** - Keep navigation in expected locations
3. **Forgiving Design** - Allow undo, confirm destructive actions
4. **Performance Perception** - Use optimistic updates, skeleton screens
5. **Mobile Gestures** - Support swipe, pinch-to-zoom where appropriate

## Design System Checklist

When building a design system:
- [ ] Color palette with semantic naming
- [ ] Typography scale and font families
- [ ] Spacing scale (4px or 8px base)
- [ ] Component library with consistent API
- [ ] Accessibility guidelines
- [ ] Dark mode support
- [ ] Documentation with live examples
- [ ] Design tokens (CSS variables or similar)

## Tools and Resources

- **Design Tools**: Figma, Adobe XD
- **Accessibility**: axe DevTools, WAVE
- **Color Contrast**: WebAIM Contrast Checker
- **Typography**: Modular Scale Calculator
- **Icons**: Heroicons, Lucide, Phosphor

## Anti-Patterns to Avoid

❌ **Low contrast text**
❌ **Tiny touch targets on mobile** (minimum 44×44px)
❌ **Removing focus outlines** without alternative
❌ **Auto-playing media** without controls
❌ **Using color alone** to convey information
❌ **Horizontal scrolling** (except carousels)
❌ **Opening links in new tabs** without indication
