"""
Adapter: ``data/outputs/`` → MCP ``Resource``.

Exposes generated images / videos / audio / code / docs under the
``guaardvark://outputs/{relative_path}`` URI scheme. Read-only. Chrooted:
any URI that resolves outside the configured outputs root is denied.

Only the generated-media folders named in ``ResourcePolicy.outputs_folders``
(and, when enabled, files directly in the root) are resources. The same
:class:`OutputScope` decides both what a listing shows and what a read
returns, so a path that is never listed cannot be read by guessing its URI.

Listing walks the tree lazily in a stable order and returns one page at a
time, so a large outputs directory costs only the directories a page reads.
Filesystem work runs off the event loop. A file above the inline limit is not
embedded in the protocol response; the result names where to download it.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import mimetypes
import os
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote, unquote, urlparse

import mcp.types as mcp_types

from backend.mcp.audit import audit_call
from backend.mcp.config import MCPConfig, ResourcePolicy, load_config
from backend.utils.backend_http import backend_base_url

logger = logging.getLogger(__name__)

URI_SCHEME = "guaardvark"
URI_PREFIX = f"{URI_SCHEME}://outputs/"

# Directories and file patterns we never surface (runtime state, not artifacts).
# Any name starting with a dot is skipped as well (job stores, scratch folders).
_EXCLUDE_DIRS = {".progress_jobs", "__pycache__", ".git"}
_EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}
# Likeness consent sidecars (``<image>.consent``, backend/services/consent_records.py)
# can sit next to an image in a served folder; they are records, not outputs.
_EXCLUDE_SUFFIXES = (".consent",)
# Resources per resources/list page.
PAGE_SIZE = 200
# The startup banner counts at most this many files.
_BANNER_COUNT_LIMIT = 500


def _skipped_name(name: str) -> bool:
    return name.startswith(".") or name in _EXCLUDE_DIRS


@dataclass(frozen=True)
class OutputScope:
    """Which paths under the outputs root are resources.

    ``folders`` holds each served folder as a tuple of path parts relative to
    the root; everything below one is served. ``root_files`` serves files that
    sit directly in the root. Paths are compared part by part, exactly, so a
    differently cased or partial folder name is not served.
    """

    folders: tuple[tuple[str, ...], ...]
    root_files: bool

    @classmethod
    def from_policy(cls, policy: ResourcePolicy) -> "OutputScope":
        folders = []
        for entry in policy.outputs_folders:
            parts = tuple(p for p in str(entry).replace("\\", "/").split("/") if p)
            if parts and not any(p in (".", "..") for p in parts):
                folders.append(parts)
        return cls(folders=tuple(folders), root_files=bool(policy.outputs_root_files))

    def enters(self, dir_parts: tuple[str, ...]) -> bool:
        """True when the directory at ``dir_parts`` is, or leads to, a served folder."""
        if any(_skipped_name(p) for p in dir_parts):
            return False
        return any(
            dir_parts[:len(folder)] == folder or folder[:len(dir_parts)] == dir_parts
            for folder in self.folders
        )

    def serves(self, file_parts: tuple[str, ...]) -> bool:
        """True when the file at ``file_parts`` is a resource."""
        if not file_parts or any(_skipped_name(p) for p in file_parts):
            return False
        name = file_parts[-1]
        if name in _EXCLUDE_FILES or name.endswith(_EXCLUDE_SUFFIXES):
            return False
        if len(file_parts) == 1:
            return self.root_files
        return any(
            len(file_parts) > len(folder) and file_parts[:len(folder)] == folder
            for folder in self.folders
        )


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _outputs_root(config: MCPConfig) -> Path:
    root = Path(config.resources.outputs_root)
    if not root.is_absolute():
        root = _project_root() / root
    return root.resolve()


def _uri_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    # Percent-encode each segment; keep the slash separators intact.
    return URI_PREFIX + "/".join(quote(seg, safe="") for seg in rel.split("/"))


def _path_for_uri(uri: str, root: Path) -> Path | None:
    """Resolve a guaardvark://outputs/... URI to a file path, or None if bad."""
    if not uri.startswith(URI_PREFIX):
        return None
    parsed = urlparse(uri)
    if parsed.scheme != URI_SCHEME:
        return None
    # guaardvark://outputs/a/b.png parses as netloc 'outputs', path '/a/b.png'.
    # The netloc is the scheme's fixed authority, never part of the file path,
    # so a real subfolder named 'outputs' round-trips like any other.
    rel = unquote(parsed.path.lstrip("/"))

    candidate = (root / rel).resolve()
    # Chroot check — the resolved path must be under root. No .. escapes.
    try:
        candidate.relative_to(root)
    except ValueError:
        logger.warning("MCP: rejected out-of-chroot URI %s", uri)
        return None
    return candidate


def outputs_root() -> Path:
    """The outputs root the provider serves under the loaded config."""
    return _outputs_root(load_config())


def is_served(path: str | os.PathLike, root: str | os.PathLike,
              policy: ResourcePolicy | None = None) -> bool:
    """True when ``path`` (symlinks resolved) is a file under ``root`` that the
    outputs provider would list and read under ``policy`` (default: the loaded
    config). Tools that take outputs as inputs from MCP clients check this, so
    they accept exactly what resources/read would return."""
    if policy is None:
        policy = load_config().resources
    try:
        rel = Path(os.path.realpath(path)).relative_to(os.path.realpath(root))
    except ValueError:
        return False
    return OutputScope.from_policy(policy).serves(rel.parts)


def _mime_for(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def _walk(
    directory: Path,
    after: tuple[str, ...],
    scope: OutputScope,
    parts: tuple[str, ...] = (),
) -> Iterator[Path]:
    """Served files below ``directory`` (whose path from the root is ``parts``),
    names sorted within each directory, starting after the relative path parts
    ``after``. Symlinks are not listed; folders outside ``scope`` are not read."""
    try:
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda entry: entry.name)
    except OSError:
        return
    head = after[0] if after else None
    for entry in entries:
        if head is not None and entry.name < head:
            continue
        rest = after[1:] if head is not None and entry.name == head else ()
        entry_parts = parts + (entry.name,)
        try:
            if entry.is_dir(follow_symlinks=False):
                if scope.enters(entry_parts):
                    yield from _walk(Path(entry.path), rest, scope, entry_parts)
            elif entry.is_file(follow_symlinks=False):
                if head is not None and entry.name == head:
                    continue  # the cursor itself ended the previous page
                if scope.serves(entry_parts):
                    yield Path(entry.path)
        except OSError:
            continue  # removed between the listing and the check


def _cursor_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return base64.urlsafe_b64encode(rel.encode("utf-8")).decode("ascii")


def _cursor_parts(cursor: str | None) -> tuple[str, ...]:
    if not cursor:
        return ()
    try:
        rel = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid resources cursor: {cursor!r}") from exc
    parts = tuple(part for part in rel.split("/") if part)
    if not parts or any(part in (".", "..") for part in parts):
        raise ValueError(f"Invalid resources cursor: {cursor!r}")
    return parts


def _list_page(
    root: Path,
    scope: OutputScope,
    cursor: str | None,
    page_size: int | None = None,
) -> tuple[list[Path], str | None]:
    """One page of served files and the cursor for the next page (None on the last)."""
    page_size = page_size or PAGE_SIZE
    after = _cursor_parts(cursor)
    if not root.exists():
        return [], None
    files: list[Path] = []
    for path in _walk(root, after, scope):
        if len(files) == page_size:
            return files, _cursor_for(files[-1], root)
        files.append(path)
    return files, None


def _count(root: Path, scope: OutputScope, limit: int | None = None) -> int:
    """Served files under ``root``, counting at most ``limit`` when given."""
    if not root.exists():
        return 0
    files = _walk(root, (), scope)
    if limit is not None:
        files = islice(files, limit)
    return sum(1 for _ in files)


def count_resources(config: MCPConfig) -> int:
    """How many files the outputs provider serves right now (a full walk)."""
    if not config.resources.outputs_enabled:
        return 0
    return _count(_outputs_root(config), OutputScope.from_policy(config.resources))


def _read_contents(uri: str, root: Path, scope: OutputScope, max_inline_bytes: int) -> tuple[Any, int]:
    """The resource contents for ``uri`` and the file size. Raises FileNotFoundError."""
    path = _path_for_uri(uri, root)
    try:
        # The scope is checked on the resolved path, the file that would be sent,
        # so '..' segments and symlinks cannot reach a folder that is not served.
        if (
            path is None
            or not scope.serves(path.relative_to(root).parts)
            or not path.is_file()
        ):
            raise FileNotFoundError(f"Unknown or out-of-scope resource: {uri}")
        size = path.stat().st_size
        mime = _mime_for(path)
        if size > max_inline_bytes:
            rel = path.relative_to(root).as_posix()
            link = f"{backend_base_url()}/outputs/{quote(rel)}"
            return mcp_types.TextResourceContents(
                uri=uri,
                mime_type="text/plain",
                text=(
                    f"{path.name} is {size} bytes, above this server's {max_inline_bytes}-byte "
                    f"inline limit, so it is not embedded. Download it from {link} on this "
                    f"machine (send the X-API-Key header if this install sets "
                    f"GUAARDVARK_API_KEY), or read {path} directly."
                ),
            ), size
        # Text MIME types go as UTF-8 text; everything else as base64 blob.
        if mime.startswith("text/") or mime in {"application/json", "application/xml"}:
            return mcp_types.TextResourceContents(
                uri=uri,
                mime_type=mime,
                text=path.read_text(encoding="utf-8", errors="replace"),
            ), size
        return mcp_types.BlobResourceContents(
            uri=uri,
            mime_type=mime,
            blob=base64.b64encode(path.read_bytes()).decode("ascii"),
        ), size
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise FileNotFoundError(f"Resource could not be read: {uri} ({exc})") from exc


def build_resource_handlers(config: MCPConfig) -> tuple[Any, Any, int]:
    """
    Build ``on_list_resources`` / ``on_read_resource`` handlers for the mcp 2.x
    ``Server`` constructor. Returns (on_list, on_read, count-at-build-time);
    handlers are ``None`` when the outputs provider is disabled so the server
    doesn't advertise a resources capability it can't serve.
    """
    if not config.resources.outputs_enabled:
        logger.info("MCP: outputs resource provider disabled by config")
        return None, None, 0

    root = _outputs_root(config)
    if not root.exists():
        logger.info("MCP: outputs root %s does not exist yet — serving empty list", root)
    scope = OutputScope.from_policy(config.resources)
    max_inline_bytes = int(config.resources.max_inline_bytes)

    async def on_list_resources(
        _ctx: Any,
        params: mcp_types.PaginatedRequestParams | None,
    ) -> mcp_types.ListResourcesResult:
        cursor = getattr(params, "cursor", None) if params is not None else None
        with audit_call(method="resources/list", target=str(root)) as rec:
            files, next_cursor = await asyncio.to_thread(_list_page, root, scope, cursor)
            rec["bytes_out"] = len(files)
            return mcp_types.ListResourcesResult(
                resources=[
                    mcp_types.Resource(
                        uri=_uri_for(path, root),
                        name=path.name,
                        description=f"Generated output: {path.relative_to(root).as_posix()}",
                        mime_type=_mime_for(path),
                    )
                    for path in files
                ],
                next_cursor=next_cursor,
            )

    async def on_read_resource(
        _ctx: Any,
        params: mcp_types.ReadResourceRequestParams,
    ) -> mcp_types.ReadResourceResult:
        uri_str = str(params.uri)
        with audit_call(method="resources/read", target=uri_str) as rec:
            try:
                contents, size = await asyncio.to_thread(_read_contents, uri_str, root, scope, max_inline_bytes)
            except FileNotFoundError:
                rec["outcome"] = "error"
                rec["error_code"] = "not_found"
                raise
            rec["bytes_out"] = size
            return mcp_types.ReadResourceResult(contents=[contents])

    # Count at build time for the startup banner, capped so a large tree does not
    # delay startup; count_resources gives the full figure. Every list request
    # walks again so new files show up without a restart.
    count = _count(root, scope, _BANNER_COUNT_LIMIT)
    return on_list_resources, on_read_resource, count
