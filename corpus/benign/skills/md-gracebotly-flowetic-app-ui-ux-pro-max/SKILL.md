---
name: ui-ux-pro-max
description: "UI/UX design intelligence. 50 styles, 21 palettes, 50 font pairings, 20 charts, 9 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, mobile app, .html, .tsx, .vue, .svelte. Elements: button, modal, navbar, sidebar, card, table, form, chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, flat design. Topics: color palette, accessibility, animation, layout, typography, font pairing, spacing, hover, shadow, gradient. Integrations: shadcn/ui MCP for component search and examples."
---

# UI/UX Pro Max Skill

## Overview
This skill provides access to a comprehensive design database via native Mastra tools.
All design recommendations MUST come from tool queries - never from LLM memory.

## Available Tools

### getStyleRecommendations
Search 67+ UI styles by product type, industry, and keywords.

**Query examples:**
- "fintech dashboard minimal"
- "healthcare monitoring dark"
- "startup saas bold"
- "enterprise corporate professional"
- "voice ai cyber glass"

**Returns:** Style category, colors (hex), effects, complexity rating, implementation checklist.

### getTypographyRecommendations
Search 57+ font pairings by style, mood, and use case.

**Query examples:**
- "professional corporate"
- "modern tech startup"
- "friendly approachable"
- "premium luxury"

**Returns:** Font pairings (heading + body), weights, line heights, use cases.

### getChartRecommendations
Search 25+ chart types by data pattern and visualization goal.

**Query examples:**
- "time series trend"
- "comparison categories"
- "part-to-whole percentage"
- "geographic distribution"

**Returns:** Chart type, secondary options, color guidance, accessibility notes, library recommendations.

### getProductRecommendations
Search industry-specific design patterns.

**Query examples:**
- "crm dashboard"
- "voice ai analytics"
- "workflow automation"
- "healthcare monitoring"

**Returns:** Primary style recommendation, landing page pattern, dashboard style, key considerations.

### getUXGuidelines
Search 98+ UX best practices by category and platform.

**Query examples:**
- "mobile navigation"
- "form validation"
- "accessibility wcag"
- "dashboard layout"

**Returns:** Guideline, do/don't examples, code samples, severity rating.

## Usage Rules

1. **ALWAYS** call tools before giving design advice
2. **NEVER** invent design values - use only what tools return
3. Reference specific values from results (hex codes, font names, style names)
4. If tools return empty, suggest broadening the query
5. Combine multiple tool results for comprehensive recommendations

## Data Sources
- styles.csv: 67 UI styles with colors, effects, complexity
- typography.csv: 57 font pairings with weights, use cases
- charts.csv: 25 chart types with accessibility notes
- products.csv: Industry-specific design patterns
- ux-guidelines.csv: 98 UX best practices

---

## Design System Workflow

### Generate Complete Design System
**Always start by generating a complete design system** before individual domain searches:

**Query Pattern:**
```
getProductRecommendations("<product_type> <industry>")
+ getStyleRecommendations("<product_type> <style_keywords>")
+ getTypographyRecommendations("<style_keywords>")
+ getChartRecommendations("<data_type>") [if dashboard]
+ getUXGuidelines("<platform> <category>")
```

**Example:**
```
User: "Create a fintech dashboard with dark mode"

1. getProductRecommendations("fintech dashboard")
   → Returns: Industry-specific design direction

2. getStyleRecommendations("fintech dark minimal professional")
   → Returns: Style category, hex colors, effects, complexity

3. getTypographyRecommendations("professional modern corporate")
   → Returns: Font pairings, weights, line heights

4. getChartRecommendations("time series trend comparison")
   → Returns: Chart types, color palettes, libraries

5. getUXGuidelines("dashboard layout dark mode accessibility")
   → Returns: Best practices, anti-patterns, code samples
```

### Design System Output Structure
A complete design system includes:
1. **Pattern** - Landing page structure (hero-centric, testimonial-driven, etc.)
2. **Style** - Visual direction (glassmorphism, minimalism, etc.) with hex colors
3. **Colors** - Primary, secondary, accent, background, text colors
4. **Typography** - Heading font + body font with weights and line heights
5. **Effects** - Shadows, borders, animations, glassmorphism values
6. **Anti-patterns** - What to avoid for this product type

### Persist Design System (Master + Overrides Pattern)
**For multi-page projects**, persist the design system for consistency:

**Concept:**
- `design-system/MASTER.md` → Global Source of Truth (all design rules)
- `design-system/pages/` → Page-specific overrides (deviations from Master)

**Hierarchical Retrieval Logic:**
1. When building a specific page (e.g., "dashboard"), first check `design-system/pages/dashboard.md`
2. If page file exists, its rules **override** the Master file
3. If page file doesn't exist, use `design-system/MASTER.md` exclusively

**When to Create Master:**
- User confirms a design system for the entire project
- Multiple pages will share the same design language

**When to Create Page Override:**
- User requests page-specific style (e.g., "Make checkout page simpler")
- Page has different density/spacing requirements
- Page has different color emphasis (e.g., success green for confirmation)

**Content Structure:**

**MASTER.md:**
```markdown
# [Project Name] Design System

## Style
- Category: Glassmorphism
- Primary: #667eea
- Effects: backdrop-blur-md, bg-white/10
- Dark mode primary: #818cf8

## Typography
- Heading: Inter Bold (700, 800)
- Body: Inter Regular (400, 500)
- Line height: 1.5

## Spacing
- Density: Comfortable
- Card padding: p-6
- Section gaps: space-y-8

## Components
- Border radius: rounded-xl
- Shadow: shadow-lg
- Hover: scale-105, transition-300ms
```

**pages/dashboard.md:**
```markdown
# Dashboard Page Overrides

## Spacing (OVERRIDE)
- Density: Compact (data-heavy)
- Card padding: p-4
- Section gaps: space-y-4

## Components (OVERRIDE)
- Border radius: rounded-lg (sharper for data tables)
- Charts: Use consistent color palette from MASTER
```

### Supplement with Domain Searches
After establishing the design system, use domain searches for specific needs:

**When to Search Additional Domains:**
| Need | Domain | Example Query |
|------|--------|---------------|
| Alternative styles | `style` | "brutalism bold high-contrast" |
| More font options | `typography` | "elegant luxury serif" |
| Chart variations | `chart` | "funnel conversion visualization" |
| UX validation | `ux` | "mobile touch targets animation" |
| Industry patterns | `product` | "healthcare HIPAA compliance" |

---

## Quick Reference by Priority

When designing or reviewing UI, apply these guidelines in priority order:

| Priority | Category | Impact | Key Rules |
|----------|----------|--------|-----------|
| 1 | Accessibility | CRITICAL | 4.5:1 contrast, focus states, alt text, aria-labels, keyboard nav |
| 2 | Touch & Interaction | CRITICAL | 44x44px targets, cursor-pointer, hover feedback, loading states |
| 3 | Performance | HIGH | WebP images, lazy loading, reduced-motion, no content jumping |
| 4 | Layout & Responsive | HIGH | Mobile-first, 16px min font, no horizontal scroll, z-index scale |
| 5 | Typography & Color | MEDIUM | 1.5-1.75 line height, 65-75 char lines, font pairing |
| 6 | Animation | MEDIUM | 150-300ms duration, transform/opacity only, skeleton screens |

### Critical Rules (Always Check)

**Accessibility:**
- `color-contrast`: Minimum 4.5:1 ratio for normal text
- `focus-states`: Visible focus rings on all interactive elements
- `alt-text`: Descriptive alt text for meaningful images
- `aria-labels`: Required for icon-only buttons
- `keyboard-nav`: Tab order matches visual order
- `form-labels`: Use label with for attribute

**Touch & Interaction:**
- `touch-target-size`: Minimum 44x44px touch targets
- `cursor-pointer`: Add to all clickable/hoverable elements
- `hover-feedback`: Clear visual feedback (color, shadow, border)
- `loading-buttons`: Disable during async operations
- `error-feedback`: Clear error messages near problem

**Performance:**
- `image-optimization`: Use WebP, srcset, lazy loading
- `reduced-motion`: Check prefers-reduced-motion media query
- `content-jumping`: Reserve space for async content

---

## Domain Search Guide

Use these domains to get specific design recommendations:

| Domain | Use For | Example Keywords | Tool |
|--------|---------|------------------|------|
| `product` | Product type recommendations | SaaS, e-commerce, portfolio, healthcare, beauty | getProductRecommendations |
| `style` | UI styles, colors, effects | glassmorphism, minimalism, dark mode, brutalism | getStyleRecommendations |
| `typography` | Font pairings, Google Fonts | elegant, playful, professional, modern | getTypographyRecommendations |
| `color` | Color palettes by product type | saas, ecommerce, healthcare, beauty, fintech | getStyleRecommendations |
| `chart` | Chart types, library recommendations | trend, comparison, timeline, funnel, pie | getChartRecommendations |
| `ux` | Best practices, anti-patterns | animation, accessibility, z-index, loading | getUXGuidelines |

### When to Use Each Domain

**Start with `product`:** Get industry-specific design direction
```
getProductRecommendations("voice ai analytics dashboard")
Returns: Primary style, landing pattern, dashboard style, key considerations
```

**Follow with `style`:** Get detailed visual direction
```
getStyleRecommendations("fintech minimal professional")
Returns: Style category, hex colors, effects, complexity rating, checklist
```

**Add `typography`:** Get font pairings
```
getTypographyRecommendations("professional corporate modern")
Returns: Heading + body fonts, weights, line heights, use cases
```

**Include `chart`:** For data visualization
```
getChartRecommendations("time series trend comparison")
Returns: Chart types, secondary options, color guidance, libraries
```

**Check `ux`:** For best practices
```
getUXGuidelines("mobile navigation accessibility")
Returns: Guidelines, do/don't examples, code samples, severity rating
```

---

## Common Anti-Patterns (DO NOT DO)

Professional UI avoids these frequently overlooked issues:

### Icons & Visual Elements
| Rule | ✅ Do | ❌ Don't |
|------|-------|----------|
| **No emoji icons** | Use SVG icons (Heroicons, Lucide, Simple Icons) | Use emojis like 🎨 🚀 ⚙️ as UI icons |
| **Stable hover states** | Use color/opacity transitions on hover | Use scale transforms that shift layout |
| **Correct brand logos** | Research official SVG from Simple Icons | Guess or use incorrect logo paths |
| **Consistent icon sizing** | Use fixed viewBox (24x24) with w-6 h-6 | Mix different icon sizes randomly |

### Interaction & Cursor
| Rule | ✅ Do | ❌ Don't |
|------|-------|----------|
| **Cursor pointer** | Add `cursor-pointer` to all clickable/hoverable cards | Leave default cursor on interactive elements |
| **Hover feedback** | Provide visual feedback (color, shadow, border) | No indication element is interactive |
| **Smooth transitions** | Use `transition-colors duration-200` | Instant state changes or too slow (>500ms) |

### Light/Dark Mode Contrast
| Rule | ✅ Do | ❌ Don't |
|------|-------|----------|
| **Glass card light mode** | Use `bg-white/80` or higher opacity | Use `bg-white/10` (too transparent) |
| **Text contrast light** | Use `#0F172A` (slate-900) for text | Use `#94A3B8` (slate-400) for body text |
| **Muted text light** | Use `#475569` (slate-600) minimum | Use gray-400 or lighter for body text |
| **Border visibility** | Use `border-gray-200` in light mode | Use `border-white/10` (invisible) |

### Layout & Spacing
| Rule | ✅ Do | ❌ Don't |
|------|-------|----------|
| **Floating navbar** | Add `top-4 left-4 right-4` spacing | Stick navbar to `top-0 left-0 right-0` |
| **Content padding** | Account for fixed navbar height | Let content hide behind fixed elements |
| **Consistent max-width** | Use same `max-w-6xl` or `max-w-7xl` | Mix different container widths per page |

---

## Pre-Delivery Checklist

Before delivering UI code, verify ALL items:

### Visual Quality
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent set (Heroicons/Lucide/Simple Icons)
- [ ] Brand logos are correct (verified from Simple Icons)
- [ ] Hover states don't cause layout shift (no scale transforms)
- [ ] Use theme colors directly (bg-primary) not var() wrapper

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states provide clear visual feedback
- [ ] Transitions are smooth (150-300ms)
- [ ] Focus states visible for keyboard navigation
- [ ] Loading states disable buttons during async

### Light/Dark Mode
- [ ] Light mode text has sufficient contrast (4.5:1 minimum)
- [ ] Glass/transparent elements visible in light mode (bg-white/80+)
- [ ] Borders visible in both modes
- [ ] Test both modes before delivery

### Layout
- [ ] Floating elements have proper spacing from edges (top-4, not top-0)
- [ ] No content hidden behind fixed navbars
- [ ] Responsive at 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile

### Accessibility
- [ ] All images have descriptive alt text
- [ ] Form inputs have associated labels
- [ ] Color is not the only indicator of state
- [ ] `prefers-reduced-motion` respected for animations
- [ ] Minimum 44x44px touch targets on mobile

### Performance
- [ ] Images optimized (WebP, lazy loading, srcset)
- [ ] No content layout shift (CLS)
- [ ] Animations use transform/opacity (not width/height)
