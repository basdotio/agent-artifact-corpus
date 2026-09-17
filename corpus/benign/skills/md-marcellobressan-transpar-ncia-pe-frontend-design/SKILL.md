---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.
version: 1.0.0
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

## Implementation Guidelines

### CSS Architecture
- Use CSS custom properties (variables) for theming
- Implement responsive design with mobile-first approach
- Use modern CSS features: Grid, Flexbox, Container Queries
- Create smooth transitions and animations
- Consider dark/light mode from the start

### Component Quality
- Build accessible components (ARIA, keyboard navigation)
- Implement proper loading and error states
- Add meaningful hover/focus/active states
- Use semantic HTML elements
- Ensure cross-browser compatibility

### Animation Best Practices
- Use CSS animations for simple effects
- Use Framer Motion for React complex animations
- Implement staggered animations for lists
- Add micro-interactions on buttons and inputs
- Create smooth page transitions
- Consider reduced-motion preferences

### Typography System
- Define a clear type scale (headings, body, captions)
- Set proper line-heights and letter-spacing
- Use font-display: swap for web fonts
- Implement responsive typography with clamp()
- Pair fonts with purpose (display vs. body)

### Color System
- Create semantic color tokens (primary, secondary, accent)
- Define state colors (success, warning, error, info)
- Implement proper contrast ratios for accessibility
- Use color to create visual hierarchy
- Consider color blindness in design choices

## Project-Specific Context

This project uses:
- **React 19** with TypeScript
- **Tailwind CSS 3.4** with custom configuration
- **Framer Motion** for animations
- **Lucide React** for icons
- **Recharts** for data visualization
- **Headless UI** for accessible components

### Available Tailwind Extensions
- Custom brand colors (brand-50 to brand-950)
- Custom animations (fade-in, fade-in-up, slide-in-right, etc.)
- Glow shadows (shadow-glow, shadow-glow-lg)
- Typography plugin (@tailwindcss/typography)
- Forms plugin (@tailwindcss/forms)
- Animation plugin (tailwindcss-animate)

### UI Components Available
Located in `components/ui/`:
- Button (with variants: primary, secondary, outline, ghost, danger, success)
- Card (with variants: default, elevated, glass, gradient)
- Badge (with semantic colors)
- Input, SearchInput
- Modal (with Headless UI)
- Dropdown, Select
- Avatar, AvatarGroup
- Skeleton loaders

### Utility Function
```tsx
import { cn } from '@/lib/utils';
// Merges Tailwind classes intelligently
cn('px-2', condition && 'px-4') // => resolves conflicts
```

## Reference Resources

For detailed guidance on prompting for high-quality frontend design, see the [Frontend Aesthetics Cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/coding/prompting_for_frontend_aesthetics.ipynb).
