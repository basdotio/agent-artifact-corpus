---
name: ClaudeCanvas
description: Generate professional UI mockups and matching architecture diagrams for Upwork proposals. Use when the user asks to "create a mockup", "design a proposal visual", "make a ClaudeCanvas", or needs branded visuals for client proposals.
version: 1.0.0
context: fork
agent: general-purpose
model: opus
effort: max
argument-hint: "project description or job posting"
---

# ClaudeCanvas - Proposal Visual Generator

Generate matched pairs of UI mockups and architecture diagrams for Upwork proposals. Both visuals share the same color palette, typography, and visual language.

## Design Philosophy

**Show the finished product, not the architecture.** Clients want to see what their users will experience, not boxes and arrows. The UI mockup is primary; the architecture diagram is supporting documentation.

### What We Create
1. **UI Mockup**: The actual product interface users will see, embedded in realistic context (e.g., a contractor's website with an embedded calculator widget)
2. **Architecture Diagram**: Matching technical diagram with the same visual language

### What We Avoid
- "LLM Purple" gradients and generic AI aesthetics
- Landing pages instead of actual products
- Architecture diagrams as primary visuals
- Generic Stripe/checkout clones without context
- Over-stripped designs that lack character

## Chinchilla AI Brand Guide

### Primary Colors
```css
:root {
    --navy: #1B2D4F;           /* Primary dark - headers, primary buttons */
    --navy-light: #2A4170;     /* Hover states */
    --cream: #FDF8F3;          /* Primary background */
    --cream-dark: #F5EDE4;     /* Secondary backgrounds, cards */
    --warm: #E8DED3;           /* Borders, dividers */
    --warm-dark: #D4C8BB;      /* Stronger borders, connectors */
    --terracotta: #C4785A;     /* Accent - CTAs, highlights */
    --terracotta-light: #D4927A; /* Hover states */
    --sage: #7A9484;           /* Secondary accent - success, data */
    --text: #2C2C2C;           /* Primary text */
    --text-light: #6B6B6B;     /* Secondary text */
}
```

### Typography
- **Font**: Plus Jakarta Sans (Google Fonts)
- **Weights**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold), 800 (extrabold)
- **Import**: `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap`

### Design Tokens
- Border radius: 8px (small), 12px (medium), 16px (large)
- Box shadows: `0 4px 24px rgba(27, 45, 79, 0.08)`
- Transitions: `all 0.2s ease`

## Generation Workflow

### Step 1: Analyze Job Description
Extract from the Upwork job:
- **Product type**: Calculator, dashboard, form, widget, etc.
- **Industry context**: Flooring, healthcare, finance, etc.
- **Key features**: What the product needs to do
- **User type**: Who will use this (end customers, admins, etc.)

### Step 2: Create UI Mockup
Generate HTML/CSS mockup showing the product in context:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Product Name] | [Client Industry]</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --navy: #1B2D4F;
            --navy-light: #2A4170;
            --cream: #FDF8F3;
            --cream-dark: #F5EDE4;
            --warm: #E8DED3;
            --warm-dark: #D4C8BB;
            --terracotta: #C4785A;
            --terracotta-light: #D4927A;
            --sage: #7A9484;
            --text: #2C2C2C;
            --text-light: #6B6B6B;
        }
        /* ... full styling ... */
    </style>
</head>
<body>
    <!-- Realistic website context -->
    <!-- Embedded product widget/component -->
    <!-- Footer with Chinchilla AI branding -->
</body>
</html>
```

**Key principles:**
- Embed the product in a realistic website context (fake client company)
- Use industry-appropriate imagery and copy
- Show the product as users would actually see it
- Include Chinchilla AI attribution in footer

### Step 3: Create Architecture Diagram
Generate matching HTML diagram with same color palette:

```html
<!-- Same CSS variables and fonts -->
<div class="diagram-container">
    <div class="diagram-header">
        <!-- Navy header with title and Chinchilla AI badge -->
    </div>
    <div class="diagram-body">
        <!-- Architecture nodes using brand colors -->
        <!-- .arch-node.primary = navy -->
        <!-- .arch-node.accent = terracotta gradient -->
        <!-- .arch-node.sage = sage -->
        <!-- Default nodes = cream with warm border -->
    </div>
    <div class="tech-stack">
        <!-- Tech pills showing stack -->
    </div>
    <div class="diagram-footer">
        <!-- "Concept by CHINCHILLA AI" -->
    </div>
</div>
```

### Step 4: Generate Screenshots
Use Puppeteer to convert HTML to PNG:

```bash
cd /Users/tori/Documents/Repos/CHI/automations
node -e "
const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({
        executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        headless: 'new',
        args: ['--no-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 1024, deviceScaleFactor: 2 });
    await page.goto('file:///Users/tori/Documents/Repos/CHI/automations/output/[FILENAME].html');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'output/[FILENAME].png', fullPage: true });
    await browser.close();
    console.log('Screenshot saved');
})();
"
```

### Step 5: Upload to Slack
```bash
cd /Users/tori/Documents/Repos/CHI/automations/scripts
node slack-upload.js ../output/[FILENAME].png [CHANNEL_ID] --title "[Title]" --comment "[Description]"
```

**Channel IDs:**
- #general: C072D98C41X
- #upwork-pipeline: C09BDVBD1EY
- #upwork-jobs: C09BNP18741

## Output Location

All outputs go to: `/Users/tori/Documents/Repos/CHI/automations/output/`

Naming convention:
- `ClaudeCanvas-[ProjectName].html` - UI mockup source
- `ClaudeCanvas-[ProjectName].png` - UI mockup screenshot
- `ClaudeCanvas-[ProjectName]-Architecture.html` - Diagram source
- `ClaudeCanvas-[ProjectName]-Architecture.png` - Diagram screenshot

## Templates

### BeonIQ / Transportation Insight (Client: Marta)
**MANDATORY:** All BeonIQ mockups must use this template. It matches the production webapp exactly.

**Font:** Oswald globally (200–700). `https://fonts.googleapis.com/css2?family=Oswald:wght@200;300;400;500;600;700&display=swap`

**Colors:**
```css
:root {
    --beon-black: #000000;
    --beon-yellow: #FFEF00;
    --beon-cloud: #F1F4FA;
    --beon-gray: #B9BEC5;
    --beon-teal: #007587;
    --glass-bg: rgba(255, 255, 255, 0.15);
    --card-shadow: 0 2px 8px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05);
}
```

**Page background (5-layer gradient):**
```css
background:
    radial-gradient(ellipse 800px 400px at 20% 40%, rgba(255, 239, 0, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse 900px 450px at 80% 30%, rgba(0, 117, 135, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse 700px 500px at 50% 60%, rgba(255, 239, 0, 0.18) 0%, transparent 50%),
    radial-gradient(ellipse 800px 400px at 70% 70%, rgba(0, 117, 135, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse 600px 350px at 30% 80%, rgba(255, 239, 0, 0.12) 0%, transparent 50%),
    #F1F4FA;
```

**Glass cards (NO white borders — shadow ring only):**
```css
background: rgba(255, 255, 255, 0.15);
backdrop-filter: blur(20px);
border: none;
border-radius: 12px;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05);
```

**Layout structure:**
1. Black top panel (`#000000`, `border-bottom: 1px solid rgba(255,255,255,0.1)`)
   - Nav bar: Oswald logo "BEON**IQ**" (yellow IQ), nav links, user avatar
   - Greeting: Oswald 700, 32px, white + subtitle `rgba(255,255,255,0.75)`
   - Orb: Deep teal body `rgb(20,60,85)` with golden yellow accents `rgba(255,215,0,0.75)` and cyan fade
   - Search: glass input `rgba(255,255,255,0.1)` + `blur(12px) saturate(180%)`, yellow focus glow
   - Yellow arrow button: `#FFEF00` bg, black icon
2. Cloud content area (glass cards on gradient background)

**Orb CSS (matches beoniqOrbPalette):**
```css
.orb-large {
    background:
        radial-gradient(circle at 38% 38%, rgba(255, 215, 0, 0.75) 0%, rgba(255, 210, 0, 0.4) 35%, transparent 55%),
        radial-gradient(circle at 62% 62%, rgba(0, 200, 220, 0.5) 0%, transparent 50%),
        radial-gradient(circle at 50% 50%, rgb(20, 60, 85) 0%, rgb(15, 50, 75) 100%);
    box-shadow: 0 0 30px rgba(255, 215, 0, 0.3), 0 0 60px rgba(255, 210, 0, 0.15);
}
```

**Reference file:** `/Users/tori/Documents/Repos/CHI/automations/output/ClaudeCanvas-BeonIQ-VoiceOrb-Options-A-B-C.html`

### Pricing Calculator Widget
For jobs requiring embedded pricing/quote calculators.
- Shows calculator in contractor/business website context
- Two-column layout: inputs left, summary right
- Real-time calculation preview

### Dashboard
For jobs requiring admin dashboards or analytics.
- Sidebar navigation
- Card-based metrics
- Data tables and charts

### Form/Wizard
For multi-step forms or onboarding flows.
- Progress indicator
- Step-by-step sections
- Validation states

## Advanced Design Techniques (2025)

### Glassmorphism (Frosted Glass Effect)
```css
.glass-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
}
```
**Use for:** Floating cards over gradient backgrounds, overlay panels, hero sections

### Mesh Gradients
```css
.mesh-bg {
    background:
        radial-gradient(at 40% 20%, var(--terracotta-light) 0px, transparent 50%),
        radial-gradient(at 80% 0%, var(--sage) 0px, transparent 50%),
        radial-gradient(at 0% 50%, var(--navy-light) 0px, transparent 50%),
        var(--cream);
}
```
**Tools:** [csshero.org/mesher](https://csshero.org/mesher/), [colorffy.com](https://colorffy.com/mesh-gradient-generator)

### Modern CSS Features
```css
/* Container queries for responsive components */
.card-wrapper { container: card / inline-size; }
@container card (min-width: 400px) {
    .card { flex-direction: row; }
}

/* :has() for parent selection */
.form-group:has(input:invalid) {
    border-left: 3px solid var(--destructive);
}

/* Scroll-driven animations */
.fade-in-section {
    animation: reveal linear;
    animation-timeline: view();
    animation-range: entry 0% entry 50%;
}

/* @starting-style for enter animations */
dialog[open] {
    opacity: 1;
    transform: translateY(0);
    transition: opacity 300ms, transform 300ms, display 300ms allow-discrete;

    @starting-style {
        opacity: 0;
        transform: translateY(100px);
    }
}
```

### Micro-Interactions
```css
/* Button hover with lift */
.cta-button {
    transition: transform 150ms ease, box-shadow 150ms ease;
}
.cta-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(196, 120, 90, 0.3);
}

/* Card hover with depth */
.card:hover {
    transform: translateY(-4px) scale(1.01);
    box-shadow: 0 12px 32px rgba(27, 45, 79, 0.12);
}

/* Skeleton loading shimmer */
.skeleton {
    background: linear-gradient(90deg, var(--warm) 25%, var(--cream) 50%, var(--warm) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

### Glow Effects
```css
/* Neon text glow */
.glow-text {
    text-shadow:
        0 0 10px var(--terracotta),
        0 0 20px var(--terracotta),
        0 0 40px var(--terracotta-light);
}

/* Box glow on hover */
.glow-card:hover {
    box-shadow:
        0 0 20px rgba(196, 120, 90, 0.4),
        0 4px 24px rgba(27, 45, 79, 0.08);
}
```

### Color Palettes (Beyond AI Purple)

**Warm Professional (Current ClaudeCanvas default):**
```css
--navy: #1B2D4F; --terracotta: #C4785A; --cream: #FDF8F3; --sage: #7A9484;
```

**Ocean Teal (Tech/Healthcare):**
```css
--deep-teal: #1a4d4d; --ocean: #2d6a6a; --seafoam: #70b8a8; --cloud: #f0ebe3;
```

**Earth Tones (Construction/Real Estate):**
```css
--forest: #2d5a3d; --clay: #c4785a; --sandstone: #d4b896; --slate: #5a6670;
```

**Dark Mode Dashboard:**
```css
--bg-primary: #0a0a0f; --bg-card: #12121a; --border: #1e1e2d; --accent: #6366f1;
```

---

## Blender MCP Integration (3D Elements)

When Blender is running with MCP addon, you can enhance mockups with 3D elements:

### Available Capabilities
| Feature | Use Case |
|---------|----------|
| **Hyper3D** | Generate 3D from text: "Modern server rack with data cables" |
| **Hunyuan3D** | Generate from image + text prompt |
| **Sketchfab** | Search/download professional 3D models |
| **Poly Haven** | Free HDRIs, textures, architectural models |

### Practical Uses for Proposals
1. **3D Tech Icons**: Server, cloud, database visualizations
2. **Product Hero Images**: Custom 3D renders of proposed systems
3. **Isometric Illustrations**: Technology stack in 3D
4. **Branded Elements**: 3D Chinchilla AI logo

### Workflow
```bash
# 1. Start Blender with MCP
# 2. Use tools via Claude:
#    - search_sketchfab_models "cloud server"
#    - download, position, render
#    - get_viewport_screenshot
# 3. Embed render in mockup
```

---

## Component Library References

### Premium Animated Libraries
- **Aceternity UI** ([ui.aceternity.com](https://ui.aceternity.com)) - Framer Motion, stunning effects
- **Magic UI** - 150+ animated Shadcn components
- **Hover.dev** - Freemium, addictive interactions
- **Cult UI** - Shader lens blur, dynamic island effects

### Code Patterns from shadcn/ui
```css
/* Design token structure */
:root {
    --background: 0 0% 100%;
    --foreground: 222 47% 11%;
    --primary: 222 89% 53%;
    --primary-foreground: 0 0% 100%;
    --muted: 210 40% 96%;
    --destructive: 0 84% 60%;
    --radius: 0.5rem;
}
```

---

## Integration with Other Skills

- **proposal-writer**: Generate visuals to accompany proposals
- **architecture-diagram**: Use for technical diagram portion
- **frontend-design**: Apply design principles

## Quick Reference

```bash
# Generate screenshot from HTML
cd /Users/tori/Documents/Repos/CHI/automations
PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
node -e "require('puppeteer').launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:'new'}).then(async b=>{const p=await b.newPage();await p.setViewport({width:1440,height:1024,deviceScaleFactor:2});await p.goto('file://[HTML_PATH]');await p.waitForTimeout(500);await p.screenshot({path:'[PNG_PATH]',fullPage:true});await b.close();console.log('Done')})"

# Upload to Slack
node scripts/slack-upload.js [FILE] [CHANNEL] --title "[Title]"
```
