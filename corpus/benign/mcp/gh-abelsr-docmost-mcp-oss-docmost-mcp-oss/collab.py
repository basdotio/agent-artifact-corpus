"""Writing the body of Docmost pages via the Yjs WebSocket.

Docmost stores page bodies in its **Hocuspocus** (Yjs) collaboration
server, not in the REST API: `/pages/create` and `/pages/update`
ignore `content`. This module implements the protocol so that the
**body of an already created page can be edited**.

Protocol (inferred from the frontend bundle and verified against a real
instance):

* URL: ``wss://<host>/collab``
* Document name: ``page.<pageId>``
* **Auth**: the token is the same ``accessToken`` returned by
  ``POST /api/auth/login``. The message is::

      varString(documentName) + varUint(2=Auth) + varUint(0=Token) + varString(token)

  The server replies ``varUint(2=Authenticated) + varString("read-write")``.

* **Sync**: ``varString(doc) + varUint(0=Sync) + <y-protocols message>`` where
  the y-protocols message is ``varUint(subtype) + varUint8Array(payload)``
  (0=SyncStep1 state vector, 1=SyncStep2 update, 2=Update).

* **Persistence to the database is debounced to 10 s**
  (``Hocuspocus({debounce: 10000, maxDebounce: 45000})``), so a change is
  not visible via REST until that time has passed.

Document format: an ``XmlFragment`` called ``default`` whose children are
elements named after the Tiptap node name (``paragraph``, ``heading``, ``codeBlock``,
``bulletList``, ``listItem``, ``blockquote``, ``table``...). **Marks**
(bold, italic, code...) **are not elements**: they are formatting attributes
over ranges of the ``XmlText``, e.g. ``xmltext.insert(0, "hello", {"bold": True})``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

try:
    from pycrdt import Doc, XmlElement, XmlFragment, XmlText
    from websockets.asyncio.client import connect as ws_connect
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Yjs support requires the extras: pip install 'docmost-mcp-oss[yjs]'"
    ) from exc

AUTH = 2
SYNC = 0
SYNC_STEP1 = 0
SYNC_STEP2 = 1
SYNC_UPDATE = 2
AUTH_TOKEN = 0

#: Docmost persists changes with a 10 s debounce (max 45 s).
DEFAULT_FLUSH_SECONDS = 13


# ---------------------------------------------------------------------- #
# Neutral representation of the content
# ---------------------------------------------------------------------- #
@dataclass
class Run:
    """A fragment of text with its marks (``{'bold': True}``, ...)."""

    text: str
    marks: dict[str, Any] = field(default_factory=dict)


@dataclass
class Block:
    """A document node (``tag`` = Tiptap node name)."""

    tag: str
    attrs: dict[str, Any] = field(default_factory=dict)
    runs: list[Run] = field(default_factory=list)
    children: list[Block] = field(default_factory=list)

    def text(self) -> str:
        return "".join(r.text for r in self.runs) + "".join(c.text() for c in self.children)


# ---------------------------------------------------------------------- #
# Encoding lib0 (varint / varstring)
# ---------------------------------------------------------------------- #
def write_var_uint(num: int) -> bytes:
    out = bytearray()
    while num > 0x7F:
        out.append(0x80 | (num & 0x7F))
        num >>= 7
    out.append(num)
    return bytes(out)


def write_var_string(value: str) -> bytes:
    encoded = value.encode()
    return write_var_uint(len(encoded)) + encoded


def read_var_uint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def read_var_string(data: bytes, pos: int) -> tuple[str, int]:
    length, pos = read_var_uint(data, pos)
    return data[pos : pos + length].decode("utf8", "replace"), pos + length


def read_var_uint8array(data: bytes, pos: int) -> tuple[bytes, int]:
    length, pos = read_var_uint(data, pos)
    return data[pos : pos + length], pos + length


# ---------------------------------------------------------------------- #
# Collaboration client
# ---------------------------------------------------------------------- #
class CollabError(RuntimeError):
    pass


class CollabClient:
    """Connection to the ``/collab`` WebSocket to read and replace a page's body.

    Example::

        async with CollabClient(url, access_token) as collab:
            await collab.open(page_id)
            blocks = await collab.read_blocks()
            await collab.replace_blocks([Block("paragraph", runs=[Run("hello")])])
            await collab.wait_for_persistence()
    """

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        host = self.base_url.split("://", 1)[-1]
        scheme = "wss" if self.base_url.startswith("https") else "ws"
        self.ws_url = f"{scheme}://{host}/collab"
        self.token = token
        self.timeout = timeout
        self._ws: Any = None
        self._doc: Doc | None = None
        self._document = ""
        self._server_state: bytes | None = None

    async def __aenter__(self) -> CollabClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # -- connection ----------------------------------------------------- #
    async def open(self, page_id: str) -> None:
        """Authenticates and syncs the page's document."""
        self._document = f"page.{page_id}"
        self._doc = Doc()
        self._ws = await ws_connect(
            self.ws_url,
            additional_headers={"Origin": self.base_url},
            max_size=None,
            open_timeout=self.timeout,
        )
        await self._ws.send(
            write_var_string(self._document)
            + write_var_uint(AUTH)
            + write_var_uint(AUTH_TOKEN)
            + write_var_string(self.token)
        )
        scope = await self._await_auth()
        if "write" not in scope:
            raise CollabError(f"No write permission on the page (scope={scope!r})")

        # SyncStep1 with an empty state vector -> the server sends everything.
        await self._ws.send(
            write_var_string(self._document)
            + write_var_uint(SYNC)
            + write_var_uint(SYNC_STEP1)
            + write_var_uint(1)
            + b"\x00"
        )
        await self._await_sync()

    async def _await_auth(self) -> str:
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
        _, pos = read_var_string(raw, 0)
        msg_type, pos = read_var_uint(raw, pos)
        if msg_type != AUTH:
            raise CollabError(f"Expected Auth, got message type {msg_type}")
        subtype, pos = read_var_uint(raw, pos)
        if subtype != 2:
            raise CollabError("Authentication rejected by the server")
        scope, _ = read_var_string(raw, pos)
        return scope

    async def _await_sync(self) -> None:
        assert self._doc is not None
        got_step1 = got_step2 = False
        for _ in range(10):
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
            _, pos = read_var_string(raw, 0)
            msg_type, pos = read_var_uint(raw, pos)
            if msg_type != SYNC:
                continue  # awareness, etc.
            subtype = raw[pos]
            payload, _ = read_var_uint8array(raw, pos + 1)
            if subtype == SYNC_STEP1:  # server's state vector
                self._server_state = payload
                got_step1 = True
            elif subtype == SYNC_STEP2:  # full document
                self._doc.apply_update(payload)
                got_step2 = True
            # Both are needed: the state vector (to compute the delta)
            # and the update with the content.
            if got_step1 and got_step2:
                return
        raise CollabError("Could not sync the document")

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    # -- reading --------------------------------------------------------- #
    @property
    def fragment(self) -> XmlFragment:
        assert self._doc is not None, "call open() first"
        return self._doc.get("default", type=XmlFragment)

    async def read_blocks(self) -> list[Block]:
        """Returns the current document structure in neutral form."""
        return [_block_from_node(child) for child in _children(self.fragment)]

    # -- writing --------------------------------------------------------- #
    async def replace_blocks(self, blocks: list[Block], *, mode: str = "replace") -> int:
        """Writes `blocks` into the document and sends the delta.

        `mode` decides what happens to the existing content, mirroring the
        `operation` field Docmost's own API documents for page updates:

        * ``"replace"`` — drop everything and write `blocks` (the default).
        * ``"append"`` — keep the content and add `blocks` at the end.
        * ``"prepend"`` — keep the content and add `blocks` at the start.

        Unlike the REST endpoint, these actually work: that one accepts
        `operation` and ignores it, because the body belongs to this document.

        Returns the number of bytes sent.
        """
        if mode not in ("replace", "append", "prepend"):
            raise ValueError("mode must be 'replace', 'append' or 'prepend'")
        assert self._doc is not None and self._server_state is not None
        fragment = self.fragment

        if mode == "replace":
            del fragment.children[:]

        # Rebuild. Important: the element must be integrated into the document
        # BEFORE touching its attributes or children.
        for offset, block in enumerate(blocks):
            _append_block(fragment, block, at=offset if mode == "prepend" else None)

        delta = self._doc.get_update(self._server_state)
        await self._ws.send(
            write_var_string(self._document)
            + write_var_uint(SYNC)
            + write_var_uint(SYNC_UPDATE)
            + write_var_uint(len(delta))
            + delta
        )
        return len(delta)

    async def wait_for_persistence(self, seconds: float = DEFAULT_FLUSH_SECONDS) -> None:
        """Waits for Docmost to persist to the database (10 s debounce)."""
        await asyncio.sleep(seconds)


# ---------------------------------------------------------------------- #
# Node <-> Block conversion
# ---------------------------------------------------------------------- #
def _children(node: Any) -> list[Any]:
    try:
        return list(node.children)
    except TypeError:
        return []


def _block_from_node(node: Any) -> Block:
    tag = getattr(node, "tag", None) or type(node).__name__
    block = Block(tag=tag, attrs=dict(getattr(node, "attributes", {}) or {}))
    for child in _children(node):
        if type(child).__name__ == "XmlText":
            for segment in child.diff():
                text, marks = segment if isinstance(segment, tuple) else (segment, None)
                block.runs.append(Run(text=text, marks=dict(marks or {})))
        else:
            block.children.append(_block_from_node(child))
    return block


def _append_block(parent: Any, block: Block, *, at: int | None = None) -> None:
    element = XmlElement(block.tag)
    if at is None:
        parent.children.append(element)  # integrates the node into the document
    else:
        parent.children.insert(at, element)
    for key, value in block.attrs.items():
        element.attributes[key] = value
    for run in block.runs:
        text = XmlText()
        element.children.append(text)
        text.insert(0, run.text, run.marks or None)
    for child in block.children:
        _append_block(element, child)


# ---------------------------------------------------------------------- #
# Markdown -> Blocks conversion using Docmost itself
# ---------------------------------------------------------------------- #
async def blocks_from_markdown(client: Any, space_id: str, markdown: str) -> list[Block]:
    """Converts Markdown to ``Block`` using Docmost's own converter.

    Instead of re-implementing the Tiptap schema, the Markdown is uploaded
    with ``/pages/import`` to a temporary page (the server converts it to
    ProseMirror), its Yjs document is read, and the temporary page is deleted.

    Advantage: supports everything Docmost supports (tables, lists, images,
    even .docx/.pdf), without re-implementing the schema.
    """
    from .client import API_PREFIX

    # Docmost uses the FIRST heading of the file as the page title and removes
    # it from the body. So that the user's Markdown arrives intact, we prepend
    # a marker heading that takes on that role.
    payload = f"# __docmost_mcp_oss_tmp__\n\n{markdown}"

    response = await client._client.post(
        f"{API_PREFIX}/pages/import",
        data={"spaceId": space_id},
        files={"file": ("tmp.md", payload.encode(), "text/markdown")},
        headers=client._headers(),
    )
    page = (response.json() or {}).get("data") or {}
    page_id = page.get("slugId") or page.get("id")
    if not page_id:
        raise CollabError("Could not create the temporary conversion page")

    try:
        async with CollabClient(client.base_url, client._bearer) as collab:
            await collab.open(page_id)
            return await collab.read_blocks()
    finally:
        await client.delete_page(page_id)


async def update_page_content(
    client: Any, page_id: str, markdown: str, *, mode: str = "replace"
) -> dict[str, Any]:
    """Writes the given Markdown into an existing page's body.

    This is the operation the REST API **cannot** do. It combines:

    1. Docmost's converter (via ``/pages/import`` on a temporary page),
    2. the write over the Yjs WebSocket,
    3. the wait for persistence (10 s debounce).

    Returns a summary with the bytes sent and the blocks written.
    """
    page = await client.request("/pages/info", {"pageId": page_id})
    space_id = (page or {}).get("spaceId")
    if not space_id:
        raise CollabError(f"Could not resolve the space for page {page_id}")

    blocks = await blocks_from_markdown(client, space_id, markdown)
    async with CollabClient(client.base_url, client._bearer) as collab:
        await collab.open(page_id)
        sent = await collab.replace_blocks(blocks, mode=mode)
        await collab.wait_for_persistence()

    return {
        "page_id": page_id,
        "mode": mode,
        "blocks": len(blocks),
        "bytes_sent": sent,
        "persisted": True,
    }


def blocks_to_markdown(blocks: list[Block]) -> str:
    """Approximate rendering to Markdown (for debugging or a preview)."""
    out: list[str] = []

    def render_runs(runs: list[Run]) -> str:
        parts = []
        for run in runs:
            text = run.text
            if run.marks.get("bold"):
                text = f"**{text}**"
            if run.marks.get("italic"):
                text = f"*{text}*"
            if run.marks.get("code"):
                text = f"`{text}`"
            if run.marks.get("strike"):
                text = f"~~{text}~~"
            parts.append(text)
        return "".join(parts)

    def walk(items: list[Block], indent: int = 0) -> None:
        pad = "  " * indent
        for block in items:
            if block.tag == "heading":
                out.append(f"{'#' * int(block.attrs.get('level', 1))} {render_runs(block.runs)}")
            elif block.tag == "paragraph":
                out.append(pad + render_runs(block.runs))
            elif block.tag == "codeBlock":
                out.append(f"```{block.attrs.get('language', '')}\n{block.text()}\n```")
            elif block.tag == "horizontalRule":
                out.append("---")
            elif block.tag == "blockquote":
                out.append(pad + "> " + render_runs(block.runs))
            elif block.tag in ("bulletList", "orderedList"):
                for i, item in enumerate(block.children, 1):
                    marker = "-" if block.tag == "bulletList" else f"{i}."
                    inner = item.children[0] if item.children else item
                    out.append(f"{pad}{marker} {render_runs(inner.runs)}")
                    if len(item.children) > 1:
                        walk(item.children[1:], indent + 1)
            else:
                text = render_runs(block.runs)
                if text:
                    out.append(pad + text)
                walk(block.children, indent)
            out.append("")

    walk(blocks)
    return "\n".join(out).strip()


__all__ = [
    "Block",
    "CollabClient",
    "CollabError",
    "Run",
    "blocks_from_markdown",
    "update_page_content",
    "blocks_to_markdown",
    "DEFAULT_FLUSH_SECONDS",
    "read_var_string",
    "read_var_uint",
    "write_var_string",
    "write_var_uint",
]
