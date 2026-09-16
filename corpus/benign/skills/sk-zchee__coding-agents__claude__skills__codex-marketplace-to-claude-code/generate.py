#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "orjson",
#   "jsonschema",
# ]
# ///

"""Generate a Claude Code marketplace manifest from a Codex one.

Reads ``<repo>/.agents/plugins/marketplace.json`` for the plugin list, each
plugin's own ``<repo>/plugins/<name>/.codex-plugin/plugin.json`` for its
metadata, and the official Claude Code marketplace for category assignments,
then writes ``<repo>/.claude-plugin/marketplace.json``.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import orjson
from jsonschema import Draft7Validator

logger = logging.getLogger("codex-marketplace")

# Both the "$schema" written into the output and the schema validated against.
# The anthropic.com URL the official marketplace names redirects rather than
# serving a document, so schemastore's is the only fetchable one.
SCHEMA_URL = "https://www.schemastore.org/claude-code-marketplace.json"
SCHEMA_CACHE = Path.home() / ".cache/codex-marketplace/claude-code-marketplace.json"

DEFAULT_OFFICIAL = (
    Path.home()
    / "src/github.com/anthropics/claude-plugins-official/.claude-plugin/marketplace.json"
)

# Codex title-case categories -> the lowercase set the official Claude Code
# marketplace uses. Consulted only when the official marketplace has no entry
# for the same plugin name.
CATEGORY_FALLBACK = {
    "Business & Operations": "productivity",
    "Communication": "productivity",
    "Creativity": "design",
    "Data & Analytics": "monitoring",
    "Developer Tools": "development",
    "Education & Research": "learning",
    "Finance": "productivity",
    "Productivity": "productivity",
    "Scientific Research": "learning",
    "Security": "security",
}

# Official descriptions top out at 665 characters and never contain newlines.
MAX_DESCRIPTION = 600

KEY_ORDER = ("$schema", "name", "description", "owner", "plugins")


def read_json(path: Path) -> dict[str, Any]:
    """Parse a JSON object from a file.

    Args:
        path: File to read.

    Returns:
        The parsed object.

    Raises:
        FileNotFoundError: If the file does not exist.
        orjson.JSONDecodeError: If the file is not valid JSON.
    """
    return orjson.loads(path.read_bytes())


def normalize_description(raw: str) -> str:
    """Reduce a vendor description to one marketplace-sized line.

    Keeps the first paragraph, collapses whitespace, and trims at a sentence
    boundary so the result stays under ``MAX_DESCRIPTION`` characters. Short
    first paragraphs absorb following ones until they carry enough text.

    Args:
        raw: Description as written in the plugin manifest.

    Returns:
        A single-line description.
    """
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in raw.split("\n")]
    paragraphs = [p for p in paragraphs if p]
    text = paragraphs[0] if paragraphs else ""
    index = 1
    while len(text) < 60 and index < len(paragraphs):
        text = f"{text} {paragraphs[index]}"
        index += 1
    if len(text) > MAX_DESCRIPTION:
        cut = text.rfind(". ", 0, MAX_DESCRIPTION)
        text = text[: cut + 1] if cut > 200 else text[:MAX_DESCRIPTION].rstrip() + "..."
    return text


def author_of(manifest: dict[str, Any]) -> dict[str, str] | None:
    """Extract the fields Claude Code reads from an author block.

    Args:
        manifest: A plugin manifest or marketplace entry.

    Returns:
        The author with only ``name``, ``email`` and ``url``, or None when the
        manifest carries no usable author.
    """
    author = manifest.get("author")
    if not isinstance(author, dict):
        return None
    return {
        key: author[key] for key in ("name", "email", "url") if author.get(key)
    } or None


def git(repo: Path, *args: str) -> str:
    """Run a git command in a repository and return its stdout.

    Args:
        repo: Repository to run in.
        *args: Arguments after ``git -C <repo>``.

    Returns:
        Trimmed stdout, or an empty string when the command fails.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def tree_url(repo: Path) -> str | None:
    """Build the browse URL that homepage fallbacks hang off.

    Args:
        repo: Repository whose ``origin`` remote names the host and path.

    Returns:
        ``https://<host>/<owner>/<repo>/tree/<default branch>``, or None when
        the repository has no origin remote.
    """
    origin = git(repo, "remote", "get-url", "origin")
    if not origin:
        return None
    origin = origin.removesuffix(".git")
    if origin.startswith("git@"):
        origin = "https://" + origin[4:].replace(":", "/", 1)
    head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    branch = head.split("/")[-1] if head else "main"
    return f"{origin}/tree/{branch}"


def convert_entry(
    entry: dict[str, Any],
    manifest: dict[str, Any],
    upstream: dict[str, Any],
    tree: str | None,
) -> dict[str, Any]:
    """Convert one Codex marketplace entry into a Claude Code entry.

    Args:
        entry: The entry as written in the Codex marketplace.
        manifest: The plugin's own ``.codex-plugin/plugin.json``, empty for a
            remote source that has no local directory.
        upstream: The official Claude Code marketplace entry of the same name,
            empty when the plugin is not published there.
        tree: Browse URL used to synthesize a missing homepage.

    Returns:
        The Claude Code entry, with keys in the order the official marketplace
        writes them.
    """
    source = entry["source"]
    local = source.get("source") == "local"
    out: dict[str, Any] = {"name": entry["name"]}

    display = (manifest.get("interface") or {}).get("displayName") or (
        entry.get("interface") or {}
    ).get("displayName")
    if display:
        out["displayName"] = display

    # Remote entries carry no local manifest, so their prose comes from the
    # official marketplace entry for the same upstream repository.
    description = manifest.get("description") or upstream.get("description")
    if description:
        out["description"] = normalize_description(description)

    if manifest.get("version"):
        out["version"] = manifest["version"]

    author = author_of(manifest) or author_of(upstream)
    if author:
        out["author"] = author

    category = upstream.get("category") or CATEGORY_FALLBACK.get(entry["category"])
    if category:
        out["category"] = category

    if local:
        out["source"] = source["path"]
        # These directories ship .codex-plugin/plugin.json, not
        # .claude-plugin/plugin.json. strict:false makes Claude Code take the
        # metadata from this entry and still auto-discover skills/, commands/,
        # agents/, hooks.json and .mcp.json at the plugin root.
        out["strict"] = False
    else:
        out["source"] = dict(source)

    homepage = manifest.get("homepage") or manifest.get("repository")
    if local and tree and (not homepage or homepage == tree.split("/tree/")[0]):
        homepage = f"{tree}/{source['path'].removeprefix('./')}"
    if not local:
        homepage = (
            homepage or upstream.get("homepage") or source["url"].removesuffix(".git")
        )
    if homepage:
        out["homepage"] = homepage

    if manifest.get("keywords"):
        out["keywords"] = manifest["keywords"]
    if manifest.get("license"):
        out["license"] = manifest["license"]
    return out


def build(repo: Path, official_path: Path | None) -> dict[str, Any]:
    """Join the Codex marketplace with plugin manifests and official categories.

    Args:
        repo: Repository holding ``.agents/plugins/marketplace.json`` and the
            plugin directories it points at.
        official_path: The official Claude Code marketplace manifest, or None
            to map every category through ``CATEGORY_FALLBACK``.

    Returns:
        The marketplace body: ``name`` plus ``plugins`` sorted by name.

    Raises:
        SystemExit: If a Codex category has no mapping, or an entry ends up
            with no description from either source.
    """
    src = read_json(repo / ".agents/plugins/marketplace.json")
    official: dict[str, dict[str, Any]] = {}
    if official_path and official_path.is_file():
        official = {p["name"]: p for p in read_json(official_path)["plugins"]}
    else:
        logger.warning(
            "official marketplace not read (%s); categories come from CATEGORY_FALLBACK only",
            official_path,
        )

    tree = tree_url(repo)
    plugins: list[dict[str, Any]] = []
    unmapped: set[str] = set()
    undescribed: list[str] = []

    for entry in src["plugins"]:
        source = entry["source"]
        manifest: dict[str, Any] = {}
        if source.get("source") == "local":
            path = source["path"].removeprefix("./")
            manifest = read_json(repo / path / ".codex-plugin/plugin.json")

        converted = convert_entry(
            entry, manifest, official.get(entry["name"], {}), tree
        )
        if not converted.get("category"):
            unmapped.add(entry["category"])
        if not converted.get("description"):
            undescribed.append(entry["name"])
        plugins.append(converted)

    if unmapped:
        raise SystemExit(
            f"unmapped Codex categories, add them to CATEGORY_FALLBACK: {', '.join(sorted(unmapped))}"
        )
    if undescribed:
        raise SystemExit(
            "no description available (no local manifest and no official entry): "
            + ", ".join(undescribed)
        )

    # Entry order follows the official marketplace convention: name ascending.
    plugins.sort(key=lambda plugin: plugin["name"])
    return {"name": src["name"], "plugins": plugins}


def load_schema(refresh: bool = False) -> dict[str, Any] | None:
    """Return the published marketplace JSON Schema, caching it on disk.

    Args:
        refresh: Fetch the schema even when a cached copy exists.

    Returns:
        The schema, or None when it is neither cached nor reachable.
    """
    if SCHEMA_CACHE.is_file() and not refresh:
        return read_json(SCHEMA_CACHE)
    try:
        with urllib.request.urlopen(SCHEMA_URL, timeout=10) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        logger.warning("schema not fetched from %s (%s)", SCHEMA_URL, error)
        return None
    SCHEMA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_CACHE.write_bytes(body)
    return orjson.loads(body)


def schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate a marketplace document against the published schema.

    The schema trails the CLI's own validator (it does not yet know
    ``displayName``, for one), so it is a structural pre-check rather than the
    authority; ``claude plugin validate --strict`` remains that.

    Args:
        document: The marketplace about to be written.
        schema: Schema from :func:`load_schema`.

    Returns:
        One ``path -> message`` line per violation, in document order.
    """
    violations = sorted(
        Draft7Validator(schema).iter_errors(document),
        key=lambda e: list(e.absolute_path),
    )
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'} -> {e.message}"
        for e in violations
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument vector, defaulting to ``sys.argv[1:]``.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--official",
        type=Path,
        default=DEFAULT_OFFICIAL,
        help="path to the official Claude Code .claude-plugin/marketplace.json",
    )
    parser.add_argument("--out", type=Path, help="output path")
    parser.add_argument(
        "--schema",
        help="$schema URL (default: keep the one already in the output file)",
    )
    parser.add_argument(
        "--description", help="top-level marketplace description for the generated file"
    )
    parser.add_argument("--owner-name", help="top-level owner.name")
    parser.add_argument("--owner-url", help="top-level owner.url")
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="write without checking the result against the published JSON Schema",
    )
    parser.add_argument(
        "--refresh-schema",
        action="store_true",
        help="re-download the cached JSON Schema",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Generate the marketplace file and report where it was written."""
    logging.basicConfig(format="%(levelname)s: %(message)s", stream=sys.stderr)
    args = parse_args()

    repo = args.repo.resolve()
    marketplace = build(repo, args.official)
    out = args.out or repo / ".claude-plugin/marketplace.json"

    # The hand-written header survives regeneration: whatever the output file
    # already carries is kept unless the matching flag overrides it. A
    # schemastore mirror an editor validates against therefore stays put.
    previous = read_json(out) if out.is_file() else {}
    marketplace["$schema"] = args.schema or previous.get("$schema") or SCHEMA_URL
    description = args.description or previous.get("description")
    if description:
        marketplace["description"] = description
    owner = {k: v for k, v in (("name", args.owner_name), ("url", args.owner_url)) if v}
    if owner or previous.get("owner"):
        marketplace["owner"] = owner or previous["owner"]

    ordered = {key: marketplace[key] for key in KEY_ORDER if key in marketplace}

    # Validate before writing, so a rejected document leaves the previous file
    # in place instead of replacing it with something that will not load.
    if not args.no_validate:
        schema = load_schema(refresh=args.refresh_schema)
        if schema:
            errors = schema_errors(ordered, schema)
            for error in errors:
                logger.error("%s", error)
            if errors:
                raise SystemExit(
                    f"{len(errors)} schema violations, nothing written to {out}"
                )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(orjson.dumps(ordered, option=orjson.OPT_INDENT_2) + b"\n")
    print(f"wrote {out} ({len(ordered['plugins'])} plugins)")


if __name__ == "__main__":
    main()
