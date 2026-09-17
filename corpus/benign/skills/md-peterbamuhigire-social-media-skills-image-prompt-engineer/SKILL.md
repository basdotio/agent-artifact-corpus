---
name: image-prompt-engineer
description: Teaches practitioners to write AI image prompts that produce professional, art-directed visuals using the Eight-Layer Prompt Anatomy — not the over-smooth, uncanny, obviously-AI aesthetic. Invoke when a client or the agency needs to generate images using Midjourney, DALL-E, Stable Diffusion, Flux, or Adobe Firefly, and the output must meet the Golden Rule: images that look like they were shot or designed by a skilled human creative.
---

# AI Image Prompt Engineering

## Required Input

Ask for the following before generating any image prompts:

1. **Client business name** — the exact trading name used publicly
2. **Industry** — e.g. financial services, hospitality, retail, professional services
3. **Country/city** — default: Uganda/Kampala
4. **Primary goal** — what the image is for: social media post, website hero, campaign visual, product showcase
5. **Platform** — which AI image tool will be used: Midjourney, DALL-E 3, Stable Diffusion, Flux, Adobe Firefly
6. **Brand visual anchors** — primary colour palette, photographic tone (warm/cool/neutral), and whether the brand is people-centric, product-centric, or environment-centric
7. **Subject matter** — describe who or what should be in the image, including nationality, age, setting, and any required cultural context

---

## The Golden Rule

AI images carry a distinctive aesthetic: over-smooth skin, slightly off proportions, hyperrealistic fantasy-realist lighting, and symmetrical perfection. The goal is to produce images that look art-directed, stylistically intentional, and culturally accurate — not AI-generated.

This requires precision in prompting, not more prompts. One precisely constructed prompt using all eight layers produces better output than ten vague attempts.

---

## The Eight-Layer Image Prompt Anatomy

*Source: LetsEnhance (2024) How to Write AI Image Prompts — From Basic to Pro*

Every prompt must address all eight layers. Leaving a layer at its default produces a generic AI aesthetic.

---

### Layer 1 — Subject

The primary focus. Be specific: not "a woman" but "a Ugandan businesswoman in her late 30s, wearing a tailored navy suit, standing confidently at a modern office window."

For East African clients: always specify nationality, city, and context explicitly. AI defaults to Western settings and Western physical appearances. "African" is not sufficient — specify the country, city, and contemporary context.

---

### Layer 2 — Environment

Where the scene is set. Not "office" but "a glass-walled conference room in a Kampala high-rise building, late afternoon, city skyline visible."

For EA clients: specify that clothing is contemporary urban or professional unless traditional dress is specifically required. AI frequently applies culturally inaccurate dress without explicit instruction.

---

### Layer 3 — Lighting

The single most powerful element for photographic realism. Always specify both quality and direction.

Options: natural window light, golden hour, overcast diffused light, dramatic side lighting, studio soft box, practical lamp light.
Direction: from the left, from behind, from above, front-lit, rim-lit.

Example: "soft natural light from a large window to the left, creating gentle shadows on the right side."

---

### Layer 4 — Colours

The palette. Specify: warm earthy tones, desaturated pastels, bold primary colours, monochromatic blue-grey, high contrast black and white.

Translate the client's brand palette directly into this layer. For EA clients: skin tone rendering accuracy depends on explicit instruction — specify "true-to-life skin tones for East African subjects" to reduce AI tendency toward over-lightening or over-darkening.

---

### Layer 5 — Mood

The emotional register. Not a feeling but an atmosphere: confident and aspirational, intimate and warm, urgent and dynamic, calm and authoritative, celebratory and energetic.

Mood directs the AI's choices for expression, posture, and colour saturation. State it explicitly.

---

### Layer 6 — Composition

Camera framing. Specify: close-up portrait, wide establishing shot, overhead flat lay, rule-of-thirds framing, Dutch angle, eye-level perspective, over-the-shoulder shot.

For social media: specify the aspect ratio context — portrait (9:16 for Stories/Reels), square (1:1 for grid posts), landscape (16:9 for covers).

---

### Layer 7 — Style

The visual aesthetic. Specify a photography style (editorial fashion photography, documentary street photography, clean product photography), a medium (digital illustration, watercolour, pencil sketch, 3D render), or reference a known visual language without naming a specific photographer to avoid copyright issues.

Example: "the visual aesthetic of high-end African fashion editorial photography" — not "shot in the style of [specific photographer's name]."

---

### Layer 8 — Technical Parameters

Platform-specific specifications:

| Platform | Key Parameters |
|---|---|
| Midjourney | `--ar 9:16` (aspect ratio), `--v 6` (version), `--seed 12345` (reproducibility), `--style raw` (less AI-filtered output) |
| DALL-E 3 | "photorealistic, ultra-high resolution, DSLR photograph" — describe the full scene in a clear sentence |
| Stable Diffusion | Negative prompt field essential; ControlNet for pose and composition control; attention weighting for emphasis |
| Flux | Specify camera type and lens; token-efficient prompts; detail and realism engine |
| Adobe Firefly | Built-in commercial use rights; include "Adobe Stock style" for clean, licensable outputs |

---

## The Negative Prompt Library

Include exclusion language to suppress the AI aesthetic. Apply to all platforms that support a negative prompt field.

**Universal negative prompt:**
`blurry, distorted proportions, extra fingers, deformed hands, uncanny valley effect, overly smooth skin, plastic appearance, wax figure aesthetic, AI-generated aesthetic, overexposed highlights, neon oversaturation, fantasy lighting, watermark, signature, text overlay, low resolution, jpeg artifacts`

**Add for images of people:**
`emotionless expression, doll-like features, exaggerated proportions, inappropriate cultural stereotypes, culturally inaccurate dress, Western default appearance`

**Apply in platform-specific ways:**
- Midjourney: append `--no [list]` at the end of the prompt
- Stable Diffusion: paste into the dedicated negative prompt field
- DALL-E 3: incorporate as "avoid" instructions in the scene description
- Flux: include as explicit exclusions in the prompt text

---

## Brand Visual Identity Translation Protocol

1. Identify the brand's three visual anchors: primary colour palette, photographic tone (warm/cool/neutral), and subject type (people-centric / product-centric / environment-centric)
2. Translate each anchor into the relevant layer: colours → Layer 4; photographic tone → Layer 7; subject type → Layer 1
3. Use seed numbers (Midjourney `--seed`) to maintain visual consistency across a campaign
4. Document the seed number and full prompt for every approved image — this is the visual consistency record

---

## Cultural Accuracy in East African Image Prompts

The BuzzFeed Barbie study (2023) documented that AI produced culturally stereotyped and racially inaccurate imagery even with an explicit diversity brief. For East African clients:

- Specify nationality, context, and setting explicitly in Layer 1 and Layer 2 — never rely on "African" as a descriptor
- Specify clothing as contemporary urban/professional unless traditional dress is specifically required
- Specify "East African urban professional" or "Ugandan business context" — not generic "African business"
- Always review images of people with a human reviewer who has direct cultural knowledge before client delivery
- Any image that contains culturally inaccurate representation is rejected and re-prompted, regardless of other quality

---

## Full Prompt Construction Example

**Brief:** A social media post for a Kampala financial services firm, showing a professional consultation scene.

**Constructed prompt (Midjourney):**
```
A Ugandan male financial advisor in his early 40s, wearing a well-fitted charcoal grey suit,
seated across a desk from a Ugandan woman client in her 30s wearing a smart yellow dress,
in a clean modern office in Kampala, glass-walled, city view in the background,
soft natural light from large windows to the left, warm golden tones,
mood: trustworthy and professional, eye-level medium shot, rule of thirds,
editorial corporate photography style, true-to-life East African skin tones,
sharp focus, high detail --ar 4:5 --v 6 --seed 44821 --style raw
--no blurry, plastic skin, fantasy lighting, Western default appearance, text overlay, watermark
```

---

## Platform-Specific Quick Reference

| Platform | Strength | Key syntax |
|---|---|---|
| Midjourney | Artistic quality, style range | `--ar`, `--v 6`, `--seed`, `--style raw` |
| DALL-E 3 | Natural language, accuracy | Full scene description; include "photorealistic" for photos |
| Stable Diffusion | Control, customisation | Negative prompt field essential; ControlNet for pose control |
| Flux | Detail and realism | Specify camera type and lens; token-efficient prompts |
| Adobe Firefly | Commercial licensing | Built-in commercial use rights; "Adobe Stock style" for clean outputs |

---

## Quality Criteria

Good output from this skill meets all of the following standards:

- All eight prompt layers are addressed — no layer left at default or unspecified
- Negative prompt included for all platforms that support it, using the universal library plus any people-specific exclusions
- Cultural accuracy review completed by a human reviewer with direct knowledge of the depicted community before client delivery
- Seed number or reference image documented for every approved image, ensuring campaign consistency across multiple assets
- Image reviewed against the brand's three visual anchors (colour palette, photographic tone, subject type) before delivery
- Platform-appropriate aspect ratio and technical parameters specified correctly for the intended use
- Output reviewed against the Golden Rule — any image that looks generically AI-generated is rejected and re-prompted

---

## References

- LetsEnhance (2024) *How to Write AI Image Prompts — From Basic to Pro*. LetsEnhance.io.
- BuzzFeed (2023) — AI image cultural accuracy study: "Barbie" diversity brief findings.
