---
name: listing-image-workflow
description: "Full pipeline for conversion-optimized product listing images: brand context → template search → 8-dim prompt → generate → refine → carousel sequence → SEO. Use when building TikTok Shop, Shopify, or Amazon listing image sets. Keywords: product photos, listing images, carousel, shop images, product photography, e-commerce images, TikTok Shop listing."
---

# Product Listing Image Workflow

Full pipeline for generating on-brand, conversion-optimized product listing images. Covers TikTok Shop, Shopify PDP, Amazon, and e-commerce carousels.

**Execution order matters.** Each phase feeds the next. Do not skip Phase 1 — brand context and reference analysis are what separate generic outputs from brand-accurate ones.

---

## Fast Path (brand known + reference images available)

Skip Phase 2 if you have references. Run Phase 1 → 3 → 4 → 5.

```
Have references? → Phase 1 (reverse-prompt refs) → Phase 3 (build prompt) → Phase 4 (generate) → Phase 5 (refine)
No references?  → Full pipeline Phase 1→7
Single image?   → Phase 1 → 3 → 4 → 5 (skip 2, 6)
Full carousel?  → Full pipeline Phase 1→7
```

---

## Full Pipeline

```
Phase 1: Context        → creating-brand-identity + image-reverse-prompter
Phase 2: Templates      → nano-banana-pro-prompts-recommend-skill
Phase 3: Prompt Build   → nanobanana-prompt-master (8-dimension)
Phase 4: Generate       → nanobanana-mcp execute
Phase 5: Refine         → image-enhancer + iterative loop
Phase 6: Story arc      → content-master (carousel sequencing)
Phase 7: Optimize       → seo-master (filenames, alt text)
```

---

## Phase 1: Context & Reference Analysis

**Skills:** `creating-brand-identity`, `image-reverse-prompter`

1. Load brand context — color palette, tone, aesthetic references (AG1-style, UGC-native, etc.)
2. Pull 2-3 competitor or reference images for the listing type (product flat lay, lifestyle, detail shot, etc.)
3. Invoke `image-reverse-prompter` on each → extract 8-dimension prompts
4. Note: lighting setup, color palette, camera angle from each reference

**No reference images?** Describe the target aesthetic (e.g., "clean white background, studio softbox, luxury supplement brand") and go directly to Phase 3.

**Output:** Brand constraints + reverse-engineered prompts from references

---

## Phase 2: Template Lookup

**Skill:** `nano-banana-pro-prompts-recommend-skill`

Search the 13K+ library before writing from scratch. Invoke the skill, then search:
- E-commerce: keywords from `ecommerce-main-image.json`
- Lifestyle: keywords from `social-media-post.json`
- Product marketing: keywords from `product-marketing.json`

Use 2-3 keywords from your reference analysis (e.g., "supplement bottle", "white marble", "studio softbox").

**Output:** Top 3 library templates as starting points

---

## Phase 3: Prompt Engineering

**Skill:** `nanobanana-prompt-master` — invoke for full 8-dimension framework

Product-specific defaults:
- Dim 2 (Clothing): skip for product-only; include every garment for lifestyle with person
- Dim 5 (Lighting): studio softbox for e-com clean shots, golden hour for lifestyle
- Dim 6 (Camera): 85mm portrait OR 100mm macro for detail
- Dim 8 (Negatives): `wrinkled background, shadow on product face, missing label, distorted perspective` + standard quality stack

**Critical:** Negatives = plain descriptions ("blurry") — NOT negation phrases ("no blur").

**Output:** Full engineered prompt in NB Format 1 (Simple Prose)

---

## Phase 4: Generate

**Tools:** `mcp__nanobanana-mcp__set_model` → `mcp__nanobanana-mcp__set_aspect_ratio` → `mcp__nanobanana-mcp__gemini_generate_image`

| Use case | Model | Size |
|----------|-------|------|
| Iterations/testing (default) | `gemini-3.1-flash-image-preview` | `1024x1024` |
| TikTok vertical | `gemini-3.1-flash-image-preview` | `768x1344` (9:16) |
| Standard portrait listing | `gemini-3.1-flash-image-preview` | `864x1184` (3:4) |
| Final approved version | `gemini-2.5-flash-image` | match approved size |

> **Note:** `gemini-3-pro-image-preview` (Nano Banana 1) was deprecated March 9, 2026. Default to `gemini-3.1-flash-image-preview` (NB2) for all generation.

Generate 2-3 variants with different lighting setups before committing.

---

## Phase 5: Refinement Loop

**Skill:** `image-enhancer`

If generated image has issues:
1. Use `mcp__gemini-vision__gemini-analyze-image` to identify specific faults
2. Rewrite the offending dimension in the prompt
3. Regenerate with `gemini-3.1-flash-image-preview` (fast iterations)
4. Final approved version → `gemini-2.5-flash-image`

Loop: `gemini-vision (analyze faults) → Claude (rewrite dim) → nanobanana (regenerate)`

---

## Phase 6: Carousel Sequencing

**Skill:** `content-master`

### Amazon / TikTok Shop — 7-Image Emotional Frame
_Researched SOP from Chris Rawlings (Sophie Society). Use this for full listing sets._

| Slot | Type | Purpose |
|------|------|---------|
| 1 | Primary Image | White background, product fills ≥85% frame. Amazon hard rule: pure white (RGB 255,255,255). |
| 2 | Lifestyle Shot | Emotion-first — customer pictures themselves with product. Sets the desire. |
| 3 | Infographic — Main Features | 4–5 icons + short labels. Best selling points, instantly scannable. |
| 4, 5, 6 | Infographics — Various | Pick from the 20 types below based on product's objections and category. |
| 7 | Lifestyle Shot | Emotional close — reinforce transformation, not product specs. Bookends with slot 2. |

**The conversion logic:** Emotion → Logic → Emotion. Images 2 and 7 are the same *feeling*, not the same shot.

### 20 Infographic Types (choose 3 for slots 4–6)

| Type | Best for |
|------|---------|
| Main Features / Benefits | Everything — always consider this first |
| Us vs. Them Comparison | Commoditized categories, price-sensitive buyers |
| What's Included | Multi-piece products, kits, bundles |
| Different Use Cases | Versatile or multi-purpose products |
| Size Guide | Apparel, serving sizes, fit-sensitive items |
| Size Comparison | Products where scale is unclear (show next to hand/phone) |
| Guarantee / Warranty | Higher-ticket items, trust-building |
| Origin of Ingredients | Food, supplements, eco products |
| Ingredient List | Supplements, food, skincare |
| Nutrition Facts | Food and supplement products |
| Full Product Line | Cross-selling, help buyer find the right variant |
| Certifications / Badges | Health, food, beauty — USDA Organic, Non-GMO, etc. |
| How to Use / Prepare | Products with a learning curve |
| Before / After | Beauty, fitness, cleaning (check local regulations) |
| Compatibility | Accessories, tech add-ons |
| Material / Quality | Quality-sensitive categories |
| Eco-Friendliness | Sustainability-positioned brands |
| Customer Reviews / Social Proof | "4.5 Stars: 'Perfect Fit!'" — builds confidence |
| Brand Mission / Brand Story | Premium or values-driven brands |
| Other Instructions | Feeding instructions, setup, assembly |

### Text Rules for Secondary Images
- 3–5 short phrases per image — no long sentences
- Font size minimum: 20–24px body, bold headline
- High contrast: black on white or white on dark — never gray on gray
- Numbers over words: "3X faster" not "three times faster"
- Mobile-first: preview on phone before finalizing

### Style Rules
- All 6 secondary images must feel like one cohesive set (same font, grid, icon style)
- 2–3 color max: brand primary + accent + neutral
- Reference brands: Apple, Bose, Anker — clean, minimal, no clip art

**Output:** Approved carousel sequence with slot assignments and infographic types selected. Proceed to Phase 7 for SEO optimization.

---

### Shopify / TikTok Short Carousel (3–5 slides)
_Use when you don't need a full Amazon-style set._

| Slide | Purpose | Shot type |
|-------|---------|-----------|
| 1 | Hook — first impression | Hero product flat lay or lifestyle |
| 2 | Key benefit visual | Detail shot or in-use context |
| 3 | Material/quality proof | Macro texture shot |
| 4 | Social proof or claim | Text overlay base image |
| 5 | CTA | Clean product + offer |

---

## Phase 7: SEO & Delivery

**Skill:** `seo-master`

Before upload:
- Rename files: `[brand]-[product-name]-[shot-type]-[variant].jpg` (never `image_001.jpg`)
- Write alt text: descriptive, keyword-rich, no keyword stuffing
- Compress to <500KB for web without quality loss

---

## Platform Rules

### TikTok Shop
- Minimum: 500×500px
- Product must be clearly visible
- No watermarks, no text overlays (main listing image only)
- White/neutral background preferred for main image
- Text overlays allowed on carousel slides 2+

### Shopify PDP
- Minimum: 2048×2048px recommended for zoom
- Square (1:1) for consistency across grid
- White or brand-consistent background

### Amazon
- **Main image: pure white background required (RGB 255,255,255)** — hard rule, not a preference
- Minimum: 1000×1000px (zoom requirement)
- Product must fill ≥85% of the frame
- No text, logos, or watermarks on main image
- Lifestyle shots allowed on additional images

---

## Quick Reference — Key Skills

| Need | Use |
|------|-----|
| Analyze a reference image | `image-reverse-prompter` |
| Find a prompt template | `nano-banana-pro-prompts-recommend-skill` |
| Build the prompt | `nanobanana-prompt-master` |
| Fix image quality | `image-enhancer` |
| Write carousel copy | `content-master` |
| Optimize for SEO | `seo-master` |
| Brand-accurate output | `creating-brand-identity` |
| Ad creative from listing | `paid-ads` |
