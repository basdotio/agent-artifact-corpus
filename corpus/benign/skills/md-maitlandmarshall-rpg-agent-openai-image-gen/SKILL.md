---
name: openai-image-gen
description: Generate and save images/panels for Obsidian-style campaign logs and lore entries using the OpenAI Images API (gpt-image-1.5 or gpt-image-1) with OPENAI_API_KEY from .env.
---

# OpenAI Image Generation (Panels + Portraits)

Use this skill whenever the game rules require **frequent image generation** (scene panels, action shots, character portraits) and you need to **save the image to the repo** and **embed it into Markdown**.

## Quickstart

Generate a new image from text:
- `python3 .codex/skills/openai-image-gen/scripts/generate_image.py --prompt "..." --out "codex/worlds/<World>/campaigns/<Campaign>/assets/001_establishing.png"`

Generate a **scene panel** that keeps characters consistent (auto-resolves their lore reference images and uses the edits endpoint):
- `python3 .codex/skills/openai-image-gen/scripts/generate_panel.py --world <World> --character "Zorn" --character "Klik" --prompt "..." --out "codex/worlds/<World>/campaigns/<Campaign>/assets/010_squad_encounter.png"`

Generate using reference images (for visual continuity) via the edits endpoint:
- `python3 .codex/skills/openai-image-gen/scripts/generate_image.py --prompt "..." --input-image "path/to/ref1.png" --input-image "path/to/ref2.png" --out "codex/worlds/<World>/campaigns/<Campaign>/assets/002_action.png"`

Generate **multiple different images/panels in one batch** (concurrent API calls):
- Create `jobs.json`:
  - ```json
    {
      "defaults": {
        "model": "gpt-image-1.5",
        "fallback_model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "high",
        "output_format": "png"
      },
      "jobs": [
        {
          "type": "image",
          "prompt": "Foggy alleyway, wet cobblestones, neon reflections.",
          "out": "codex/worlds/<World>/campaigns/<Campaign>/assets/020_establishing.png"
        },
        {
          "type": "panel",
          "world": "<World>",
          "characters": ["Zorn", "Klik"],
          "prompt": "Wide shot: Zorn and Klik at the tunnel mouth, lantern light cutting the mist.",
          "out": "codex/worlds/<World>/campaigns/<Campaign>/assets/021_tunnel_mouth.png"
        }
      ]
    }
    ```
- Run:
  - `python3 .codex/skills/openai-image-gen/scripts/generate_batch.py --jobs jobs.json --concurrency 4`

## Embedding into logs (Obsidian-friendly)

From `campaign_logs/*.md`, embed panels like:
- `![Caption](../assets/001_establishing.png)`

## Prompting rules (to keep the world consistent)

- Use the world’s `ART_STYLE.md` “deconstructed style” keywords.
- Prefer concrete, visual descriptions (lighting, materials, camera, mood).
- For known entities: describe their consistent features + pass their existing images as `--input-image`.

## Environment

- Reads `OPENAI_API_KEY` from the environment.
- If not present, tries to load it from a repo `.env` file (simple `KEY=VALUE` parsing).

## Scripts

- `scripts/generate_image.py`: Create an image using `gpt-image-1.5` (fallback to `gpt-image-1`) and write it to disk.
- `scripts/generate_panel.py`: Wrapper that resolves lore reference images (characters) and calls `generate_image.py` with `--input-image` for visual consistency.
- `scripts/generate_batch.py`: Run many `generate_image.py`/`generate_panel.py` jobs concurrently from a JSON/JSONL manifest.
- `scripts/verify_markdown_images.py`: Verify that all image links in a Markdown file exist on disk.
