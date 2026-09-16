---
name: gemini-imagegen
description: Generate and edit images using Gemini API (Nano Banana Pro). Supports text-to-image, image editing, multi-turn refinement, Google Search grounding for factual accuracy, and composition from multiple reference images.
---

# Gemini Image Generation (Nano Banana Pro)

Generate professional-quality images using Google's **Gemini 3 Pro Image** model (aka Nano Banana Pro). The environment variable `GEMINI_API_KEY` must be set.

## Model

**gemini-3-pro-image-preview** (Nano Banana Pro)
- Resolution: Up to 4K (1K, 2K, 4K)
- Built on Gemini 3 Pro with advanced reasoning and real-world knowledge
- Best for: Professional assets, illustrations, diagrams, text rendering, product mockups
- Features: Google Search grounding, automatic "Thinking" process for refined composition

## Quick Start Scripts

CRITICAL FOR AGENTS: These are executable scripts in your PATH. All scripts now default to **gemini-3-pro-image-preview**.

### Text-to-Image
```bash
scripts/generate_image.py "A technical diagram showing microservices architecture" output.png
```

### Edit Existing Image
```bash
scripts/edit_image.py diagram.png "Add API gateway component with arrows showing data flow" output.png
```

### Multi-Turn Chat (Iterative Refinement)
```bash
scripts/multi_turn_chat.py
```

For high-resolution technical diagrams:
```bash
scripts/generate_image.py "Your prompt" output.png --size 4K --aspect 16:9
```

## Core API Pattern

All image generation uses the `generateContent` endpoint with `responseModalities: ["TEXT", "IMAGE"]`:

```python
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Your prompt here"],
)

for part in response.parts:
    if part.text:
        print(part.text)
    elif part.inline_data:
        image = part.as_image()
        image.save("output.png")
```

## Image Configuration Options

Control output with `image_config`:

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",  # 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
            image_size="4K"       # 1K, 2K, 4K (Nano Banana Pro supports up to 4K)
        ),
    )
)
```

## Editing Images

Pass existing images with text prompts:

```python
from PIL import Image

img = Image.open("input.png")
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Add a sunset to this scene", img],
)
```

## Multi-Turn Refinement

Use chat for iterative editing:

```python
from google.genai import types

chat = client.chats.create(
    model="gemini-3-pro-image-preview",
    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
)

response = chat.send_message("Create a logo for 'Acme Corp'")
# Save first image...

response = chat.send_message("Make the text bolder and add a blue gradient")
# Save refined image...
```

## Prompting Best Practices

### Core Prompt Structure
Keep prompts concise and specific. Research shows prompts under 25 words achieve **30% higher accuracy**. Structure as:

**Subject + Adjectives + Action + Location/Context + Composition + Lighting + Style**

### Photorealistic Scenes
Include camera details: lens type, lighting, angle, mood.
> "Photorealistic close-up portrait, 85mm lens, soft golden hour light, shallow depth of field"

### Stylized Art
Specify style explicitly:
> "Kawaii-style sticker of a happy red panda, bold outlines, cel-shading, white background"

### Text in Images
Be explicit about font style and placement:
> "Logo with text 'Daily Grind' in clean sans-serif, black and white, coffee bean motif"

### Product Mockups
Describe lighting setup and surface:
> "Studio-lit product photo on polished concrete, three-point softbox setup, 45-degree angle"

### Technical Diagrams
Be explicit about positions, relationships, and labels:
> "Technical diagram: Component A at top, Component B at bottom. Arrow from A to B labeled 'HTTP GET'. Clean boxes, directional arrows, white background."

## Advanced Features

### Google Search Grounding
Generate images based on real-time data:

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Visualize today's weather in Tokyo as an infographic"],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        tools=[{"google_search": {}}]
    )
)
```

### Multiple Reference Images (Up to 14)
Combine elements from multiple sources:

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[
        "Create a group photo of these people in an office",
        Image.open("person1.png"),
        Image.open("person2.png"),
        Image.open("person3.png"),
    ],
)
```

## REST API (curl)

```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Technical diagram showing RESTful API architecture"}]}]
  }' | jq -r '.candidates[0].content.parts[] | select(.inlineData) | .inlineData.data' | base64 --decode > output.png
```

## Notes

- All generated images include SynthID watermarks
- Image-only mode (`responseModalities: ["IMAGE"]`) won't work with Google Search grounding
- For editing, describe changes conversationally—the model understands semantic masking
- Be specific about positions, colors, labels, and relationships for best results
