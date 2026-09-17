---
name: Brand Identity Research
description: Systematic methodology for analyzing competitor designs and developing strategic brand direction options with visual mockups
owner: Undangan team
last_updated: 2026-01-24
---

# Brand Identity Research Skill

## Purpose

This skill provides a systematic framework for conducting brand identity research when a design feels "cheap," lacks character, or needs differentiation from competitors.

## Inputs

- User feedback on what feels "cheap" or generic
- Current design URL or screenshots
- 3-5 reference URLs (same or adjacent industry)

## Outputs

- Research notes and artifacts under `.agent/artifacts/{conversation-id}/`
- 3+ strategic direction options with design DNA
- Mockups (or documented fallback) per option
- Comparison matrix and hybrid recommendation

## Prerequisites

- Ability to capture screenshots (manual or tool-based)
- Stakeholder availability for decision-making

## Tools & Availability

- `browser_subagent` for screenshots (if unavailable, capture manually)
- `generate_image` for mockups (if unavailable, document prompt + create in Figma or skip with rationale)

## When to Use

- User reports current design feels generic or template-like
- Design lacks distinct visual character
- Need to evaluate if brand identity redesign is warranted
- Want to develop strategic design direction options
- Need to make data-driven design decisions

## Methodology

### Phase 1: Problem Definition

1. **Capture User Feedback**
   - What specific words does user use? ("cheap," "generic," "template")
   - What's the emotional gap? (aspirational vs actual perception)
   - What's the business impact? (pricing perception, conversion concerns)

2. **Identify Key Questions**
   - What makes designs feel "premium" vs "cheap"?
   - What creates "distinctive character"?
   - What design patterns do memorable brands use?
   - Is current approach (color, typography, layout) sufficient?

### Phase 2: Reference Collection

1. **Request References**
   - Ask user for 3-5 landing pages they admire
   - Prioritize sites with "character" or "soul"
   - Mix of same-industry and aspirational cross-industry examples

2. **Capture Screenshots**
   - Use browser_subagent to navigate and capture
   - Get hero, features, testimonials, footer sections
   - Save with descriptive names: `{sitename}_{section}_*.png`

3. **Document Current State**
   - Capture existing design for before/after comparison
   - Focus on sections that feel weakest

### Phase 3: Pattern Analysis

For each reference, analyze:

#### Color Palette
- **Base colors:** Background and primary text
- **Accent colors:** CTAs, highlights
- **Palette size:** Single bold accent vs multi-color system
- **Emotional tone:** Warm cream vs clinical white, dark vs light
- **Specific hex codes** when visible

#### Typography
- **Font families:** Serif vs sans-serif, display vs body
- **Visual weight:** Thin/polite vs thick/bold
- **Scale:** Moderate vs massive headlines
- **Unique elements:** Handwriting, decorative fonts
- **Hierarchy patterns:** How headings relate to body

#### Layout Patterns
- **Grid structure:** Rigid vs broken/asymmetrical
- **Spacing:** Tight vs generous whitespace
- **Visual volume:** Thin borders vs thick, minimal vs maximal
- **Signature elements:** Numbered cards, badges, organic shapes

#### Texture & Depth
- **Background treatment:** Flat vs grain/texture
- **Layering:** Flat vs overlapping elements
- **Shadow/glow:** Subtle vs pronounced
- **Material cues:** Paper, glass, fabric references

#### Human Elements
- **Photography:** Real people vs illustrations vs none
- **Handmade touches:** Doodles, annotations, imperfect shapes
- **Personality signals:** Humor, warmth, playfulness markers

### Phase 4: Current Design Critique

Compare current design against reference patterns:

| Element | Current State | Reference Standard | Gap |
|---------|--------------|-------------------|-----|
| Color | Single-color, predictable | Multi-tone or bold single accent | Generic |
| Typography | Safe serif + sans | Distinctive display fonts | Forgettable |
| Layout | Template grid | Broken grid or signature pattern | Template feel |
| Texture | Flat white | Grain, paper, depth | Sterile |
| Signature | None | Unique visual hook | No character |

### Phase 5: Strategic Options Development

**Develop 3 distinct directions**, not 3 variations of the same idea:

#### Option A: Conservative/Safe
- Low implementation risk
- Market-tested patterns
- Incremental improvement from current
- **Example:** High-End Editorial (magazine aesthetic)

#### Option B: Emotional/Human
- Medium implementation risk
- Focus on warmth and connection
- Unique but potentially polarizing
- **Example:** Handcrafted/Organic (scrapbook aesthetic)

#### Option C: Disruptive/Bold
- High implementation risk
- Maximum differentiation
- May alienate conservative audience
- **Example:** Tech Brutalist (bold minimalism)

**For each option, specify:**

```markdown
### Option X: [Name]

**Inspiration:** [Reference sites]

**Design DNA:**
- Color: [Specific palette with hex codes]
- Typography: [Font recommendations]
- Signature: [Unique visual element]
- Texture: [Background/depth treatment]

**Pros:** (Rate 1-5 stars on: Premium Feel, Emotional Warmth, Memorability, Brand Fit, Context Fit, Implementation Ease)

**Cons:** (List specific risks with mitigations)

**Implementation Complexity:** 🟢 Low | 🟡 Medium | 🔴 High
```

### Phase 6: Visual Mockup Generation

**Generate mockups for each option:**

1. Use `generate_image` with detailed prompts
2. Include hero section at minimum
3. Use specific color codes, font names, and design elements
4. Balance: 70% strategic direction + 30% context-specific

**Prompt Template:**
```
A [product type] landing page hero section in "[Direction Name]" style.

Design elements:
- [Color palette with hex codes]
- [Typography specifications]
- [Layout description]
- [Unique signature elements]
- [Texture/depth cues]

Mood: [3-5 adjectives describing feeling]
```

### Phase 7: Hybrid Recommendation

**Most projects benefit from a hybrid:**

1. **Identify the strongest foundation** (usually conservative option)
2. **Add soul from emotional option** (human touches)
3. **Borrow signature from bold option** if appropriate

**Document hybrid ratio:**
```
Foundation (70%) + Soul (20%) + Signature (10%) = Strategic Hybrid
```

**Generate 2 hybrid variants:**
- Light/Day version (primary landing page)
- Dark/Evening version (premium sections or campaigns)

### Phase 8: Decision Framework

**Create a clear decision guide:**

```markdown
### Choose Option A If:
- ✅ [Business scenario]
- ✅ [Target audience characteristic]
- ✅ [Risk tolerance level]

### Choose Option B If:
- ✅ [Different scenario]
...
```

### Phase 9: Documentation

**Create comprehensive research artifact:**

1. **Executive Summary:** Problem, approach, recommendation, next step
2. **Reference Analysis:** Each site with screenshots and learnings
3. **Current Critique:** What feels cheap and why
4. **Strategic Options:** All 3+ options with mockups
5. **Comparison Matrix:** Star ratings across criteria
6. **Implementation Specs:** Color codes, font names, complexity assessment
7. **Agent Handoff:** For cross-conversation continuity

**File structure:**
```
.agent/artifacts/{conversation-id}/
  design_direction_research_notes.md  (comprehensive)
  brand_identity_research.md          (initial findings)
  brand_direction_comparison.md       (options comparison)
  {option}_mockup_*.png               (visual assets)
```

## Output Checklist

- [ ] 3+ reference sites analyzed with screenshots
- [ ] Current design critique with specific problems
- [ ] 3 distinct strategic direction options
- [ ] Visual mockups for each option (hero minimum)
- [ ] Hybrid recommendation with 2 variants
- [ ] Color palette with hex codes
- [ ] Typography specifications with font names
- [ ] Comparison matrix with star ratings
- [ ] Decision framework
- [ ] Implementation complexity assessment
- [ ] Comprehensive research notes for agent handoff

## Verification

- [ ] Artifacts stored under `.agent/artifacts/{conversation-id}/` with descriptive names
- [ ] Each option includes color palette (hex codes), typography, signature, and risks
- [ ] At least one mockup or a documented fallback per option
- [ ] Comparison matrix + decision framework present

**Pass/Fail:** Pass only if all checks above are satisfied.

## Risks & Mitigations

- Reference copying risk → extract patterns, never replicate layouts verbatim
- Overfitting to a single reference → require 3+ distinct references
- Tool unavailability → document fallbacks and constraints in outputs

## Common Pitfalls

❌ **Don't:** Develop 3 variations of the same safe direction  
✅ **Do:** Create genuinely distinct options (safe, emotional, bold)

❌ **Don't:** Use vague descriptions like "modern" or "clean"  
✅ **Do:** Specify exact hex codes, font names, element sizes

❌ **Don't:** Skip the hybrid recommendation  
✅ **Do:** Most real projects need balanced combinations

❌ **Don't:** Generate mockups without detailed prompts  
✅ **Do:** Include specific colors, fonts, moods in generate_image prompts

❌ **Don't:** Leave decision to gut feel  
✅ **Do:** Provide star-rated comparison matrix and decision framework

## Example Usage

```
User: "Our design feels cheap and generic."

Agent: 
1. Request 3-5 reference landing pages they admire
2. Use browser_subagent to capture screenshots
3. Analyze each for color/typography/layout/texture/human patterns
4. Critique current design against reference standards
5. Develop 3 distinct options (Editorial, Human, Brutalist)
6. Generate mockups for each option
7. Create hybrid combining best of 2-3 options
8. Generate 2 hybrid variants (light/dark)
9. Create comparison matrix and decision framework
10. Document in comprehensive research notes
11. Request user selection to proceed with implementation
```

## Integration with Existing Workflows

This skill works well with:
- `/design` workflow (Design context and guidelines)
- Design system documentation
- Component library development
- A/B testing planning
