"""MemeCP: FastMCP Server for generating classic & post-ironic Impact memes on demand."""

__version__ = "0.1.0"

from .generator import (
    create_classic_meme,
    create_demotivator,
    create_post_ironic_meme,
    create_caption_meme,
    create_news_meme,
    list_available_fonts,
)

__all__ = [
    "create_classic_meme",
    "create_demotivator",
    "create_post_ironic_meme",
    "create_caption_meme",
    "create_news_meme",
    "list_available_fonts",
]
