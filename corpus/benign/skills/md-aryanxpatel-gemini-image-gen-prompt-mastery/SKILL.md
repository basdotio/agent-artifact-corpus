---
name: prompt-mastery
description: This skill should be used when the user asks to "generate an image", "create an image", "optimize a prompt", "improve my prompt", "make my prompt better", mentions "nanobanana", "image prompt", "prompt engineering for images", or needs guidance on crafting professional AI image prompts. Provides the 6 core rules from analyzing 1,186 viral prompts.
version: 1.0.0
---

# Prompt Mastery for AI Image Generation

Transform casual image descriptions into professional, high-quality prompts using patterns extracted from 1,186 viral AI-generated images.

## The 6 Core Optimization Rules

### Rule 1: Professional Terms Over Feeling Words

Replace vague aesthetic words with specific professional terminology, proper nouns, brand names, or artist names.

| Instead of... | Use... |
|---------------|--------|
| Cinematic, vintage | Wong Kar-wai aesthetics, Saul Leiter style |
| Film look, retro | Kodak Vision3 500T, Cinestill 800T |
| Warm tones | Sakura Pink, Golden Hour warmth |
| Japanese style | Wabi-sabi aesthetics, MUJI visual language |
| High-end design | Swiss International Style, Bauhaus functionalism |

**Key terminology banks:**
- **Photographers**: Annie Leibovitz, Christopher Doyle, Saul Leiter
- **Film stocks**: Kodak Vision3 500T, Cinestill 800T, Fujifilm Superia
- **Aesthetics**: Wabi-sabi, Bauhaus, Swiss International Style

### Rule 2: Quantified Parameters Over Adjectives

Replace subjective adjectives with specific technical parameters.

| Instead of... | Use... |
|---------------|--------|
| Professional looking | 90mm lens, f/1.8, high dynamic range |
| From above | 45-degree overhead angle |
| Soft lighting | Soft side backlight, diffused light |
| Blurred background | Shallow depth of field, f/1.4 bokeh |
| Dramatic | Volumetric light, chiaroscuro lighting |
| Wide shot | 16mm wide-angle lens |

### Rule 3: Negative Constraints

Explicitly state what NOT to include to prevent unwanted elements.

**Common constraints:**
- No text or words allowed
- No watermarks or logos
- No low-key dark lighting (unless intended)
- No high-saturation neon colors
- Product must not be distorted or warped
- Maintain realistic facial features

### Rule 4: Sensory Stacking

Go beyond visual descriptions by adding multiple sensory dimensions.

**Sensory layers:**
- **Visual**: Color, light, shadow, composition (baseline)
- **Tactile**: "Texture feels tangible", "Soft velvet surface"
- **Olfactory**: "Aroma penetrates the frame", "Fresh morning dew scent"
- **Motion**: "Steam wisps rising", "Fabric gently flowing"
- **Temperature**: "Steamy warmth", "Crisp cold air"

### Rule 5: Group and Cluster

For complex scenes, organize information into logical groups.

**Standard grouping pattern:**
```
[Subject Description]

Visual Style:
[Aesthetic references, color palette, artistic style]

Lighting & Atmosphere:
[Light sources, mood, environmental conditions]

Technical Parameters:
[Lens, aperture, film stock, resolution]

Constraints:
[What to avoid, what to preserve]
```

### Rule 6: Format Adaptation

Choose format based on complexity:
- **Simple scenes** (single subject): Natural language paragraphs
- **Complex scenes** (multiple elements): Structured groupings with headers

## Scene-Specific Patterns

Consult `references/scene-guide.md` for detailed patterns by scene type:
- Product Photography
- Portrait Photography
- Food Photography
- Cinematic Scenes
- Japanese Aesthetic
- Design/Poster

## Smart Genre-Based Optimization

When generating an image, follow this intelligent flow:

### Step 1: Auto-Detect Genre

Analyze the user's request and classify into one of these genres:

| Genre | Trigger Keywords |
|-------|------------------|
| `food` | dish, meal, cuisine, recipe, ingredient, cooking |
| `portrait` | person, face, woman, man, selfie, headshot |
| `product` | product, packaging, brand, commercial, advertising |
| `3d` | icon, render, 3D, isometric, emoji, character |
| `cinematic` | movie, scene, dramatic, action, poster |
| `design` | UI, app, poster, layout, typography, mockup |

### Step 2: Load Genre-Specific Patterns

Read `${CLAUDE_PLUGIN_ROOT}/data/prompts-by-category.json` and extract techniques from top prompts in that genre.

**Top techniques by genre:**
- **Food**: overhead view, macro closeup, steam visualization, warm lighting
- **Portrait**: depth of field, bokeh, skin texture detail, artificial lighting
- **Product**: centered composition, minimalist style, studio lighting, grid layouts
- **3D**: array/list format, negative constraints, white background, icon grids
- **Cinematic**: volumetric lighting, hard contrast, dramatic composition
- **Design**: minimalist style, geometric shapes, limited color palette

### Step 3: Apply the 6 Rules with Genre Context

1. **Identify genre** from user's request
2. **Load top techniques** from that genre's viral prompts
3. **Extract the core subject** they want to depict
4. **Apply Rule 1**: Replace feeling words with genre-appropriate pro terms
5. **Apply Rule 2**: Add genre-typical technical parameters
6. **Apply Rule 4**: Layer in genre-appropriate sensory descriptions
7. **Apply Rule 3**: Add genre-specific negative constraints
8. **Apply Rule 5/6**: Structure using genre's preferred format

## Quick Optimization Process (Simplified)

1. **Identify scene type** from the user's request
2. **Extract the core subject** they want to depict
3. **Apply Rule 1**: Replace feeling words with pro terms
4. **Apply Rule 2**: Add quantified technical parameters
5. **Apply Rule 4**: Layer in sensory descriptions
6. **Apply Rule 3**: Add negative constraints
7. **Apply Rule 5/6**: Structure appropriately for complexity

## Example Transformation

**User input:** "a bowl of ramen"

**Optimized output:**
```
Steaming bowl of authentic Japanese tonkotsu ramen, rich milky pork bone broth.

Visual Style:
High-end culinary magazine aesthetic. Warm earth tones with cream and amber highlights. Shot with Hasselblad medium format quality.

Composition:
45-degree overhead angle, 85mm lens, f/2.8, shallow depth of field on the soft-boiled egg.

Sensory Details:
Steam wisps rising and curling, noodles glisten with broth, chashu pork with caramelized edges, the aroma of garlic and sesame seems to penetrate the frame.

Constraints:
No utensils in frame. No text or watermarks. Maintain appetizing warm color temperature.
```

## Additional Resources

### Reference Files

For detailed patterns and terminology, consult:
- **`references/scene-guide.md`** - Scene-specific optimization patterns
- **`references/terminology.md`** - Complete professional terminology banks
- **`references/top-prompts.md`** - Top 50 viral prompts for inspiration

### Generation Script

Execute image generation:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/gen.js" "YOUR_OPTIMIZED_PROMPT"
```

## Model Information

This skill is optimized for **Gemini 3 Pro Image** (`gemini-3-pro-image`) via the antigravity-claude-proxy at `localhost:8080`.

The model excels at:
- Photorealistic imagery
- Complex scene composition
- Following detailed structured prompts
- Respecting negative constraints
