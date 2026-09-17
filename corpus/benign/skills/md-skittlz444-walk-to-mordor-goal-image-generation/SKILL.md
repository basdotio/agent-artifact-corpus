---
name: Goal Image Generation
description: Process for generating watercolour-style images for goals in the Walk to Mordor application. Use when asked to create or update an image for a specific goal.
---

# Goal Image Generation Process

This workflow guides the process of generating a watercolour-style image for a specific goal in the Walk to Mordor application.

## Pre-requisites

- Access to the `generate_image` tool for image generation
- Access to reference images for style adherence:
  - `public/img/highres/2.jpg` - Bridge with warm golden light
  - `public/img/highres/21.jpg` - Dark hooded figures, moody atmosphere
  - `public/img/highres/28.jpg` - Rider in forest, soft edges
  - `public/img/highres/30.jpg` - Elven ruins, misty atmosphere
  - `public/img/highres/56.jpg` - Dark cave, dramatic lighting
- Access to `migrations/0003_init_goals.sql` for goal reference
- Access to `.github/skills/goal-description-update/resources/goal-description-reference.md` for milestone context

---

## Step 1: Identify the Target Goal

1. Determine which goal the user wants to generate an image for.
   - If the user provides a name or approximate location, search `migrations/0003_init_goals.sql` to find the matching goal.
   - You need the **Distance** value to uniquely identify the goal.
2. Once identified, record:
   - Goal Distance (e.g., `241`)
   - Goal Title (e.g., "Attacked by Nazgul on Amon Sûl (Weathertop)")
   - Goal Description (from latest migration files)
   - The goal title/distance immediately BEFORE this one
   - The goal title/distance immediately AFTER this one
3. Check the goal's current `image_id` value to determine if this is a new image or replacement.

---

## Step 2: Identify Anchoring Milestones

1. Open the reference document (`.github/skills/goal-description-update/resources/goal-description-reference.md`).
2. Consult the **Book Milestones** section.
3. Identify:
   - The milestone that occurs DIRECTLY BEFORE the target goal
   - The milestone that occurs DIRECTLY AFTER the target goal
4. Note the Book Reference (e.g., "Book 1, Ch 11") for research purposes.

---

## Step 3: Research LOTR Context (Sub-Agent)

> **IMPORTANT**: Use a sub-agent for this step to keep context clean and avoid influencing prompt generation with unrelated information.
> **NOTE**: If sub-agents are not available, perform this research directly but be mindful of context size.

Provide the sub-agent with:
1. The **Target Goal's** distance, title, and description
2. The anchoring milestones (before and after)
3. The book chapter reference

**Sub-agent prompt template:**
```
Research the Lord of the Rings narrative context for a specific goal location.

GOAL INFORMATION:
- Distance: [DISTANCE VALUE]
- Title: [GOAL TITLE]
- Description: [GOAL DESCRIPTION]

BOOK CONTEXT:
- Previous milestone: [MILESTONE BEFORE] (Book ref: [BOOK REFERENCE])
- Next milestone: [MILESTONE AFTER] (Book ref: [BOOK REFERENCE])

RESEARCH REQUIREMENTS:
Gather detailed information about THIS EXACT location in the narrative:

1. TERRAIN & GEOGRAPHY:
   - What does the landscape look like here? (hills, forests, rivers, mountains, plains, marshes)
   - What specific geographic features are mentioned in the books?
   - What is the vegetation like?

2. STRUCTURES & LANDMARKS:
   - Are there any buildings, ruins, or landmarks at this location?
   - What architectural style would be appropriate (Elven, Dwarven, Númenórean, etc.)?

3. ATMOSPHERE & MOOD:
   - What is the emotional tone at this point in the story? (hope, dread, wonder, weariness, urgency)
   - What time of day is it?
   - What is the weather like?
   - Is there any magical or supernatural presence?

4. CHARACTERS PRESENT:
   - Who EXACTLY is present at this location at this time?
   - Before Breaking of Fellowship (1309 miles): Which Fellowship members are present?
   - After Breaking: Is it Frodo/Sam/Gollum or the Three Hunters or another group?
   - Verify against book chapters - do NOT include characters who are not present

5. KEY VISUAL ELEMENTS:
   - What specific visual moments from the book could be depicted?
   - Are there any distinctive colours or lighting conditions mentioned?

Return a structured summary with all findings. Cite book passages where possible.
If uncertain about any detail, indicate uncertainty rather than guessing.
```

---

## Step 4: Build Image Prompt (Sub-Agent)

> **IMPORTANT**: Use a sub-agent for prompt construction to maintain clean context and ensure the prompt is focused solely on this goal.

Provide the sub-agent with:
1. The research findings from Step 3
2. The style reference information (below)
3. Clear instructions on prompt structure

**Sub-agent prompt template:**
```
Build an image generation prompt for a watercolour painting of a Lord of the Rings location.

LOCATION RESEARCH:
[INSERT RESEARCH FINDINGS FROM STEP 3]

STYLE REQUIREMENTS:
Create a prompt for a watercolour painting with these characteristics:
- Watercolour painting in the style of Alan Lee and John Howe
- Wet-on-wet technique with soft diffused edges
- Visible brushwork and organic texture
- Atmospheric perspective (misty backgrounds, depth through colour desaturation)
- Traditional watercolour on textured paper appearance
- Warm/cool colour contrast where appropriate
- Limited, harmonious colour palette (not overly saturated)
- Dramatic lighting appropriate to the scene:
  * For bright scenes: strong light sources, atmospheric glow
  * For dark scenes: subtle light sources, deep shadows, ambient glow
- Small figures in landscape (not character portraits) if characters are included

PROMPT STRUCTURE:
Build the prompt in this order:
1. STYLE PREFIX: "Watercolour painting, wet-on-wet technique, soft diffused edges, visible brushwork, atmospheric perspective, textured paper, in the style of Alan Lee and John Howe,"
2. SCENE DESCRIPTION: Specific terrain, structures, landmarks from research
3. ATMOSPHERE: Mood, weather, time of day, lighting conditions
4. CHARACTERS (if appropriate): Small figures in landscape, described by clothing/silhouette not faces
5. TECHNICAL SUFFIX: "High detail, museum quality, square format, no text, no watermarks, no borders"

CONSTRAINTS:
- Maximum prompt length: 200 words
- Do NOT include anything not verified in the research
- Do NOT include characters who are not present at this location
- Focus on the landscape and atmosphere, characters are secondary
- Match the mood to the narrative moment

Return ONLY the complete prompt text, nothing else.
```

---

## Step 5: Validate Prompt (Sub-Agent)

> **IMPORTANT**: Use a sub-agent to validate the prompt before generation. This ensures narrative accuracy.

Provide the sub-agent with:
1. The generated prompt from Step 4
2. The original goal information
3. The research findings

**Sub-agent prompt template:**
```
Validate this image generation prompt for narrative accuracy.

PROMPT TO VALIDATE:
[INSERT PROMPT FROM STEP 4]

ORIGINAL GOAL:
- Distance: [DISTANCE]
- Title: [GOAL TITLE]
- Book milestone before: [MILESTONE]
- Book milestone after: [MILESTONE]

RESEARCH FINDINGS:
[INSERT RESEARCH FROM STEP 3]

VALIDATION CHECKLIST:

1. CHARACTER ACCURACY:
   - Are ONLY characters who are actually present at this location mentioned?
   - If before Moria (798 miles): Is Gandalf included appropriately?
   - If after Moria but before Lothlórien (855 miles): Is Gandalf excluded?
   - If after Breaking of Fellowship (1309 miles): Are the correct characters for this path included?
   - Check goal description and online sources for specific character presence

2. GEOGRAPHIC ACCURACY:
   - Does the terrain match both book descriptions AND the goal description?
   - Are the structures/landmarks appropriate for this location?
   - Is the architectural style correct (Elven, Dwarven, Hobbit, Gondorian, etc.)?

3. TEMPORAL ACCURACY:
   - Does the lighting match the time of day in the narrative?
   - Does the weather match what's described?
   - Does the season/vegetation match the journey timeline?

4. MOOD ACCURACY:
   - Does the atmosphere match the narrative tension at this point?
   - Is the colour palette appropriate (dark/foreboding vs bright/hopeful)?

5. ANACHRONISMS:
   - Is there anything in the prompt that wouldn't exist at this location in Middle-earth?
   - Are there any modern elements or out-of-place details?

RESPONSE FORMAT:
If the prompt passes all checks, respond with:
VALID: [original prompt unchanged]

If the prompt needs corrections, respond with:
INVALID: [list of issues]
CORRECTED PROMPT: [fixed prompt]
```

---

## Step 6: Generate Images

Once the prompt is validated, generate the images using the `generate_image` tool.

### High-Resolution Image
1. Use the validated prompt
2. Generate at 1024x1024 pixels (current generator limit)
3. Upscale to 2560x2560 using the script:
   - Script: `.github/skills/goal-image-generation/resources/resize-webp.js`
   - Example: `node .github/skills/goal-image-generation/resources/resize-webp.js public/img/highres/[slug].webp public/img/highres/[slug].webp --width 2560 --height 2560 --quality 90 --upscale --targetKB 0`
4. Pass reference images for style adherence:
   - `d:\GitHub\walk-to-mordor\public\img\highres\2.jpg`
   - `d:\GitHub\walk-to-mordor\public\img\highres\30.jpg`
   - `d:\GitHub\walk-to-mordor\public\img\highres\28.jpg`
   (Maximum 3 reference images)

### Thumbnail Image
After generating the high-res image:
1. Generate from the high-res image or use a downscaling script
   - Script: `.github/skills/goal-image-generation/resources/resize-webp.js`
   - Example: `node .github/skills/goal-image-generation/resources/resize-webp.js public/img/highres/[slug].webp public/img/thumbs/[slug]-thumb.webp --max 400 --targetKB 20 --quality 60`
2. Maximum dimension: 400px
3. Quality: 60
4. Target size: <20KB

### File Naming
Use descriptive slugs based on the goal:
- Format: `[location-or-event-slug]`
- Examples: `weathertop-attack`, `moria-gates`, `shelob-lair`, `bucklebury-ferry`
- Avoid numbers-only names

### File Locations
- High-res: `public/img/highres/[slug].webp`
- Thumbnail: `public/img/thumbs/[slug]-thumb.webp`

### Post-Generation Verification
1. Verify high-res file size is <25MB
2. Verify thumbnail file size is <20KB
3. Verify dimensions are correct
4. Visual check: Does the style match reference images?

---

## Step 7: Update Database

Create a migration file to update the goal's `image_id`:

1. Determine the next available migration number by checking the `migrations/` folder.
2. Create the migration file:

**File Name:** `migrations/00XX_update_image_[slug].sql`

**File Content:**
```sql
-- Migration number: 00XX    [TIMESTAMP]

-- Update image_id for goal: [GOAL TITLE] (Distance: [DISTANCE])
UPDATE goals SET image_id = '[slug]' WHERE distance = [DISTANCE] * 1.60934;
```

**Example:**
```sql
-- Migration number: 0025    2026-01-21T20:30:00.000Z

-- Update image_id for goal: Attacked by Nazgul on Amon Sûl (Weathertop) (Distance: 241)
UPDATE goals SET image_id = 'weathertop-attack' WHERE distance = 241 * 1.60934;
```

---

## Notes

- The sub-agent isolation for research, prompt building, and validation is critical to prevent context pollution and ensure accuracy
- When in doubt about narrative details, consult online LOTR resources rather than guessing
- The watercolour style should be consistent with the reference images - atmospheric, soft edges, dramatic but not overly detailed
- Characters should be small figures in the landscape, not portrait-style close-ups
- The mood of the image should match the emotional tone of that point in the journey

---

## Quick Reference: Character Locations

| Journey Segment | Characters Present |
|-----------------|-------------------|
| 0-842 miles (Shire to Moria exit) | Full Fellowship (9 members) |
| 842-855 miles (After Gandalf falls) | Fellowship minus Gandalf (8 members) |
| 855-930 miles (Lothlórien) | Fellowship minus Gandalf (8 members) |
| 930-1309 miles (River journey) | Fellowship minus Gandalf (8 members) |
| 1309-1779 miles (Frodo/Sam path) | Frodo, Sam, Gollum |
| 1779-1899 miles (Post-Ring) | Frodo, Sam (later reunite with others) |
| 1899+ miles (Return journey) | Varies - all four hobbits typically |

> **IMPORTANT**: This is a general guide. Always verify against the specific goal's description and book references for exact character presence.
