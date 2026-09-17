---
name: gemini-image-generator
description: Generate images using Google Gemini API. Use when the user asks to create, generate, or produce images, illustrations, sprites, backgrounds, or any visual assets for the game.
---

# Gemini Image Generator

Generate images using Google's Gemini API with Imagen 3 model.

## Prerequisites

1. Set your API key as environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key"
   ```

2. Or create a `.env` file in project root (add to .gitignore):
   ```
   GEMINI_API_KEY=your-api-key
   ```

## Generate Image

Use this curl command to generate images:

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{"prompt": "YOUR_PROMPT_HERE"}],
    "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
  }' | jq -r '.predictions[0].bytesBase64Encoded' | base64 -d > output.png
```

### Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `sampleCount` | 1-4 | Number of images to generate |
| `aspectRatio` | `1:1`, `3:4`, `4:3`, `9:16`, `16:9` | Image aspect ratio |

## Workflow

When user requests an image:

1. **Craft the prompt** based on HorseHeave art style:
   - Include: "cartoon style, warm colors, game asset, bright and cheerful"
   - Be specific about composition and elements

2. **Generate the image**:
   ```bash
   curl -s "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=${GEMINI_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{
       "instances": [{"prompt": "A cartoon style horse ranch barn with red roof, white fences, warm sunset colors, game asset, bright and cheerful, no text"}],
       "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
     }' | jq -r '.predictions[0].bytesBase64Encoded' | base64 -d > src/assets/images/generated_image.png
   ```

3. **Save to appropriate location**:
   - UI assets → `src/assets/images/ui/`
   - Horse sprites → `src/assets/images/horses/`
   - Buildings → `src/assets/images/buildings/`
   - Environment → `src/assets/images/environment/`

## Example Prompts for HorseHeave

### Horse Sprite
```
A cute cartoon horse, chestnut brown color, standing pose, side view, game sprite, transparent background, warm friendly style, vector art, clean lines
```

### Building
```
Cartoon style wooden horse stable building, red and brown colors, farm aesthetic, isometric view, game asset, bright daylight, no text, clean design
```

### UI Button
```
Cartoon game UI button, golden frame, green center, glossy, rounded rectangle, game asset, transparent background, no text
```

### Background
```
Peaceful horse ranch landscape, rolling green hills, blue sky with fluffy clouds, wooden fences, cartoon illustration style, warm colors, 16:9 aspect ratio, no text
```

## Troubleshooting

### "API key not valid"
- Verify GEMINI_API_KEY is set: `echo $GEMINI_API_KEY`
- Check key at https://aistudio.google.com/apikey

### "jq: command not found"
Install jq:
- macOS: `brew install jq`
- Linux: `apt install jq`

### Empty output
- Check if Imagen is available in your region
- Try the alternative Gemini 2.0 Flash model (see below)

## Alternative: Gemini 2.0 Flash (Experimental)

If Imagen is not available, use Gemini 2.0 Flash for image generation:

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Generate an image: YOUR_PROMPT_HERE"}]}],
    "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
  }' | jq -r '.candidates[0].content.parts[0].inlineData.data' | base64 -d > output.png
```
