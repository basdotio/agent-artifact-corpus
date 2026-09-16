---
name: tileset-pipeline
description: "Build or review Cloverhollow 16x16 biome tilesets and atlases. Use for tile art, props, palette compliance, packing, or grid-alignment work."
compatibility: "Godot 4.5.1, locked Python/Pillow helpers, Scenario Runner"
---

# Tileset pipeline

Read `docs/art/style-lock.md`, `docs/art/palettes.md`, and the relevant biome
docs before changing art. Keep the 16x16 tile grid, nearest-neighbor pixels,
clean silhouettes, and the eight-direction naming convention in mind. Props may
be larger than one tile when the asset spec requires it.

## Workflow

1. Inspect existing assets and palette JSON before generating anything.
2. Use the actual project output path and preserve source files. Do not
   overwrite an input during quantization.
3. Use the implemented `uv run --locked` Python tools. Validation accepts
   nested `.colors` objects and flat color lists, unions repeated palettes,
   ignores RGB in fully transparent pixels, and requires an explicit asset
   size. Quantization always receives a separate output path and repeated
   `--palette` options may extend the primary palette.
4. Validate dimensions, transparency, palette membership, grid alignment, and
   readability from the generated artifact. Validate every changed asset
   explicitly; `just validate-assets` is only two selected bench samples.
5. For visual changes, run a real rendered Scenario Runner scenario, inspect
   `trace.json`, the run log, and every capture with image reading/vision.

Fail closed on missing palettes, unknown asset dimensions, tool errors, or
missing captures. The sorted packer requires same-sized frames, emits metadata,
and guards source/output collisions. Do not use blanket color quantization to
hide a palette problem. See `docs/art/verified-pipeline.md`.

For visual acceptance, use native PNG inspection and the rendered trace/diff.
If UI or dialogue text is involved, corroborate with OCR and the isolated
attachment reviewer; prior approvals and the disabled built-in vision helper are
not evidence.
