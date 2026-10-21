"""Parse URLs locally. No requests or DNS lookups are performed."""

from urllib.parse import parse_qs, urlsplit


def inspect_url(url: str) -> dict:
    """Inspect an absolute URL with a hostname; preserve repeated/blank query values."""
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValueError("URL must not contain whitespace or control characters; encode them first.")
    try:
        parts = urlsplit(url)
        if not parts.scheme or not parts.hostname:
            raise ValueError("Use an absolute URL with a scheme and hostname, such as https://example.com.")
        port = parts.port
    except ValueError as error:
        raise ValueError(f"Cannot inspect URL: {error}") from error
    return {"scheme": parts.scheme, "hostname": parts.hostname, "port": port,
            "path": parts.path, "query_parameters": parse_qs(parts.query, keep_blank_values=True),
            "fragment": parts.fragment}
