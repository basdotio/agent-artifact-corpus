"""Finding and opening files on the device's shared storage."""

from __future__ import annotations

import mimetypes
import posixpath

from fastmcp import FastMCP

from ..errors import fail
from ..observe import mutate
from ..parsers.system import MEDIA_KINDS, media_uri, parse_content_rows, parse_find
from ..session import Runtime
from ..shell import q
from .apps import start_intent
from .common import Device, get_session

ALLOWED_ROOTS = ("/sdcard", "/storage/emulated/0", "/data/local/tmp", "/mnt/sdcard")


def safe_path(path: str) -> str:
    clean = posixpath.normpath(path)
    if ".." in path.split("/") or not any(
        clean == r or clean.startswith(r + "/") for r in ALLOWED_ROOTS
    ):
        fail(
            "not_permitted",
            f"{path} is outside shared storage",
            f"allowed roots: {', '.join(ALLOWED_ROOTS)}",
        )
    return clean


MEDIA_KEYS = ("_id", "_display_name", "mime_type", "date_modified", "media_type", "_size", "_data")
KIND_WHERE = {
    "image": "media_type=1",
    "audio": "media_type=2",
    "video": "media_type=3",
    "document": "media_type=6 OR (media_type=0 AND mime_type IS NOT NULL)",
}


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def media_index(session, query: str, kind: str, limit: int) -> list[dict]:
        where = [f"({KIND_WHERE[kind]})" if kind in KIND_WHERE else "mime_type IS NOT NULL"]
        if query:
            where.append("_display_name LIKE " + "'%" + query.replace("'", "''") + "%'")
        cmd = (
            "content query --uri content://media/external/file --projection "
            + ":".join(MEDIA_KEYS)
            + " --where "
            + q(" AND ".join(where))
            + " --sort "
            + q("date_modified DESC")
        )
        rows = parse_content_rows(await session.shell(cmd, timeout=60, check=False), MEDIA_KEYS)
        rows.sort(key=lambda r: int(r.get("date_modified") or 0), reverse=True)
        return [
            {
                "uri": media_uri(r),
                "name": r.get("_display_name", ""),
                "mime": r.get("mime_type", ""),
                "kind": MEDIA_KINDS.get(r.get("media_type", ""), "document"),
                "size": int(r["_size"]) if r.get("_size", "").isdigit() else None,
                "modified": int(r.get("date_modified") or 0),
                "path": r.get("_data", ""),
            }
            for r in rows[:limit]
        ]

    @mcp.tool(tags={"read"})
    async def find_files(
        query: str = "",
        kind: str = "any",
        limit: int = 10,
        path: str | None = None,
        max_depth: int = 6,
        device: Device = None,
    ) -> dict:
        """Search the device's media index by name, newest first: images, videos, audio and
        documents (downloads included). kind: image | video | audio | document | any. Returns
        content:// URIs for open_file (limit default 10, cap 25). With path, searches that
        shared-storage folder by file name instead (any file type)."""
        if kind not in ("image", "video", "audio", "document", "any"):
            fail("invalid_argument", "kind must be image, video, audio, document or any")
        session = get_session(rt, device)
        if path is None:
            files = await media_index(session, query, kind, min(max(limit, 1), 25))
            return {"status": "ok", "count": len(files), "files": files}
        root = safe_path(path)
        cmd = (
            f"find -L {q(root)} -maxdepth {int(max_depth)} -iname {q('*' + query + '*')} "
            f"2>/dev/null | head -n {int(limit)}"
        )
        found = parse_find(await session.shell(cmd, timeout=60))
        return {"status": "ok", "root": root, "count": len(found), "files": found}

    @mcp.tool(tags={"write"})
    async def open_file(
        uri: str | None = None, path: str | None = None, device: Device = None
    ) -> dict:
        """Open a file in its default viewer. uri: a content://media/... URI from find_files
        (never build one by hand); path: a file under shared storage."""
        session = get_session(rt, device)
        if uri:
            if not uri.startswith("content://media/"):
                fail("not_permitted", "only content://media/ URIs from find_files are accepted")
            rows = parse_content_rows(
                await session.shell(
                    f"content query --uri {q(uri)} --projection mime_type:_display_name",
                    check=False,
                ),
                ("mime_type", "_display_name"),
            )
            if not rows:
                fail("element_not_found", f"{uri} does not exist", "call find_files again")
            mime = rows[0].get("mime_type") or "*/*"
            args = (
                f"-a android.intent.action.VIEW -d {q(uri)} -t {q(mime)} "
                "--grant-read-uri-permission"
            )
            info = {"action": "open_file", "uri": uri, "mime": mime}
        elif path:
            clean = safe_path(path)
            mime = mimetypes.guess_type(clean)[0] or "*/*"
            args = f"-a android.intent.action.VIEW -d {q('file://' + clean)} -t {q(mime)}"
            info = {"action": "open_file", "path": clean, "mime": mime}
        else:
            fail("invalid_argument", "give uri (from find_files) or path")
        return await mutate(
            session,
            lambda: start_intent(session, args),
            info,
            settle_timeout=15.0,
            expect_change=True,
        )
