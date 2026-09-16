# Accessibility Checklist

WCAG 2.1 Level AA checklist dla portfolio Pawla Lipowczana.

## Pre-Development

- [ ] Define keyboard interaction model
- [ ] Plan focus management strategy
- [ ] Identify ARIA requirements
- [ ] Consider screen reader flow

## Semantic HTML

### Structure

- [ ] Use semantic elements: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`
- [ ] Only ONE `<h1>` per page
- [ ] Logical heading hierarchy (H1 -> H2 -> H3, no skipping)
- [ ] Use `<button>` for interactive elements (not div/span)
- [ ] Use `<a>` for navigation links
- [ ] Use `<ul>`/`<ol>` for lists

### Landmarks

```jsx
// Required landmarks
<header role="banner">       {/* Site header */}
<nav role="navigation">      {/* Main navigation */}
<main role="main">           {/* Main content */}
<footer role="contentinfo">  {/* Site footer */}

// Optional landmarks
<aside role="complementary"> {/* Sidebar content */}
<section role="region" aria-labelledby="section-title">
```

## Color Contrast

### Requirements

| Element | Minimum Ratio | Test Tool |
|---------|---------------|-----------|
| Normal text | 4.5:1 | WebAIM Contrast Checker |
| Large text (18pt+) | 3:1 | WebAIM Contrast Checker |
| UI components | 3:1 | WebAIM Contrast Checker |
| Focus indicators | 3:1 | WebAIM Contrast Checker |

### Portfolio Color Combinations

| Foreground | Background | Ratio | Pass? |
|------------|------------|-------|-------|
| `#ffffff` | `#0a0e1a` | 16.5:1 | Yes |
| `#e5e7eb` | `#0a0e1a` | 12.9:1 | Yes |
| `#00ff9d` | `#0a0e1a` | 12.1:1 | Yes |
| `#9ca3af` | `#0a0e1a` | 6.3:1 | Yes |
| `#6b7280` | `#0a0e1a` | 4.0:1 | Borderline |

### Best Practices

- [ ] Don't rely on color alone to convey information
- [ ] Provide additional indicators (icons, text, patterns)
- [ ] Test with colorblind simulation tools

## Keyboard Navigation

### Requirements

- [ ] All interactive elements are focusable
- [ ] Focus order matches visual order
- [ ] Focus indicator is clearly visible
- [ ] No keyboard traps
- [ ] Skip links available

### Focus Styles

```css
/* Default focus style */
:focus {
  outline: 2px solid #00ff9d;
  outline-offset: 2px;
}

/* Focus-visible for keyboard only */
:focus-visible {
  outline: 2px solid #00ff9d;
  outline-offset: 2px;
}

/* Remove focus for mouse users */
:focus:not(:focus-visible) {
  outline: none;
}
```

### Keyboard Interactions

| Component | Enter/Space | Escape | Arrow Keys | Tab |
|-----------|-------------|--------|------------|-----|
| Button | Activate | - | - | Next element |
| Link | Navigate | - | - | Next element |
| Menu | Open/Select | Close | Navigate items | Exit menu |
| Modal | - | Close | - | Trap focus |
| Form input | Submit | - | - | Next field |

### Modal/Menu Focus Management

```jsx
// Focus trap for modals
useEffect(() => {
  if (isOpen) {
    const firstElement = modalRef.current.querySelector('button, [href], input');
    firstElement?.focus();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }
}, [isOpen]);
```

## Images & Media

### Images

- [ ] All informative images have `alt` text
- [ ] Decorative images have `alt=""`
- [ ] Complex images have extended description
- [ ] Background images don't convey essential info

```jsx
// Informative image
<img src="project.jpg" alt="Screenshot of the project dashboard showing analytics" />

// Decorative image
<img src="decoration.svg" alt="" role="presentation" />

// Icon with text
<button>
  <FaGithub aria-hidden="true" />
  <span>View on GitHub</span>
</button>

// Icon-only button
<button aria-label="Open menu">
  <FaBars aria-hidden="true" />
</button>
```

### Video/Audio

- [ ] Captions for video content
- [ ] Transcripts for audio content
- [ ] No auto-playing media with sound

## Forms

### Labels

- [ ] All inputs have associated labels
- [ ] Labels are visible (not placeholder-only)
- [ ] Required fields are indicated
- [ ] Error messages are descriptive

```jsx
// Proper label association
<label htmlFor="email">Email Address</label>
<input
  id="email"
  type="email"
  aria-required="true"
  aria-describedby="email-error"
/>
<span id="email-error" role="alert">
  Please enter a valid email address
</span>
```

### Validation

```jsx
// Form validation pattern
<input
  type="email"
  aria-invalid={hasError}
  aria-describedby={hasError ? 'email-error' : undefined}
/>
{hasError && (
  <span id="email-error" role="alert" className="text-red-500">
    Please enter a valid email address
  </span>
)}
```

### Contact Form Checklist

- [ ] Name field has label
- [ ] Email field has label and type="email"
- [ ] Message field has label
- [ ] Submit button is a `<button type="submit">`
- [ ] Error messages are announced to screen readers
- [ ] Success message is announced

## ARIA Usage

### When to Use ARIA

1. When HTML semantics are insufficient
2. For dynamic content updates
3. For complex widgets (tabs, accordions, etc.)

### Common ARIA Patterns

```jsx
// Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// Expanded/collapsed state
<button
  aria-expanded={isOpen}
  aria-controls="menu-content"
>
  Menu
</button>
<div id="menu-content" hidden={!isOpen}>
  {/* Menu items */}
</div>

// Current page in navigation
<nav>
  <a href="/" aria-current="page">Home</a>
  <a href="/about">About</a>
</nav>

// Loading states
<button aria-busy={isLoading} disabled={isLoading}>
  {isLoading ? 'Sending...' : 'Send'}
</button>
```

### ARIA Labels for Icon Buttons

```jsx
// Social links
<a href="https://github.com/..." aria-label="View GitHub profile">
  <FaGithub aria-hidden="true" />
</a>

// Navigation toggle
<button aria-label="Open navigation menu">
  <FaBars aria-hidden="true" />
</button>

// Close button
<button aria-label="Close modal">
  <FaTimes aria-hidden="true" />
</button>
```

## Testing Commands

### Automated Testing

```bash
# Lighthouse accessibility audit
npx lighthouse http://localhost:5173 --only-categories=accessibility --output=html

# axe-core CLI
npx @axe-core/cli http://localhost:5173

# Pa11y
npx pa11y http://localhost:5173
```

### Browser Extensions

- axe DevTools (Chrome/Firefox)
- WAVE Evaluation Tool
- Accessibility Insights

### Manual Testing Checklist

- [ ] Navigate entire page using only keyboard
- [ ] Test with screen reader (NVDA, VoiceOver, JAWS)
- [ ] Zoom to 200% and verify layout
- [ ] Test with high contrast mode
- [ ] Disable CSS and verify content order

## Quick Fixes Checklist

### Common Issues

| Issue | Fix |
|-------|-----|
| Missing alt text | Add descriptive alt or alt="" for decorative |
| Low contrast | Use colors from design-tokens.md |
| Missing form labels | Add `<label htmlFor="id">` |
| Icon-only buttons | Add `aria-label` |
| Missing heading hierarchy | Use proper H1-H6 order |
| No focus indicator | Add `:focus-visible` styles |
| Keyboard inaccessible | Use `<button>` not `<div onClick>` |
| Auto-playing media | Add user controls |

### Portfolio-Specific Checks

- [ ] NetworkBackground canvas doesn't interfere with interaction
- [ ] Smooth scroll doesn't trap focus
- [ ] Mobile menu closes on Escape
- [ ] Contact form errors are announced
- [ ] Blog post content has proper heading structure
- [ ] Code blocks have accessible syntax highlighting

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)
- [MDN Accessibility Guide](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
