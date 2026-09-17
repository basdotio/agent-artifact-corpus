---
name: creating-staticmap-maps
description: "Use when generating static map images with the Python `staticmap` library — embedding isochrone or drive-time polygon maps in Word (.docx) reports, placing facility or location markers over polygon fills using PIL, sizing maps for page layout, or debugging CircleMarker visibility, `m.transformer` AttributeErrors, or coordinate conversion failures. Triggers on: trade area map, isochrone map, drive-time map, map image too large, legend pushed to next page, markers not appearing, blank page in docx."
---

# Creating Staticmap Maps

## Overview

Covers generating a static map with the `staticmap` library, manually drawing visible markers and labels with PIL after `m.render()`, embedding the map in a Word document at the correct size, and embedding the legend inside the image so no separate legend paragraph is needed.

## Required Tools

This skill requires the following tools at runtime:
- **staticmap** — Tile-based static map rendering (`pip install staticmap`)
- **Pillow (PIL)** — Manual marker and legend drawing after `m.render()` (`pip install Pillow`)
- **python-docx** — Embedding the final map image in a Word document (`pip install python-docx`)

**Before starting**: Verify that `staticmap`, `Pillow`, and `python-docx` are installed. If any are unavailable, STOP and inform the user which step cannot proceed. Do NOT silently substitute plain-image output for docx embedding.

---

## Critical Pitfalls (Read First)

### 1. `CircleMarker` is invisible under polygon fills

**Problem**: `staticmap.CircleMarker` is composited *below* `Polygon` fills. If you add isochrone polygons (even with low alpha like `#FF000030`), any `CircleMarker` added via `m.add_marker()` will be invisible underneath them.

**Never do this:**
```python
m.add_marker(CircleMarker((lon, lat), "#FF0000", 14))  # INVISIBLE under polygons
```

**Fix**: Do NOT call `m.add_marker()` at all. Draw markers manually with PIL *after* `m.render()`, so they appear on top of everything.

---

### 2. `m.transformer` does not exist

**Problem**: The `StaticMap` object never exposes a `.transformer` attribute at any point. Code like `m.transformer.lng_to_x(lon)` always raises `AttributeError`.

**Fix**: Import and use the module-level `_lon_to_x` and `_lat_to_y` functions directly, combined with the instance methods `m._x_to_px()` and `m._y_to_px()`. These instance attributes (`m.zoom`, `m.x_center`, `m.y_center`, `m.tile_size`) are only available **after** `m.render()` is called.

```python
from staticmap.staticmap import _lon_to_x, _lat_to_y

def latlon_to_pixel(lat, lon):
    """Convert geographic coordinates to pixel (x, y) on the rendered image."""
    try:
        tile_x = _lon_to_x(lon, m.zoom)
        tile_y = _lat_to_y(lat, m.zoom)
        px = m._x_to_px(tile_x)
        py = m._y_to_px(tile_y)
        return int(px), int(py)
    except Exception:
        return None, None

# IMPORTANT: call m.render() BEFORE calling latlon_to_pixel
img = m.render()
px, py = latlon_to_pixel(lat, lon)
```

---

### 3. Map aspect ratio controls page layout

**Problem**: `StaticMap(1000, 1400)` produces a 1000×1400 image. At `width=Inches(6.5)` in a Word document, the image renders as 6.5" wide × 9.1" tall — leaving only 0.4" on the page for any heading or legend, which spills to the next page and creates a blank page.

**Rule of thumb for 8.5×11" pages with 0.75" margins (9.5" usable height):**

| Image dimensions | Insert width | Rendered height | Fits with heading? |
|---|---|---|---|
| 1000 × 1400 | 6.5" | 9.1" | ❌ No — legend on next page |
| 1000 × 1200 | 6.5" | 7.8" | ✅ Barely |
| 1000 × 1000 | 5.5" | 5.5" | ✅ Yes — room for heading + caption |
| 1000 × 800  | 5.5" | 4.4" | ✅ Yes |

**Recommended default:** `StaticMap(1000, 1000)` inserted at `Inches(5.5)`.

---

## Reference Implementation

```python
from staticmap import StaticMap, Polygon as SMPolygon
from staticmap.staticmap import _lon_to_x, _lat_to_y
from PIL import Image, ImageDraw, ImageFont

SUBJ_LAT, SUBJ_LON = 48.2215, -122.6853

def generate_map(iso_polys, facilities):
    """Static map: isochrone polygons + manually drawn markers + embedded legend."""

    # ── 1. Build StaticMap with square aspect ratio ──────────────────────────
    m = StaticMap(1000, 1000,
                  url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")

    # ── 2. Add isochrone polygons (DO NOT add CircleMarkers here) ────────────
    colors  = {20: "#FF880030", 15: "#0000FF30", 10: "#00AA0030", 5: "#FF000030"}
    outlines = {20: "#FF8800",  15: "#0000FF",   10: "#00AA00",  5: "#FF0000"}

    for mins in [20, 15, 10, 5]:
        if mins not in iso_polys:
            continue
        poly = iso_polys[mins]
        geoms = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
        for geom in geoms:
            sm_coords = [(lon, lat) for lon, lat in geom.exterior.coords]
            m.add_polygon(SMPolygon(sm_coords,
                                    fill_color=colors[mins],
                                    outline_color=outlines[mins],
                                    simplify=True))

    # ── 3. Render the base image (sets m.zoom, m.x_center, m.y_center) ───────
    img = m.render()
    draw = ImageDraw.Draw(img)

    # ── 4. Load fonts (fallback to default if Arial unavailable) ─────────────
    try:
        font      = ImageFont.truetype("arial.ttf", 13)
        font_sm   = ImageFont.truetype("arial.ttf", 11)
        font_leg  = ImageFont.truetype("arial.ttf", 11)
    except (OSError, IOError):
        font = font_sm = font_leg = ImageFont.load_default()

    # ── 5. Coordinate conversion (only valid after render) ───────────────────
    def latlon_to_pixel(lat, lon):
        try:
            tile_x = _lon_to_x(lon, m.zoom)
            tile_y = _lat_to_y(lat, m.zoom)
            return int(m._x_to_px(tile_x)), int(m._y_to_px(tile_y))
        except Exception:
            return None, None

    # ── 6. Draw subject marker (red circle, white border) ────────────────────
    SUBJ_R = 12
    px, py = latlon_to_pixel(SUBJ_LAT, SUBJ_LON)
    if px is not None:
        draw.ellipse([(px - SUBJ_R, py - SUBJ_R), (px + SUBJ_R, py + SUBJ_R)],
                     fill="#FF0000", outline="#FFFFFF", width=3)
        draw.text((px + SUBJ_R + 6, py - 8), "Subject", fill="#CC0000", font=font)

    # ── 7. Draw competitor markers (blue circles, white border) ──────────────
    COMP_R = 8
    for f in facilities:
        if f.get("is_subject"):
            continue
        px, py = latlon_to_pixel(f["lat"], f["lon"])
        if px is not None:
            draw.ellipse([(px - COMP_R, py - COMP_R), (px + COMP_R, py + COMP_R)],
                         fill="#0044FF", outline="#FFFFFF", width=2)
            label = f["name"].split(" ")[0]
            draw.text((px + COMP_R + 5, py - 6), label, fill="#002266", font=font_sm)

    # ── 8. Embedded legend (inside the image, bottom-left) ───────────────────
    legend_items = [
        ("#FF0000", "● Subject Property"),
        ("#0044FF", "● Competitor Facility"),
        ("#FF0000", "■ 5-min Primary"),
        ("#00AA00", "■ 10-min Secondary"),
        ("#0000FF", "■ 15-min Tertiary"),
        ("#FF8800", "■ 20-min Extended"),
    ]
    legend_y = img.height - 120
    draw.rectangle(
        [(10, legend_y - 5),
         (250, legend_y + len(legend_items) * 18 + 5)],
        fill="#FFFFFFEE", outline="#666666")
    for i, (color, label) in enumerate(legend_items):
        draw.text((18, legend_y + i * 18 - 1), label, fill=color, font=font_leg)

    img.save("gold_map.png")
    return "gold_map.png"
```

---

## Embedding in Word

```python
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Insert map at 5.5" width — image is square so height = 5.5", fits on page
doc.add_picture("gold_map.png", width=Inches(5.5))
last_p = doc.paragraphs[-1]
last_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

# Attribution only — legend is already inside the image
caption = doc.add_paragraph()
caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = caption.add_run(
    "Basemap: OpenStreetMap  |  "
    "Routing: Valhalla public demo (valhalla1.openstreetmap.de)")
run.font.size = Pt(8)
run.italic = True
```

---

## Verification Checklist

After generating the map image, verify markers are visible with numpy:

```python
from PIL import Image
import numpy as np

img = Image.open("gold_map.png")
arr = np.array(img)
map_h = int(img.height * 0.85)  # top 85% = map area, bottom 15% = legend

# Subject marker: exact red (255,0,0)
red = (arr[:map_h,:,0] == 255) & (arr[:map_h,:,1] == 0) & (arr[:map_h,:,2] == 0)
print(f"Red pixels in map area: {red.sum()}")  # expect > 100

# Competitor markers: dark blue near (0,68,255)
blue = (arr[:map_h,:,0]<20) & (arr[:map_h,:,1]>40) & (arr[:map_h,:,1]<100) & (arr[:map_h,:,2]>220)
print(f"Blue pixels in map area: {blue.sum()}")  # expect > 100 per competitor
```

**Expected passing values**: each circular marker (radius 8–12px) contains ~100–300 filled pixels. If the map-area count is 0, the coordinate conversion failed.

---

## How `staticmap` Coordinate Conversion Works

After `m.render()`, the instance has:
- `m.zoom` — integer tile zoom level chosen automatically
- `m.x_center`, `m.y_center` — tile-space center of the map
- `m.tile_size` — pixel size of one tile (default: 256)

Conversion pipeline:
```
(lat, lon)
  → _lon_to_x(lon, m.zoom) / _lat_to_y(lat, m.zoom)   # geographic → tile numbers
  → m._x_to_px(tile_x) / m._y_to_px(tile_y)            # tile numbers → pixel coords
  → (px, py)                                             # pixel position on image
```

The module-level formulas:
```python
# Longitude → tile x
x = ((lon + 180.0) / 360.0) * 2**zoom

# Latitude → tile y  (Mercator projection)
y = (1 - log(tan(lat * pi/180) + 1/cos(lat * pi/180)) / pi) / 2 * 2**zoom

# Tile → pixel
px = (tile_x - m.x_center) * m.tile_size + m.width  / 2
py = (tile_y - m.y_center) * m.tile_size + m.height / 2
```

---

## Polygon Color Format

`staticmap` accepts hex colors for fill and outline. The fill alpha is part of the 8-character hex string:

```python
"#FF000030"   # Red fill, ~19% opacity  (30 hex = 48 decimal / 255 ≈ 0.19)
"#00AA0060"   # Green fill, ~38% opacity
"#FF0000"     # Red outline, fully opaque (6-char = no alpha)
```

Keep fill alpha low (20–50 hex) so markers and basemap roads remain visible beneath the overlay.

---

## Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `AttributeError: 'StaticMap' object has no attribute 'transformer'` | Old code pattern; `transformer` never existed | Use `_lon_to_x` / `_lat_to_y` from `staticmap.staticmap` |
| Markers invisible on map | `CircleMarker` renders below polygon fills | Draw markers with `draw.ellipse()` after `m.render()` |
| `AttributeError: m.zoom` (or `m.x_center`) | `latlon_to_pixel` called before `m.render()` | Always call `img = m.render()` before any pixel conversion |
| Map pushes legend to next page | Image too tall for page | Use square image (1000×1000) at `Inches(5.5)` |
| Blank page 3 in docx | Same as above | Reduce image height; embed legend inside image |
| Marker labels overlap | Facilities too close together | Abbreviate labels to first word only; offset text by marker radius + 5px |
