# Unsplash MCP Server

An MCP (Model Context Protocol) server for fetching photos from [Unsplash](https://unsplash.com) with **proper attribution**. Designed for LLMs building content pages that need properly credited images.

## Features

- **Search Photos** - Find photos by keyword with filters (color, orientation)
- **Random Photos** - Get random photos for variety in content
- **Download Tracking** - Compliant with Unsplash API guidelines
- **Full Attribution** - Every photo includes ready-to-use attribution text and HTML
- **LLM-Optimized** - Pre-formatted attribution strings for easy embedding

## Why This Server?

Unsplash requires proper attribution when using their photos. This server makes it easy by including:

- `attribution_text`: Plain text like "Photo by John Doe on Unsplash"
- `attribution_html`: Full HTML with proper links for web pages

```html
Photo by <a href="https://unsplash.com/@johndoe">John Doe</a> on <a href="https://unsplash.com">Unsplash</a>
```

## Installation

### Prerequisites

- Python 3.11+
- An Unsplash API access key ([Get one here](https://unsplash.com/developers))

### Quick Start

```bash
# Clone the repository
git clone https://github.com/cevatkerim/unsplash-mcp.git
cd unsplash-mcp

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastmcp httpx python-dotenv

# Set your API key
echo "UNSPLASH_ACCESS_KEY=your_key_here" > .env

# Run the server
fastmcp run server.py
```

## Configuration

### Claude Code

Add to your `~/.claude.json` (user-level) or project `.mcp.json`:

```json
{
  "mcpServers": {
    "unsplash": {
      "type": "stdio",
      "command": "/path/to/unsplash-mcp/.venv/bin/fastmcp",
      "args": ["run", "/path/to/unsplash-mcp/server.py"],
      "env": {
        "UNSPLASH_ACCESS_KEY": "your_access_key_here"
      }
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "unsplash": {
      "command": "/path/to/unsplash-mcp/.venv/bin/fastmcp",
      "args": ["run", "/path/to/unsplash-mcp/server.py"],
      "env": {
        "UNSPLASH_ACCESS_KEY": "your_access_key_here"
      }
    }
  }
}
```

### Windsurf / Cline

Add to your MCP configuration:

```json
{
  "unsplash": {
    "command": "/path/to/unsplash-mcp/.venv/bin/fastmcp",
    "args": ["run", "/path/to/unsplash-mcp/server.py"],
    "env": {
      "UNSPLASH_ACCESS_KEY": "your_access_key_here"
    }
  }
}
```

## Tools

### `search_photos`

Search for photos by keyword with optional filters.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search keyword(s) |
| `page` | int | 1 | Page number |
| `per_page` | int | 10 | Results per page (1-30) |
| `order_by` | string | "relevant" | Sort: "relevant" or "latest" |
| `color` | string | null | Color filter (see below) |
| `orientation` | string | null | "landscape", "portrait", "squarish" |
| `content_filter` | string | "low" | Safety: "low" or "high" |

**Color options:** `black_and_white`, `black`, `white`, `yellow`, `orange`, `red`, `purple`, `magenta`, `green`, `teal`, `blue`

**Example:**
```
search_photos("mountain sunset", per_page=5, orientation="landscape")
```

### `get_random_photos`

Get random photos, optionally filtered by keyword.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | null | Optional keyword filter |
| `count` | int | 1 | Number of photos (1-30) |
| `orientation` | string | null | "landscape", "portrait", "squarish" |
| `content_filter` | string | "low" | Safety: "low" or "high" |

**Example:**
```
get_random_photos(query="nature", count=3, orientation="landscape")
```

### `track_download`

Track a photo download (required by Unsplash API guidelines).

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `photo_id` | string | Photo ID from search results |

**Example:**
```
track_download("abc123xyz")
```

## Response Format

Each photo includes:

```python
{
    "id": "abc123",
    "description": "A beautiful mountain landscape",
    "alt_description": "snow-capped mountains under blue sky",
    "urls": {
        "raw": "https://images.unsplash.com/...",
        "full": "https://images.unsplash.com/...",
        "regular": "https://images.unsplash.com/...",  # Recommended for web
        "small": "https://images.unsplash.com/...",
        "thumb": "https://images.unsplash.com/..."
    },
    "width": 4000,
    "height": 3000,
    "color": "#a3c4f3",  # Dominant color for placeholders
    "blur_hash": "LKO2?U%2Tw=w...",  # For progressive loading

    # Attribution (REQUIRED when using the image)
    "photographer_name": "John Doe",
    "photographer_username": "johndoe",
    "photographer_url": "https://unsplash.com/@johndoe?utm_source=...",
    "photo_url": "https://unsplash.com/photos/abc123?utm_source=...",

    # Ready-to-use attribution
    "attribution_text": "Photo by John Doe on Unsplash",
    "attribution_html": "Photo by <a href=\"...\">John Doe</a> on <a href=\"...\">Unsplash</a>"
}
```

## Usage Example

When an LLM builds a content page:

1. Search for relevant images:
   ```
   photos = search_photos("coffee shop interior", per_page=5)
   ```

2. Select a photo and use it:
   ```html
   <img src="{photo.urls.regular}" alt="{photo.alt_description}">
   <p class="attribution">{photo.attribution_html}</p>
   ```

3. If offering download, track it:
   ```
   download_url = track_download(photo.id)
   ```

## Unsplash API Guidelines

This server helps you comply with [Unsplash API guidelines](https://unsplash.com/api-terms):

1. **Attribution** - Always credit the photographer and Unsplash (use `attribution_html`)
2. **Hotlinking** - Use the provided URLs directly (enables view tracking)
3. **Download tracking** - Call `track_download()` when users download images

## Rate Limits

- **Demo mode**: 50 requests/hour
- **Production**: 5,000 requests/hour (after approval)

## License

MIT License - See [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Support

If you find this project useful, consider buying me a coffee!

<a href="https://www.buymeacoffee.com/cevatkerim" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## Acknowledgments

- [Unsplash](https://unsplash.com) for providing an amazing free photo API
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP server framework
