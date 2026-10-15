"""Project generator: turn a template directory into a working MCP server."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

__all__ = ["TEMPLATES_DIR", "available_templates", "render", "generate"]

TEMPLATES_DIR = Path(__file__).parent / "templates"

#: Files named like this are written to a different path in the output.
RENAMES = {"gitignore.tmpl": ".gitignore"}

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,48}$")


def available_templates() -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir())


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return slug or "mcp-server"


def render(text: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def build_context(project: str, description: str, author: str) -> dict[str, str]:
    slug = slugify(project)
    return {
        "project_name": slug,
        "package_name": slug.replace("-", "_"),
        "title": slug.replace("-", " ").title(),
        "description": description,
        "author": author,
        "year": str(_dt.date.today().year),
    }


def generate(
    project: str,
    destination: Path,
    *,
    template: str = "basic",
    description: str = "An MCP server built with mcp-forge.",
    author: str = "",
    force: bool = False,
) -> list[Path]:
    """Write a new project into ``destination``; returns the files created."""
    # A template is either a bundled name or a path to a template directory
    # (that is how the Pro pack plugs in: mcp-forge new x -t ./pro/templates/sqlite).
    candidate = Path(template).expanduser()
    source = candidate if candidate.is_dir() else TEMPLATES_DIR / template
    if not source.is_dir():
        raise FileNotFoundError(
            f"unknown template {template!r}. Available: {', '.join(available_templates()) or 'none'}"
        )
    slug = slugify(project)
    if not SLUG_PATTERN.match(slug):
        raise ValueError(f"invalid project name: {project!r}")

    root = destination / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"{root} already exists and is not empty (use --force)")

    context = build_context(project, description, author)
    created: list[Path] = []
    for item in sorted(source.rglob("*")):
        if item.is_dir():
            continue
        relative = item.relative_to(source)
        name = RENAMES.get(relative.name, relative.name)
        if name.endswith(".tmpl"):
            name = name[: -len(".tmpl")]
        target = root / relative.parent / render(name, context)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(item.read_text(encoding="utf-8"), context), encoding="utf-8")
        created.append(target)
    return created
