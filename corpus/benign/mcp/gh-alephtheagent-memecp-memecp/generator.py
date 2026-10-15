"""Meme generation engine supporting classic, demotivator, post-ironic, caption, and news styles."""

from __future__ import annotations

import io
import math
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageFilter, ImageSequence

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_CACHE_DIR = Path("~/.hermes/cache/memes").expanduser()
DEFAULT_FONT_CACHE_DIR = Path("~/.cache/memecp/fonts").expanduser()

FONT_ALIASES: dict[str, str] = {
    "impact": "impact.ttf",
    "futura": "futura_condensed.otf",
    "caption": "futura_condensed.otf",
    "esmbot": "futura_condensed.otf",
    "ifunny": "futura_condensed.otf",
    "lobster": "lobster.ttf",
    "oswald": "oswald.ttf",
    "serif": "serif.ttf",
    "times": "serif.ttf",
    "times new roman": "serif.ttf",
    "sans": "sans.ttf",
    "arial": "sans.ttf",
    "helvetica": "sans.ttf",
}

SYSTEM_FONTS: dict[str, str] = {
    "sans.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "serif.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
}

FONT_DOWNLOAD_URLS: dict[str, list[str]] = {
    "impact.ttf": [
        "https://raw.githubusercontent.com/justrajdeep/fonts/master/Impact.ttf",
    ],
    "futura_condensed.otf": [
        "https://raw.githubusercontent.com/Kyles-World/Futura-Font/main/Futura%20PT%20(ParaType)/FuturaPTCond-Bold.otf",
    ],
    "caption.otf": [
        "https://raw.githubusercontent.com/esmBot/esmBot/master/assets/fonts/caption.otf",
    ],
    "lobster.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lobster/Lobster-Regular.ttf",
    ],
    "oswald.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    ],
    "serif.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserif/NotoSerif%5Bwdth%2Cwght%5D.ttf",
    ],
    "sans.ttf": [
        "https://raw.githubusercontent.com/HikiNarou/DejavuSans-TTF/master/DejaVuSans-Bold.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
    ],
}


@dataclass
class LoadedMedia:
    """Container for loaded media frames, animation state, and playback metadata."""
    is_animated: bool
    frames: list[Image.Image]
    durations: list[int]
    loop: int
    width: int
    height: int


def list_available_fonts() -> list[str]:
    """Return a list of available built-in font identifiers."""
    names = set(FONT_ALIASES.keys())
    if DEFAULT_FONT_CACHE_DIR.exists():
        for p in DEFAULT_FONT_CACHE_DIR.glob("*.*"):
            if p.suffix.lower() in (".ttf", ".otf"):
                names.add(p.stem.lower())
    if ASSETS_DIR.exists():
        for p in ASSETS_DIR.glob("*.*"):
            if p.suffix.lower() in (".ttf", ".otf"):
                names.add(p.stem.lower())
    return sorted(names)


def download_font(target_filename: str) -> Path | None:
    """Download a required font on demand into local cache directory."""
    urls = FONT_DOWNLOAD_URLS.get(target_filename, [])
    if not urls:
        return None

    DEFAULT_FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DEFAULT_FONT_CACHE_DIR / target_filename

    for url in urls:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    target_path.write_bytes(resp.content)
                    # Verify font validity
                    ImageFont.truetype(str(target_path), 20)
                    return target_path
        except Exception:
            continue
    return None


def resolve_font_path(font_name_or_path: str) -> Path:
    """
    Resolve a font alias, local file path, or download on demand.
    Keeps repository clean and DMCA-safe.
    """
    # 1. Direct path check
    direct = Path(font_name_or_path).expanduser()
    if direct.exists() and direct.is_file():
        return direct

    # 2. Alias lookup
    normalized = font_name_or_path.strip().lower()
    filename = FONT_ALIASES.get(normalized, normalized)
    if not filename.endswith((".ttf", ".otf")):
        filename = f"{filename}.ttf"

    # 3. Cache directory check (~/.cache/memecp/fonts/)
    cached_path = DEFAULT_FONT_CACHE_DIR / filename
    if cached_path.exists() and cached_path.is_file() and cached_path.stat().st_size > 1000:
        return cached_path

    # 4. In-repo assets directory check (if present locally)
    asset_file = ASSETS_DIR / filename
    if asset_file.exists() and asset_file.is_file() and asset_file.stat().st_size > 1000:
        return asset_file

    # 5. Host system font check
    if filename in SYSTEM_FONTS:
        sys_path = Path(SYSTEM_FONTS[filename])
        if sys_path.exists() and sys_path.is_file():
            return sys_path

    # 6. On-demand download
    downloaded = download_font(filename)
    if downloaded and downloaded.exists():
        return downloaded

    # 7. Fallback search across available cached fonts or system fonts
    for fallback_file in ("impact.ttf", "futura_condensed.otf", "sans.ttf", "serif.ttf"):
        fc = DEFAULT_FONT_CACHE_DIR / fallback_file
        if fc.exists() and fc.is_file() and fc.stat().st_size > 1000:
            return fc
        fa = ASSETS_DIR / fallback_file
        if fa.exists() and fa.is_file() and fa.stat().st_size > 1000:
            return fa

    for sys_fallback in SYSTEM_FONTS.values():
        sp = Path(sys_fallback)
        if sp.exists() and sp.is_file():
            return sp

    raise FileNotFoundError(f"Could not resolve font '{font_name_or_path}' and all fallbacks failed.")


def load_font(font_name_or_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a truetype/opentype font at the specified size with on-demand retrieval."""
    try:
        font_path = resolve_font_path(font_name_or_path)
        return ImageFont.truetype(str(font_path), max(10, int(size)))
    except Exception:
        # Graceful fallback to any working font or Pillow default
        for candidate in [
            DEFAULT_FONT_CACHE_DIR / "sans.ttf",
            DEFAULT_FONT_CACHE_DIR / "impact.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]:
            if candidate.exists() and candidate.is_file():
                try:
                    return ImageFont.truetype(str(candidate), max(10, int(size)))
                except Exception:
                    continue
        return ImageFont.load_default()


def _prepare_frame(frame: Image.Image, max_dimension: int) -> Image.Image:
    """Convert frame to RGB (compositing alpha on white) and downscale if max dimension exceeded."""
    if frame.mode in ("RGBA", "LA") or (frame.mode == "P" and "transparency" in frame.info):
        alpha_img = frame.convert("RGBA")
        background = Image.new("RGBA", alpha_img.size, (255, 255, 255, 255))
        composed = Image.alpha_composite(background, alpha_img)
        rgb_frame = composed.convert("RGB")
    elif frame.mode != "RGB":
        rgb_frame = frame.convert("RGB")
    else:
        rgb_frame = frame.copy()

    w, h = rgb_frame.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        rgb_frame = rgb_frame.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return rgb_frame


def load_media(
    image_source: str,
    max_dimension: int = 1920,
    max_gif_frames: int = 120,
) -> LoadedMedia:
    """
    Load an image or animated GIF from a local path or HTTP(S) URL.
    Preserves animated GIF frames, durations, and loop settings.
    """
    if not image_source:
        raise ValueError("image_source must not be empty.")

    source_lower = image_source.strip().lower()
    if source_lower.startswith(("http://", "https://")):
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(image_source)
            resp.raise_for_status()
            image_data = resp.content
        bio = io.BytesIO(image_data)
        img = Image.open(bio)
    else:
        path = Path(image_source).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local image file not found: {path}")
        img = Image.open(path)

    is_animated = bool(getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1)

    if not is_animated:
        prepared = _prepare_frame(img, max_dimension)
        return LoadedMedia(
            is_animated=False,
            frames=[prepared],
            durations=[100],
            loop=0,
            width=prepared.width,
            height=prepared.height,
        )

    # Animated GIF processing
    loop = int(img.info.get("loop", 0))
    raw_frames: list[Image.Image] = []
    durations: list[int] = []

    for frame in ImageSequence.Iterator(img):
        dur = int(frame.info.get("duration", 100) or 100)
        if dur <= 10:
            dur = 100
        durations.append(dur)
        raw_frames.append(_prepare_frame(frame, max_dimension))

    if not raw_frames:
        prepared = _prepare_frame(img, max_dimension)
        return LoadedMedia(
            is_animated=False,
            frames=[prepared],
            durations=[100],
            loop=0,
            width=prepared.width,
            height=prepared.height,
        )

    # Gracefully sample if GIF has excessive frame count (> max_gif_frames)
    if len(raw_frames) > max_gif_frames:
        step = math.ceil(len(raw_frames) / max_gif_frames)
        sampled_frames: list[Image.Image] = []
        sampled_durations: list[int] = []
        for i in range(0, len(raw_frames), step):
            sampled_frames.append(raw_frames[i])
            sampled_durations.append(sum(durations[i : min(i + step, len(durations))]))
        raw_frames = sampled_frames
        durations = sampled_durations

    return LoadedMedia(
        is_animated=True,
        frames=raw_frames,
        durations=durations,
        loop=loop,
        width=raw_frames[0].width,
        height=raw_frames[0].height,
    )


def load_image(image_source: str, max_dimension: int = 1920) -> Image.Image:
    """Load an image from a local path or HTTP(S) URL and convert to RGB (first frame if animated)."""
    media = load_media(image_source, max_dimension=max_dimension)
    return media.frames[0]


def resolve_output_path(output_path: str | None, prefix: str = "meme", is_gif: bool = False) -> Path:
    """Resolve or generate an output file path with automatic GIF/JPG extension handling."""
    ext = ".gif" if is_gif else ".jpg"
    if output_path:
        out = Path(output_path).expanduser().resolve()
        if is_gif and out.suffix.lower() not in (".gif", ""):
            out = out.with_suffix(".gif")
        elif not out.suffix:
            out = out.with_suffix(ext)
        out.parent.mkdir(parents=True, exist_ok=True)
        return out

    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_id = uuid.uuid4().hex[:8]
    return DEFAULT_CACHE_DIR / f"{prefix}_{ts}_{rand_id}{ext}"


def save_media_result(
    frames: list[Image.Image],
    durations: list[int],
    loop: int,
    output_path: str | None,
    prefix: str,
    is_animated: bool,
    quality: int = 95,
) -> tuple[Path, int, int]:
    """Save processed frames as static image or animated GIF with clean palette quantization."""
    destination = resolve_output_path(output_path, prefix=prefix, is_gif=is_animated)

    if is_animated and len(frames) > 1:
        p_frames = [f.convert("P", palette=Image.ADAPTIVE) for f in frames]
        p_frames[0].save(
            destination,
            format="GIF",
            save_all=True,
            append_images=p_frames[1:],
            duration=durations,
            loop=loop,
            disposal=2,
            optimize=False,
        )
    elif is_animated and len(frames) == 1:
        p_frame = frames[0].convert("P", palette=Image.ADAPTIVE)
        p_frame.save(
            destination,
            format="GIF",
            save_all=True,
            duration=durations[0] if durations else 100,
            loop=loop,
        )
    else:
        out_format = destination.suffix.lstrip(".").upper()
        if out_format in ("JPG", "JPEG"):
            frames[0].save(destination, format="JPEG", quality=quality)
        else:
            frames[0].save(destination, quality=quality)

    return destination, frames[0].width, frames[0].height


def wrap_text_to_width(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-wrap text into lines so each line fits within max_width."""
    lines: list[str] = []
    paragraphs = text.splitlines() or [""]

    for paragraph in paragraphs:
        cleaned = paragraph.strip()
        if not cleaned:
            lines.append("")
            continue

        words = cleaned.split()
        cur_line: list[str] = []

        for word in words:
            candidate = " ".join(cur_line + [word])
            bbox = draw.textbbox((0, 0), candidate, font=font)
            line_w = bbox[2] - bbox[0]

            if line_w <= max_width:
                cur_line.append(word)
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                    cur_line = [word]
                else:
                    # Single word is wider than max_width: break word character by character
                    part = ""
                    for ch in word:
                        test_part = part + ch
                        bbox_part = draw.textbbox((0, 0), test_part, font=font)
                        if (bbox_part[2] - bbox_part[0]) <= max_width or not part:
                            part = test_part
                        else:
                            lines.append(part)
                            part = ch
                    if part:
                        cur_line = [part]

        if cur_line:
            lines.append(" ".join(cur_line))

    return lines


def calculate_multiline_box(lines: list[str], font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, line_spacing: int = 4) -> tuple[int, int]:
    """Calculate total bounding width and height for wrapped lines."""
    if not lines:
        return 0, 0

    max_w = 0
    total_h = 0
    for i, line in enumerate(lines):
        if not line:
            bbox = draw.textbbox((0, 0), "A", font=font)
            h = bbox[3] - bbox[1]
        else:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_w = max(max_w, w)
        total_h += h
        if i > 0:
            total_h += line_spacing

    return max_w, total_h


def fit_text(
    text: str,
    font_name: str,
    target_width: int,
    max_height: int,
    initial_font_size: int,
    min_font_size: int = 16,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Iteratively size down font until wrapped text fits within max_height."""
    temp_img = Image.new("RGB", (100, 100))
    temp_draw = ImageDraw.Draw(temp_img)

    size = initial_font_size
    while size >= min_font_size:
        font = load_font(font_name, size)
        lines = wrap_text_to_width(text, font, target_width, temp_draw)
        _, total_h = calculate_multiline_box(lines, font, temp_draw, line_spacing=int(size * 0.15))
        if total_h <= max_height or size <= min_font_size:
            return font, lines
        size = max(min_font_size, size - 3)

    font = load_font(font_name, min_font_size)
    lines = wrap_text_to_width(text, font, target_width, temp_draw)
    return font, lines


def create_classic_meme(
    image_source: str,
    top_text: str = "",
    bottom_text: str = "",
    font_name: str = "impact",
    font_size: int = 0,
    stroke_width: int = 0,
    text_color: str = "white",
    stroke_color: str = "black",
    all_caps: bool = True,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a classic meme with white text and black outline (Impact font by default).
    Automatically wraps lines, auto-scales font size, and supports animated GIFs.
    """
    media = load_media(image_source)
    w, h = media.width, media.height

    max_text_w = int(w * 0.92)
    max_section_h = int(h * 0.38)
    base_font_size = font_size if font_size > 0 else max(24, int(w * 0.085))

    # Pre-render text overlay onto transparent canvas to composite across frames
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Process top text
    if top_text.strip():
        txt = top_text.upper() if all_caps else top_text
        if font_size <= 0:
            f_top, lines_top = fit_text(txt, font_name, max_text_w, max_section_h, base_font_size)
        else:
            f_top = load_font(font_name, font_size)
            lines_top = wrap_text_to_width(txt, f_top, max_text_w, draw)

        top_stroke = stroke_width if stroke_width > 0 else max(2, int(f_top.size * 0.065))
        line_spacing = int(f_top.size * 0.15)
        _, total_top_h = calculate_multiline_box(lines_top, f_top, draw, line_spacing)

        cur_y = int(h * 0.03)
        for line in lines_top:
            if line:
                draw.text(
                    (w / 2, cur_y),
                    line,
                    font=f_top,
                    fill=text_color,
                    stroke_width=top_stroke,
                    stroke_fill=stroke_color,
                    anchor="ma",
                )
            bbox = draw.textbbox((0, 0), line or "A", font=f_top)
            cur_y += (bbox[3] - bbox[1]) + line_spacing

    # Process bottom text
    if bottom_text.strip():
        txt = bottom_text.upper() if all_caps else bottom_text
        if font_size <= 0:
            f_bot, lines_bot = fit_text(txt, font_name, max_text_w, max_section_h, base_font_size)
        else:
            f_bot = load_font(font_name, font_size)
            lines_bot = wrap_text_to_width(txt, f_bot, max_text_w, draw)

        bot_stroke = stroke_width if stroke_width > 0 else max(2, int(f_bot.size * 0.065))
        line_spacing = int(f_bot.size * 0.15)
        _, total_bot_h = calculate_multiline_box(lines_bot, f_bot, draw, line_spacing)

        cur_y = h - int(h * 0.03) - total_bot_h
        for line in lines_bot:
            if line:
                draw.text(
                    (w / 2, cur_y),
                    line,
                    font=f_bot,
                    fill=text_color,
                    stroke_width=bot_stroke,
                    stroke_fill=stroke_color,
                    anchor="ma",
                )
            bbox = draw.textbbox((0, 0), line or "A", font=f_bot)
            cur_y += (bbox[3] - bbox[1]) + line_spacing

    has_text = bool(top_text.strip() or bottom_text.strip())
    output_frames: list[Image.Image] = []
    for frame in media.frames:
        if has_text:
            frame_rgba = frame.convert("RGBA")
            composed = Image.alpha_composite(frame_rgba, overlay).convert("RGB")
            output_frames.append(composed)
        else:
            output_frames.append(frame)

    destination, out_w, out_h = save_media_result(
        frames=output_frames,
        durations=media.durations,
        loop=media.loop,
        output_path=output_path,
        prefix="classic",
        is_animated=media.is_animated,
    )

    return {
        "success": True,
        "path": str(destination),
        "width": out_w,
        "height": out_h,
    }


def create_demotivator(
    image_source: str,
    title: str,
    subtitle: str = "",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a classic Russian 2007 demotivator frame:
    - Pure black background
    - Thin white rectangular border around original image
    - Large centered serif title
    - Smaller explanatory serif subtitle
    Supports static images and animated GIFs.
    """
    media = load_media(image_source)
    orig_w, orig_h = media.width, media.height

    margin_x = max(36, int(orig_w * 0.09))
    margin_top = max(36, int(orig_h * 0.08))
    canvas_w = orig_w + 2 * margin_x

    # Font sizing
    title_size = max(26, int(orig_w * 0.065))
    font_title, lines_title = fit_text(
        title,
        font_name="serif",
        target_width=int(canvas_w * 0.88),
        max_height=int(orig_h * 0.35),
        initial_font_size=title_size,
        min_font_size=18,
    )

    temp_img = Image.new("RGB", (100, 100))
    temp_draw = ImageDraw.Draw(temp_img)
    _, title_h = calculate_multiline_box(lines_title, font_title, temp_draw, line_spacing=int(font_title.size * 0.15))

    lines_sub: list[str] = []
    sub_h = 0
    font_sub = None
    if subtitle.strip():
        sub_size = max(14, int(font_title.size * 0.46))
        font_sub, lines_sub = fit_text(
            subtitle,
            font_name="serif",
            target_width=int(canvas_w * 0.88),
            max_height=int(orig_h * 0.25),
            initial_font_size=sub_size,
            min_font_size=12,
        )
        _, sub_h = calculate_multiline_box(lines_sub, font_sub, temp_draw, line_spacing=int(font_sub.size * 0.15))

    gap_img_to_title = max(24, int(orig_h * 0.055))
    gap_title_to_sub = max(12, int(orig_h * 0.025)) if subtitle.strip() else 0
    margin_bottom = max(36, int(orig_h * 0.085))

    canvas_h = (
        margin_top
        + orig_h
        + gap_img_to_title
        + title_h
        + gap_title_to_sub
        + sub_h
        + margin_bottom
    )

    base_canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    draw = ImageDraw.Draw(base_canvas)

    # Thin white border around image (offset by 4px)
    border_gap = 4
    border_rect = [
        margin_x - border_gap,
        margin_top - border_gap,
        margin_x + orig_w + border_gap - 1,
        margin_top + orig_h + border_gap - 1,
    ]
    draw.rectangle(border_rect, outline=(255, 255, 255), width=2)

    # Draw Title
    cur_y = margin_top + orig_h + gap_img_to_title
    line_spacing_title = int(font_title.size * 0.15)
    for line in lines_title:
        if line:
            draw.text((canvas_w / 2, cur_y), line, font=font_title, fill=(255, 255, 255), anchor="ma")
        bbox = draw.textbbox((0, 0), line or "A", font=font_title)
        cur_y += (bbox[3] - bbox[1]) + line_spacing_title

    # Draw Subtitle
    if subtitle.strip() and font_sub:
        cur_y = margin_top + orig_h + gap_img_to_title + title_h + gap_title_to_sub
        line_spacing_sub = int(font_sub.size * 0.15)
        for line in lines_sub:
            if line:
                draw.text((canvas_w / 2, cur_y), line, font=font_sub, fill=(230, 230, 230), anchor="ma")
            bbox = draw.textbbox((0, 0), line or "A", font=font_sub)
            cur_y += (bbox[3] - bbox[1]) + line_spacing_sub

    # Paste each frame onto base canvas
    output_frames: list[Image.Image] = []
    for frame in media.frames:
        canvas = base_canvas.copy()
        canvas.paste(frame, (margin_x, margin_top))
        output_frames.append(canvas)

    destination, out_w, out_h = save_media_result(
        frames=output_frames,
        durations=media.durations,
        loop=media.loop,
        output_path=output_path,
        prefix="demotivator",
        is_animated=media.is_animated,
    )

    return {
        "success": True,
        "path": str(destination),
        "width": out_w,
        "height": out_h,
    }


def create_caption_meme(
    image_source: str,
    caption: str,
    font_name: str = "futura",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate an esmBot / Discord / iFunny style white header caption box meme:
    - Pure white rectangular header box placed above the image
    - Bold geometric sans typography (Futura Condensed Bold / Extra Bold)
    - Perfectly centered horizontally and vertically
    - Clean proportional padding
    Supports static images and animated GIFs.
    """
    media = load_media(image_source)
    w, h = media.width, media.height

    # Prominent geometric font sizing
    base_font_size = max(24, int(w * 0.072))
    min_font_size = max(14, int(w * 0.032))
    pad_x = max(18, int(w * 0.04))
    max_box_text_w = w - 2 * pad_x
    max_box_h = int(h * 0.50)

    temp_img = Image.new("RGB", (100, 100))
    temp_draw = ImageDraw.Draw(temp_img)

    selected_font = None
    selected_lines: list[str] = []
    selected_spacing = 0

    # Auto-scale font down if caption is long
    for size in range(base_font_size, min_font_size - 1, -2):
        f = load_font(font_name, size)
        lines = wrap_text_to_width(caption, f, max_box_text_w, temp_draw)
        spacing = max(3, int(size * 0.15))
        _, text_h = calculate_multiline_box(lines, f, temp_draw, spacing)
        pad_y = max(14, int(size * 0.42))
        if text_h + 2 * pad_y <= max_box_h and len(lines) <= 4:
            selected_font = f
            selected_lines = lines
            selected_spacing = spacing
            break

    if not selected_font:
        selected_font = load_font(font_name, min_font_size)
        selected_spacing = max(3, int(min_font_size * 0.15))
        selected_lines = wrap_text_to_width(caption, selected_font, max_box_text_w, temp_draw)

    _, text_h = calculate_multiline_box(selected_lines, selected_font, temp_draw, selected_spacing)
    pad_y = max(14, int(selected_font.size * 0.42))
    box_h = text_h + 2 * pad_y

    # Pre-render the header box ONCE
    header_img = Image.new("RGB", (w, box_h), (255, 255, 255))
    header_draw = ImageDraw.Draw(header_img)
    cur_y = pad_y
    for line in selected_lines:
        if line:
            header_draw.text((w / 2, cur_y), line, font=selected_font, fill=(0, 0, 0), anchor="ma")
        bbox = header_draw.textbbox((0, 0), line or "A", font=selected_font)
        cur_y += (bbox[3] - bbox[1]) + selected_spacing

    canvas_h = h + box_h
    output_frames: list[Image.Image] = []
    for frame in media.frames:
        canvas = Image.new("RGB", (w, canvas_h), (255, 255, 255))
        canvas.paste(header_img, (0, 0))
        canvas.paste(frame, (0, box_h))
        output_frames.append(canvas)

    destination, out_w, out_h = save_media_result(
        frames=output_frames,
        durations=media.durations,
        loop=media.loop,
        output_path=output_path,
        prefix="caption",
        is_animated=media.is_animated,
    )

    return {
        "success": True,
        "path": str(destination),
        "width": out_w,
        "height": out_h,
    }


def create_post_ironic_meme(
    image_source: str,
    caption: str,
    style: str = "caption_box",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate post-ironic and modern meme styles:
    - 'caption_box': White rectangular header box above image (esmBot / iFunny format).
    - 'deep_fry': Nuked meme with hyper-saturation, sharpness, contrast, and JPEG compression artifacts.
    - 'bottom_ticker': Breaking news ticker overlay at the bottom.
    Supports static images and animated GIFs.
    """
    norm_style = style.strip().lower()

    if norm_style in ("caption_box", "top_box", "ifunny", "esmbot", "caption"):
        return create_caption_meme(image_source=image_source, caption=caption, output_path=output_path)

    elif norm_style in ("bottom_ticker", "news_ticker", "breaking_news"):
        return create_news_meme(image_source=image_source, headline=caption, output_path=output_path)

    elif norm_style in ("deep_fry", "fried", "nuked"):
        source_to_fry = image_source
        temp_created = None
        if caption.strip():
            temp_res = create_classic_meme(
                image_source=image_source,
                top_text=caption,
                all_caps=True,
                font_name="impact",
            )
            source_to_fry = temp_res["path"]
            temp_created = temp_res["path"]

        try:
            media = load_media(source_to_fry)
            output_frames: list[Image.Image] = []

            for frame in media.frames:
                fry_img = frame.copy()
                # 1. Extreme saturation
                fry_img = ImageEnhance.Color(fry_img).enhance(2.8)
                # 2. Extreme contrast
                fry_img = ImageEnhance.Contrast(fry_img).enhance(2.2)
                # 3. Extreme sharpness
                fry_img = ImageEnhance.Sharpness(fry_img).enhance(3.5)
                # 4. First heavy JPEG compression pass
                buf = io.BytesIO()
                fry_img.save(buf, format="JPEG", quality=15)
                buf.seek(0)
                fry_img = Image.open(buf).convert("RGB")

                # 5. Red/yellow color temperature bias
                r, g, b = fry_img.split()
                r = r.point(lambda i: min(255, int(i * 1.2 + 10)))
                b = b.point(lambda i: max(0, int(i * 0.85 - 10)))
                fry_img = Image.merge("RGB", (r, g, b))

                # 6. Second JPEG compression pass
                buf2 = io.BytesIO()
                fry_img.save(buf2, format="JPEG", quality=18)
                buf2.seek(0)
                result_img = Image.open(buf2).convert("RGB")
                output_frames.append(result_img)

            destination, out_w, out_h = save_media_result(
                frames=output_frames,
                durations=media.durations,
                loop=media.loop,
                output_path=output_path,
                prefix="post_deep_fry",
                is_animated=media.is_animated,
                quality=25,
            )

            return {
                "success": True,
                "path": str(destination),
                "width": out_w,
                "height": out_h,
            }
        finally:
            if temp_created:
                try:
                    os.remove(temp_created)
                except OSError:
                    pass

    else:
        raise ValueError(f"Unknown post-ironic style: '{style}'. Supported: 'caption_box', 'deep_fry', 'bottom_ticker'.")


def create_news_meme(
    image_source: str,
    headline: str,
    category: str = "⚡ СРОЧНО",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a breaking news broadcast ticker overlay on the bottom of the image.
    Uses two-tier TV lower-third layout with dynamic font scaling and multiline spacing:
    - Tier 1: Red category strip with category badge and live broadcast indicator
    - Tier 2: Dark lower-third bar sized dynamically to fit all headline lines without clipping
    Supports static images and animated GIFs.
    """
    media = load_media(image_source)
    w, h = media.width, media.height

    # Tier 1: Top Category Strip
    badge_font_size = max(14, int(w * 0.024))
    badge_font = load_font("sans", badge_font_size)
    strip_h = max(28, int(badge_font_size * 1.75))

    # Tier 2: Lower-third Headline Box
    pad_x = max(20, int(w * 0.035))
    pad_y = max(14, int(h * 0.024))
    max_text_w = w - 2 * pad_x
    max_total_ticker_h = int(h * 0.38)
    max_headline_box_h = max_total_ticker_h - strip_h - 2 * pad_y

    base_font_size = max(20, int(w * 0.040))
    min_font_size = max(13, int(w * 0.022))

    temp_img = Image.new("RGB", (100, 100))
    temp_draw = ImageDraw.Draw(temp_img)

    selected_font = None
    selected_lines: list[str] = []
    selected_spacing = 0

    # Auto-scale font size: step down until headline fits in 2-3 lines comfortably
    for size in range(base_font_size, min_font_size - 1, -1):
        f = load_font("sans", size)
        lines = wrap_text_to_width(headline, f, max_text_w, temp_draw)
        spacing = max(4, int(size * 0.16))
        _, th = calculate_multiline_box(lines, f, temp_draw, spacing)
        if len(lines) <= 2 and th <= max_headline_box_h:
            selected_font = f
            selected_lines = lines
            selected_spacing = spacing
            break
        if len(lines) <= 3 and size <= int(base_font_size * 0.8) and th <= max_headline_box_h:
            selected_font = f
            selected_lines = lines
            selected_spacing = spacing
            break

    # If headline is exceptionally long even at min_font_size:
    if not selected_font:
        selected_font = load_font("sans", min_font_size)
        selected_spacing = max(4, int(min_font_size * 0.16))
        selected_lines = wrap_text_to_width(headline, selected_font, max_text_w, temp_draw)
        if len(selected_lines) > 3:
            selected_lines = selected_lines[:3]
            while selected_lines[2] and (
                temp_draw.textbbox((0, 0), selected_lines[2] + "…", font=selected_font)[2]
                - temp_draw.textbbox((0, 0), selected_lines[2] + "…", font=selected_font)[0]
                > max_text_w
            ):
                words = selected_lines[2].split()
                if len(words) > 1:
                    selected_lines[2] = " ".join(words[:-1])
                else:
                    selected_lines[2] = selected_lines[2][:-1]
            selected_lines[2] = selected_lines[2].rstrip() + "…"

    # Calculate exact dynamic height from wrapped lines
    _, text_h = calculate_multiline_box(selected_lines, selected_font, temp_draw, selected_spacing)
    headline_bar_h = text_h + 2 * pad_y
    total_ticker_h = strip_h + headline_bar_h
    strip_y = h - total_ticker_h

    # Pre-render the ticker overlay ONCE
    ticker_img = Image.new("RGB", (w, total_ticker_h))
    ticker_draw = ImageDraw.Draw(ticker_img)

    # 1. Dark lower-third background
    ticker_draw.rectangle([0, strip_h, w, total_ticker_h], fill=(18, 20, 26))

    # 2. Red category header strip
    ticker_draw.rectangle([0, 0, w, strip_h], fill=(210, 25, 25))

    # 3. TV broadcast golden divider line (2px)
    ticker_draw.rectangle([0, strip_h, w, strip_h + 2], fill=(255, 204, 0))

    # 4. Category badge text
    ticker_draw.text((pad_x, strip_h / 2), category.upper(), font=badge_font, fill=(255, 255, 255), anchor="lm")

    # 5. Live broadcast indicator on the right
    cat_bbox = ticker_draw.textbbox((0, 0), category.upper(), font=badge_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    if cat_w < w * 0.6:
        ticker_draw.text((w - pad_x, strip_h / 2), "● ПРЯМОЙ ЭФИР", font=badge_font, fill=(255, 255, 255), anchor="rm")

    # 6. Headline text lines
    cur_y = strip_h + pad_y
    for line in selected_lines:
        if line:
            ticker_draw.text((pad_x, cur_y), line, font=selected_font, fill=(255, 255, 255))
        bbox = ticker_draw.textbbox((0, 0), line or "A", font=selected_font)
        cur_y += (bbox[3] - bbox[1]) + selected_spacing

    # Apply ticker overlay to each frame
    output_frames: list[Image.Image] = []
    for frame in media.frames:
        frame_copy = frame.copy()
        frame_copy.paste(ticker_img, (0, strip_y))
        output_frames.append(frame_copy)

    destination, out_w, out_h = save_media_result(
        frames=output_frames,
        durations=media.durations,
        loop=media.loop,
        output_path=output_path,
        prefix="news",
        is_animated=media.is_animated,
    )

    return {
        "success": True,
        "path": str(destination),
        "width": out_w,
        "height": out_h,
    }
