---
name: image-gen
description: Generate and edit images (生图 / 改图 / 图生图 / 商品图 / 海报) using any OpenAI-compatible image API (gpt-image and similar). Use when the user asks to generate an image, create a product/电商图, poster, logo, illustration, or to edit/modify an existing image (改图, 换背景, 加元素, 图生图), or mentions 生图, 生成图片, 画一张, gpt-image, 商品图.
---

# image-gen

Generate and edit images through any **OpenAI-compatible** image API
(`/images/generations` and `/images/edits`), e.g. a relay serving the
`gpt-image` family. Point it at your own endpoint + key via `.env`. Outputs are
downloaded locally as PNG, with a PDD/e-commerce template system and a local
gallery for viewing.

## When to use

- User wants a **new image** from a text prompt (生图 / 画一张 / 商品图 / 海报 / 插画 / logo).
- User wants to **edit an existing image** (改图 / 换背景 / 加/去掉元素 / 图生图 / 保持一致的系列图).
- User references `gpt-image` or this repo's image workflow.

## Config

Credentials live in `.env` next to this skill (`IMAGE_API_KEY`, `IMAGE_API_BASE`,
`IMAGE_MODEL`). Environment variables override the file. Never print the key.
Copy `.env.example` to `.env` and fill in your own endpoint + key.

Model ids depend on your provider — list them with `GET {API_BASE}/models`.
Common OpenAI-style ids: `gpt-image-1`, `gpt-image-2`, `gpt-image-2.5`.

## Usage

Run the helper script (paths relative to this skill directory):

```bash
# text-to-image
python3 gen.py "a cute orange cat on a wooden table, soft daylight"

# choose model / size / count
python3 gen.py "minimalist product hero shot of a ceramic mug" \
  --model gpt-image-2.5 --size 1536x1024 --n 2

# image edit / 图生图  (pass one or more --ref)
python3 gen.py "make the cat wear a red party hat" --ref cat.png

# multiple refs = character/product consistency
python3 gen.py "put this product into a summer beach scene" --ref product.png --ref bg.png

# explicit output
python3 gen.py "a logo for a tea brand" --out assets/logo.png

# PDD product image from a template (模板)
python3 gen.py "a minimalist wooden pencil holder" --template pdd-main --out product-images/
python3 gen.py "a minimalist wooden pencil holder" --template pdd-sellingpoint \
  --text "天然实木|大容量收纳|防滑底座" --out product-images/
```

The script prints the saved file path(s) on stdout (use those paths in your reply).
Add `--json` for a machine-readable result including `revised_prompt` and `usage`.

### Templates (拼多多)

`python3 gen.py --list-templates` shows all. Templates wrap the subject with a
platform-appropriate prompt and set sane defaults (size / background / quality);
any explicit CLI flag overrides the template default.

| Template | 用途 | 备注 |
|----------|------|------|
| `pdd-main` | 白底主图 | 白底居中、无文字水印，符合主图规范 |
| `pdd-scene` | 场景图 | 真实生活场景，适合详情/种草 |
| `pdd-sellingpoint` | 卖点图 | **需 `--text`**，产品 + 中文卖点标注 |
| `pdd-detail` | 详情图 | 竖向 2:3 |
| `pdd-poster` | 促销海报 | **需 `--text`**，大标题 |

Add new templates by editing `templates.json` (fields: `name`, `desc`,
`size`, `quality`, `background`, `requires_text`, `prompt_prefix`,
`prompt_suffix`). For `--text`, separate items with `|` (or `、，,;`); they are
rendered as a Chinese list.

### Presets (风格)

`python3 gen.py --list-presets` shows all. A preset adds industry/style
language and can set defaults. **Stack it with a template** — template controls
the platform format, preset controls the look:

```bash
# 3C 白底主图
python3 gen.py "a wireless earbuds charging case" --template pdd-main --preset 3c-white

# 家居场景图
python3 gen.py "a woven storage basket" --template pdd-scene --preset home

# 国潮促销海报
python3 gen.py "a ceramic tea cup gift set" --template pdd-poster --preset guochao \
  --text "国潮好物|匠心传承"
```

Presets: `3c-white`, `3c-dark`, `home`, `guochao`, `beauty`, `food`,
`apparel`, `jewelry`, `festive`. Add your own in `presets.json` (same fields as
templates, minus `requires_text`).

Default precedence: **explicit CLI flag > template > preset > built-in**.

### Options

| Flag | Meaning |
|------|---------|
| `--model` | model id (default `gpt-image-2.5`) |
| `--size` | `1024x1024` \| `1536x1024` \| `1024x1536` \| `auto` |
| `--n` | number of images |
| `--quality` | `low` \| `medium` \| `high` \| `auto` |
| `--background` | `transparent` \| `opaque` \| `auto` |
| `--template` | apply a PDD template (see `--list-templates`) |
| `--preset` | apply a style preset (see `--list-presets`) |
| `--text` | Chinese text to render (卖点/海报) |
| `--list-templates` | print available templates and exit |
| `--list-presets` | print available style presets and exit |
| `--ref FILE` | reference image → edit mode; repeat for multiple |
| `--mask FILE` | optional inpainting mask (edit mode) |
| `--out` | output file, or directory when ending in `/` |
| `--json` | emit JSON result |

Default output directory is `generated-images/` in the current working directory.

## Batch (CSV)

`batch.py` reads a CSV and generates many images in parallel, reusing the same
templates/presets, auto-naming and writing a manifest.

```bash
python3 batch.py --sample > products.csv     # starter CSV
python3 batch.py --dry-run products.csv      # preview prompts, no API calls
python3 batch.py products.csv --out product-images/ --workers 3
```

CSV columns (header required; extras ignored): `name` (required), `template`,
`preset`, `text` (separate with `|`), `model`, `size`, `quality`,
`background`, `n`, `ref` (path(s) separated by `|` → edit mode), `slug`.

- Outputs: `<out>/NNN-<slug>[-<template>][-<preset>].png`
- Manifest: `<out>/batch-manifest.csv` (row, name, template, preset, status, files, error)
- `--workers` controls parallelism (default 2 — keep modest for rate limits)
- A row can override anything via its own columns; row value wins over template/preset.
- Failing rows do not abort the batch; exit code is 1 if any row failed.

## Viewing images (local gallery)

opencode's terminal cannot render images inline, so use the bundled gallery
server to view results in a browser (this is the "image display layer"). It
serves a directory recursively and the page auto-refreshes as new images land.

```bash
# start once, keep running; then open http://localhost:8099/
python3 serve.py <images-dir> --port 8099 --open
```

- Endpoints: `/` gallery, `/api/list` JSON index, `/img?p=<rel>` full image, `/thumb?p=<rel>` thumbnail.
- The page polls every 2.5s, so generate while it is open and new images pop in.
- `--open` launches the Windows browser from WSL (`explorer.exe`).
- Thumbnails use Pillow if installed (`pip install Pillow`); otherwise full images are served.
- Path traversal is blocked; only image extensions are listed.

## Notes

- Responses return an **image URL** (not b64); the script downloads it for you.
- The API is billed per token (image tokens dominate). Check `usage` if needed.
- For a consistent series, reuse the same `--ref` image(s) across calls.
- If a call fails, surface the relay's error text; do not retry blindly.
