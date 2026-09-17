# Add Case Study Skill

## When to Use
When user wants to add a new case study to the portfolio.

## Prerequisites
- Case study content (problem, solution, results)
- At least one hero image
- Stats/metrics for the stats section

## Steps

### 1. Create MDX File
Location: `src/content/caseStudies/{slug}.md`

### 2. Required Frontmatter
```yaml
---
title: "Short title for cards"
pageTitle: "Full title shown on page"
seoTitle: "SEO optimized title | Jitan Gupta"
summary: "2-3 sentence summary for preview cards"
description: "SEO description 150-160 chars"
pubDate: "YYYY-MM-DD"
heroImage: "/images/{image-name}.png"
articleTag: "Category"
stats:
  - percentage: "XX%"
    description: "What this metric means"
keywords: "keyword1, keyword2, long-tail keyword"
author: "Jitan Gupta"
robots: "index, follow"
ogType: "article"
canonicalUrl: "https://jitangupta.com/case-studies/{slug}/"
---
```

### 3. Content Structure
- Use ## for main sections
- Use ### for subsections
- Include code blocks with language specifier
- Add images with descriptive alt text

### 4. Voice & Tone
- Warm, approachable — senior colleague energy
- Lead with the problem, show the solution, prove with numbers
- Avoid: "guru", "expert", "master", "consultant"
- Use: "real patterns", "what actually worked", "production-tested"

### 5. Color Classes (v2.0)
- Buttons: `bg-primary-600 hover:bg-primary-700` (cerulean blue)
- Accent links: `text-accent-500` (orange)
- Page bg: `bg-[#F8FAFC]`
- Do NOT use: `bg-secondary-*`, `text-secondary-*` (deleted)

### 6. Verify
```bash
npm run build
# Check for TypeScript/content errors
```

### 7. Test Locally
```bash
npm run dev
# Visit http://localhost:4321/case-studies/{slug}
```
