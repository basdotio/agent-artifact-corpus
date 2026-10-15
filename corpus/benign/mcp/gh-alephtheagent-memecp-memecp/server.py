"""MemeCP FastMCP Server for generating classic and post-ironic memes."""

from __future__ import annotations

import sys
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import MCPServer as FastMCP

from memecp.generator import (
    create_classic_meme as gen_classic_meme,
    create_demotivator as gen_demotivator,
    create_post_ironic_meme as gen_post_ironic_meme,
    create_caption_meme as gen_caption_meme,
    create_news_meme as gen_news_meme,
    list_available_fonts as gen_list_fonts,
)

mcp = FastMCP(
    "memecp",
    instructions="MemeCP: FastMCP Server for generating classic Impact memes, Russian demotivators, caption boxes, and post-ironic formats on demand with full static image and animated GIF support.",
)


@mcp.tool()
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
    Generate a classic top/bottom text meme with black outline (Impact font default).
    Supports static images and animated GIFs (outputs animated .gif).

    Args:
        image_source: Local file path or direct HTTP/HTTPS URL (supports JPG, PNG, animated GIF).
        top_text: Text placed at the top (auto-wrapped and auto-sized).
        bottom_text: Text placed at the bottom (auto-wrapped and auto-sized).
        font_name: Font to use ('impact', 'lobster', 'oswald', 'serif', 'sans', or file path).
        font_size: Font size in pixels (0 for auto-calculated size).
        stroke_width: Outline width in pixels (0 for auto-calculated width).
        text_color: Text fill color (default 'white').
        stroke_color: Outline stroke color (default 'black').
        all_caps: Whether to convert text to UPPERCASE (default True).
        output_path: Destination path for saved image (.gif automatically if source is animated GIF).

    Returns:
        dict with success (bool), path (str), width (int), height (int).
    """
    try:
        return gen_classic_meme(
            image_source=image_source,
            top_text=top_text,
            bottom_text=bottom_text,
            font_name=font_name,
            font_size=font_size,
            stroke_width=stroke_width,
            text_color=text_color,
            stroke_color=stroke_color,
            all_caps=all_caps,
            output_path=output_path,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def create_demotivator(
    image_source: str,
    title: str,
    subtitle: str = "",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a classic Russian 2007-style demotivator.
    Supports static images and animated GIFs (outputs animated .gif).

    Args:
        image_source: Local file path or direct HTTP/HTTPS URL (supports JPG, PNG, animated GIF).
        title: Large serif title centered below the framed image.
        subtitle: Explanatory smaller serif subtitle.
        output_path: Destination path for saved image (.gif automatically if source is animated GIF).

    Returns:
        dict with success (bool), path (str), width (int), height (int).
    """
    try:
        return gen_demotivator(
            image_source=image_source,
            title=title,
            subtitle=subtitle,
            output_path=output_path,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def create_caption_meme(
    image_source: str,
    caption: str,
    font_name: str = "futura",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate an esmBot / Discord / iFunny style white header caption box meme.
    Supports static images and animated GIFs (outputs animated .gif).

    Args:
        image_source: Local file path or direct HTTP/HTTPS URL (supports JPG, PNG, animated GIF).
        caption: Caption text placed in the top white canvas box.
        font_name: Bundled alias (default 'futura' for Futura Condensed, or 'sans', 'impact').
        output_path: Destination path for saved image (.gif automatically if source is animated GIF).

    Returns:
        dict with success (bool), path (str), width (int), height (int).
    """
    try:
        return gen_caption_meme(
            image_source=image_source,
            caption=caption,
            font_name=font_name,
            output_path=output_path,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def create_post_ironic_meme(
    image_source: str,
    caption: str,
    style: str = "caption_box",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate post-ironic and modern memes (top caption box, deep-fry, or bottom ticker).
    Supports static images and animated GIFs (outputs animated .gif).

    Args:
        image_source: Local file path or direct HTTP/HTTPS URL (supports JPG, PNG, animated GIF).
        caption: Caption text or headline.
        style: Meme style ('caption_box', 'deep_fry', 'bottom_ticker').
        output_path: Destination path for saved image (.gif automatically if source is animated GIF).

    Returns:
        dict with success (bool), path (str), width (int), height (int).
    """
    try:
        return gen_post_ironic_meme(
            image_source=image_source,
            caption=caption,
            style=style,
            output_path=output_path,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def create_news_meme(
    image_source: str,
    headline: str,
    category: str = "⚡ СРОЧНО",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a breaking news ticker overlay at the bottom of the image.
    Supports static images and animated GIFs (outputs animated .gif).

    Args:
        image_source: Local file path or direct HTTP/HTTPS URL (supports JPG, PNG, animated GIF).
        headline: Main news headline text.
        category: News category tag (default '⚡ СРОЧНО').
        output_path: Destination path for saved image (.gif automatically if source is animated GIF).

    Returns:
        dict with success (bool), path (str), width (int), height (int).
    """
    try:
        return gen_news_meme(
            image_source=image_source,
            headline=headline,
            category=category,
            output_path=output_path,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def list_fonts() -> list[str]:
    """
    List all available built-in font identifiers.

    Returns:
        List of font names (e.g. ['impact', 'lobster', 'oswald', 'sans', 'serif', ...]).
    """
    return gen_list_fonts()


def main() -> None:
    """Run the MemeCP FastMCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
