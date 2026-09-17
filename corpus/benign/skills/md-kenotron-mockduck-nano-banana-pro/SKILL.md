---
name: nano-banana-pro
description: >
  Use this skill when the user wants to generate UI mockup images, analyze existing
  designs or screenshots, iterate on a design with image-to-image generation,
  combine images side-by-side for comparison, or produce an AI-annotated comparison
  image. Calls the nano-banana CLI.
allowed-tools: Bash, Read, Write
---

# nano-banana-pro (local dev)

Same as the distributed plugin skill but prefers the local build for faster iteration.

## Tool Resolution

```bash
# Prefer local build if it exists, otherwise fall back to npx
if [ -f "tools/nano-banana/dist/nano-banana.js" ]; then
  NB="node tools/nano-banana/dist/nano-banana.js"
else
  NB="npx nano-banana-pro"
fi
```

## Setup Check

```bash
echo ${GEMINI_API_KEY:+set} || echo "GEMINI_API_KEY not set"
```

If not set → `export GEMINI_API_KEY="your-key"` — get one at https://aistudio.google.com/apikey

To rebuild the local binary after source changes:
```bash
cd tools/nano-banana && bun run build.ts && cd ../..
```

---

For full command reference, see `skills/nano-banana-pro/SKILL.md` (the distributable version).

## Quick Reference

```bash
NB="node tools/nano-banana/dist/nano-banana.js"

$NB generate "<prompt>" --output <path>
$NB analyze <image> [--prompt "<question>"]
$NB generate-from <image> "<prompt>" --output <path>
$NB combine <img1> <img2> [img3] --output <path> [--gap <px>]
$NB overlay <img1> <img2> [img3] --prompt "<annotation>" --output <path> [--gap <px>]
```
