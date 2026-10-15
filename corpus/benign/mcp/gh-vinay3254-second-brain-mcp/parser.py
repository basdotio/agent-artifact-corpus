import os
import re
import frontmatter

# Regex for Obsidian wikilinks: [[Target Note]] or [[Target Note#Header]] or [[Target Note|Alias]]
# Captures the target note title before any # or |
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]')

def parse_markdown_file(file_path: str) -> dict:
    """
    Parses an Obsidian markdown file and extracts its title, body, tags, and wikilinks.
    """
    filename = os.path.basename(file_path)
    default_title = os.path.splitext(filename)[0]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
    except Exception as e:
        # Fallback if frontmatter parsing fails entirely
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "title": default_title,
                "body": content,
                "tags": [],
                "wikilinks": list(set(link.strip() for link in WIKILINK_RE.findall(content) if link.strip()))
            }
        except Exception:
            return {
                "title": default_title,
                "body": "",
                "tags": [],
                "wikilinks": []
            }

    # Extract title from frontmatter or fallback to filename
    title = post.get('title', default_title)
    if not isinstance(title, str):
        title = str(title)
    title = title.strip()

    # Extract body
    body = post.content or ""

    # Extract tags from frontmatter
    raw_tags = post.get('tags', [])
    tags = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if t:
                # Strip # prefix if present
                t_str = str(t).strip()
                if t_str.startswith('#'):
                    t_str = t_str[1:]
                tags.append(t_str)
    elif isinstance(raw_tags, str):
        # Handle comma-separated or space-separated tags
        separator = ',' if ',' in raw_tags else ' '
        for t in raw_tags.split(separator):
            t_str = t.strip()
            if t_str:
                if t_str.startswith('#'):
                    t_str = t_str[1:]
                tags.append(t_str)
    
    # Extract wikilinks from body
    raw_links = WIKILINK_RE.findall(body)
    wikilinks = sorted(list(set(link.strip() for link in raw_links if link.strip())))

    return {
        "title": title,
        "body": body,
        "tags": tags,
        "wikilinks": wikilinks
    }
