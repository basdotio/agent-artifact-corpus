"""MCP tools/call handling: validation, fan-out to the bridge, and rendering
of bridge results into MCP content blocks.

Octop speaks MCP; the bridge speaks the plain {id, method, params} protocol.
This module is the translation layer, including the security checks the server
owns: per-user session isolation (enforced by SessionRegistry keying),
the admin kill-switch, write-tool gating, and payload size sanity checks on
results coming back from the client (never trust the far end).
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import time
from typing import Any

from .audit import AuditLog
from .config import Settings
from .errors import (
    BridgeProtocolError,
    CODE_INTERNAL,
    CODE_INVALID_PARAMS,
    CODE_NO_BRIDGE,
    CODE_NOT_ALLOWED,
    CODE_TOO_LARGE,
)
from .protocol import (
    M_CREATE_DIRECTORY,
    M_DELETE_FILE,
    M_DELIVER_TO_LOCAL,
    M_EDIT_FILE,
    M_FETCH_TO_CLOUD,
    M_GET_FILE_INFO,
    M_LIST_ALLOWED_DIRECTORIES,
    M_LIST_DIRECTORY,
    M_LIST_DIRECTORY_WITH_SIZES,
    M_DIRECTORY_TREE,
    M_MOVE_FILE,
    M_READ_FILE,
    M_READ_MEDIA_FILE,
    M_READ_MULTIPLE_FILES,
    M_REMOVE_DIRECTORY,
    M_SEARCH_FILES,
    M_TRANSFER_STATUS,
    M_UNZIP_FILE,
    M_WRITE_FILE,
    M_ZIP_FILES,
    READ_ONLY_TOOLS,
    WRITE_TOOLS,
    validate_tool_name,
)
from .sessions import SessionRegistry

logger = logging.getLogger("localoctop.tools")

# Hard ceiling on a rendered MCP text block, independent of client config, so
# a compromised/buggy client cannot make us relay arbitrarily large payloads.
# v0.5.0: raised to 48 MiB to match the frame ceiling so one-shot media/zip
# transfers (30 MB raw -> ~40 MB base64) survive the relay; per-tool caps still
# apply on the client (MaxReadBytes/MaxMediaBytes), this is the outer bound.
SERVER_MAX_RESULT_BYTES = 48 * 1024 * 1024

# Timeout budget: the platform's MCP client times out a single request at
# 30s (langchain-mcp-adapters default), so the adapter's overall response to
# one tools/call must land well within that. The bridge round-trip itself is
# capped at settings.bridge_timeout (≤18s); this outer bound also covers
# validation, rendering and audit overhead, so the connector never waits
# past the budget.
ADAPTER_RESPONSE_BUDGET = 25.0

# Experiment branch. Everything a tool returns is fed to the model verbatim,
# so the ceiling that matters is the model's context, not the network frame.
# 64 KiB of text is roughly 15-25K tokens. Anything larger is cut on a line
# boundary with a note on how to narrow the request.
MODEL_RESULT_CAP_BYTES = int(os.environ.get("LOCALOCTOP_MODEL_RESULT_CAP", 64 * 1024))
# How long one fetch/deliver/status call waits for the transfer before
# answering "IN PROGRESS" — the platform MCP client times out one request at
# 30s, so this keeps a 10s margin inside it (and inside the response budget).
TRANSFER_WAIT_SECONDS = float(os.environ.get("LOCALOCTOP_TRANSFER_WAIT", 20))
TRANSFER_TOOLS = (M_FETCH_TO_CLOUD, M_DELIVER_TO_LOCAL, M_TRANSFER_STATUS)


# --- error-text enrichment (T5-2) -------------------------------------------
# Every error string that comes back from the employee's machine (or is
# produced here for routing problems) must tell the model TWO things: what
# happened, and what to do next (which tool, with which arguments). The
# enrichment lives HERE, on the server, so a new adapter paired with an old
# client program still produces actionable text — the old client's bare
# messages are recognised and extended, never merely relayed.
#
# Matching is wording-based because that is all an old client gives us. The
# patterns below cover every message the current Go client emits (pathguard.go
# / tools.go / tools_ext.go / transfer.go) plus the server's own refusals.

def _next_step_for_error(message: str) -> str:
    """Append a concrete next step to a bare client error message. Messages
    that already carry guidance ('Next step:' / 'What you can do') are returned
    unchanged, as are messages no rule recognises (they get a generic fallback
    so the model is never left with a bare cause)."""
    m = message.strip()
    low = m.lower()
    if "next step" in low or "what you can do" in low or "call transfer_status" in low \
            or "start it again" in low or "try again" in low:
        return m
    if "file not found" in low or "path not found" in low or "directory not found" in low \
            or "folder not found" in low or "search root not found" in low:
        return (m + " Next step: call list_directory on the containing folder to see the "
                "names actually there, or search_files with the file name to find it.")
    if "cloud file not found" in low:
        return (m + " Next step: cloud_path is the absolute path as YOU see it on the cloud "
                "machine (starting with '/'); list the folder in the cloud with your own tools "
                "(execute) to see the names actually there.")
    if "path is a directory" in low or "destination is a directory" in low:
        return (m + " Next step: call list_directory on it to see what is inside; if you need "
                "the whole folder, call fetch_to_cloud with the folder path.")
    if "path is not a directory" in low or "must be a directory" in low:
        return (m + " Next step: use get_file_info to check what the path actually is, or "
                "list_directory on its parent folder.")
    if "path traversal" in low or "escapes the whitelist" in low or "outside the whitelist" in low:
        return (m + " Next step: call list_allowed_directories to see the allowed folders, "
                "and give the path relative to one of them (e.g. \"docs/report.pdf\").")
    if "must not be absolute" in low or "must not contain a drive letter" in low \
            or "must not be a unc path" in low:
        return (m + " Next step: give the path relative to an allowed folder "
                "(e.g. \"docs/report.pdf\"); call list_allowed_directories to see the roots.")
    if "nul byte" in low:
        return m + " Next step: re-issue the call with a plain path (no NUL bytes)."
    if "already exists" in low:
        if "never overwrites" in low:
            # move_file has no overwrite parameter at all — never send the
            # model looking for one.
            return (m + " Next step: choose a different destination name, or — if the user "
                    "explicitly asked to replace the existing file — call delete_file on the "
                    "destination first (it goes to the recycle bin), then move again.")
        return (m + " Next step: choose a different name, or pass overwrite=true only if the "
                "user explicitly asked to replace the existing file.")
    if "not empty" in low and "recursive" in low:
        return m + " Next step: pass recursive=true, or list_directory first to see what is inside."
    if "not a valid zip" in low:
        return (m + " Next step: check with get_file_info that the path really is a zip archive; "
                "to read what is inside without extracting, fetch_to_cloud it and inspect it in "
                "the cloud with your own tools.")
    if "escapes destination" in low:
        return m + " Next step: the archive is not safe to extract; tell the user instead of retrying."
    if "recycle bin" in low:
        return m  # the recycle-bin refusals already carry their own next step
    if "exceeds" in low and ("limit" in low or "byte" in low):
        return (m + " Next step: use fetch_to_cloud to copy the file to the cloud machine and "
                "process it there with your own tools instead.")
    if "utf-8" in low or "not directly readable text" in low or "invalid base64" in low:
        return (m + " Next step: use fetch_to_cloud to copy the file to the cloud machine and "
                "process it there with your own tools.")
    if "write operations are disabled" in low or "does not allow" in low:
        return (m + " Next step: tell the user this action needs write access enabled "
                "(on their computer's localoctop switch), or do it a read-only way.")
    if "unknown tool" in low or "unknown method" in low:
        return (m + " Next step: the localoctop program on the user's computer is likely an "
                "older version — ask the user to update it.")
    if "whitelist root" in low:
        return m + " Next step: choose a folder inside the whitelist root, not the root itself."
    if "same path" in low:
        return m + " Next step: choose a different destination name."
    if "own subtree" in low:
        return m + " Next step: choose a destination outside the folder being moved."
    if "not found" in low:
        return (m + " Next step: call list_directory on the containing folder to see the "
                "names actually there, or search_files to find it by name.")
    # Unrecognised: never leave the model with a bare cause.
    return (m + " Next step: if the fix is not obvious from this message, tell the user "
            "what was attempted and this reason — do not retry blindly.")


def _strip_machine_paths(text: str, allowed_dirs: list[str]) -> str:
    """T5-3: an error text must never carry an absolute path of the employee's
    machine. Replace every known whitelist root (and common drive-letter /
    home-dir forms) with a neutral placeholder. The text stays truthful —
    paths the client already made relative are untouched."""
    out = text
    for root in allowed_dirs:
        if root:
            out = out.replace(root, "<allowed folder>")
            out = out.replace(root.replace("/", "\\"), "<allowed folder>")
    return out



def _req_path(arguments: dict[str, Any]) -> str:
    """Pick the most meaningful path-ish value for audit logging across the
    v0.5.0 tool parameter names (path/source/archive/paths[0]/pattern)."""
    for key in ("path", "source", "archive"):
        v = arguments.get(key)
        if isinstance(v, str) and v:
            return v
    paths = arguments.get("paths")
    if isinstance(paths, list) and paths:
        first = paths[0]
        if isinstance(first, str):
            return first
    v = arguments.get("pattern")
    if isinstance(v, str):
        return v
    return ""


class ToolService:
    """Executes MCP tool calls against a user's bridge session."""

    def __init__(self, settings: Settings, registry: SessionRegistry, audit: AuditLog):
        self.settings = settings
        self.registry = registry
        self.audit = audit
        self.transfers = None  # TransferManager, attached by create_app

    async def call_tool(self, user_id: str, pair_id: str, name: str,
                        arguments: dict[str, Any] | None) -> dict[str, Any]:
        """Run one tools/call. Returns the MCP result object
        ({"content": [...], "isError": bool}).

        v0.6.1: `pair_id` is the strict pair of the authenticated mcp token;
        routing resolves to the bridge session registered with THAT pair
        (registry.require_paired / call_paired) — same-name cross-pair
        fallback does not exist. `pair_id=""` falls back to the legacy
        user-name resolution; only reachable from non-pairing entry points
        (kept so hand-built test/ops call paths keep working).

        Raises BridgeProtocolError for auth/routing/protocol problems; tool-
        level failures (denied path, missing file, ...) are returned as
        isError results, per the MCP spec (they are not protocol errors).
        """
        started = time.monotonic()
        arguments = arguments if isinstance(arguments, dict) else {}
        req_path = _req_path(arguments)[:512]

        # --- server-side gates -------------------------------------------
        if self.settings.disabled:
            await self._audit(user_id, name, req_path, "deny", CODE_NOT_ALLOWED,
                              "connector disabled by administrator", started)
            raise BridgeProtocolError(CODE_NOT_ALLOWED, "localoctop connector is disabled by the administrator")

        write_enabled = self.settings.user_can_write(user_id)
        try:
            validate_tool_name(name, write_enabled)
        except BridgeProtocolError as exc:
            await self._audit(user_id, name, req_path, "deny", exc.code, exc.message, started)
            raise

        # Checking on a transfer must work while the machine is offline: that
        # is exactly when the model needs to be told what is going on.
        if name == M_TRANSFER_STATUS:
            return await self._transfer_tool(user_id, pair_id, name, arguments, req_path, started, "")

        # Extra gate: even when the server allows writes, the client session
        # must also have registered with write support (both switches matter).
        try:
            session = (self.registry.require_paired(user_id, pair_id) if pair_id
                       else self.registry.require(user_id))
        except BridgeProtocolError as exc:
            if exc.code == CODE_NO_BRIDGE:
                await self._audit(user_id, name, req_path, "deny", exc.code, exc.message, started)
                return self._error_result(
                    "The user's computer is not connected right now (it is off, asleep, offline, or the "
                    "localoctop client is not running). Nothing was done. Ask the user to open "
                    "localoctop on their computer, then try again.")
            raise
        if name in WRITE_TOOLS and not session.write_enabled:
            await self._audit(user_id, name, req_path, "deny", CODE_NOT_ALLOWED,
                              "client session has writes disabled", started, session.client_id)
            return self._error_result(f"the connected client does not allow {name} (write switch off on the machine)")

        # Payload size sanity for writes before they even hit the wire.
        if name == M_WRITE_FILE:
            content = arguments.get("content")
            if not isinstance(content, str):
                raise BridgeProtocolError(CODE_INVALID_PARAMS, "write_file requires string 'content'")
            approx = len(content)
            limit = self.settings.max_write_bytes * 2  # base64 inflates ~4/3
            if approx > limit:
                await self._audit(user_id, name, req_path, "deny", CODE_TOO_LARGE,
                                  f"content {approx}B exceeds limit", started, session.client_id)
                return self._error_result(f"content exceeds the {self.settings.max_write_bytes}-byte write limit")

        if name in TRANSFER_TOOLS:
            return await self._transfer_tool(user_id, pair_id, name, arguments, req_path, started,
                                             session.client_id)

        # --- fan out to the bridge ----------------------------------------
        # read_file is served by the bridge's bounded, line-based reader.
        method = "read_text" if name == M_READ_FILE else name
        try:
            if pair_id:
                result = await self.registry.call_paired(
                    user_id, pair_id, method, arguments, timeout=self.settings.bridge_timeout)
            else:
                result = await self.registry.call(
                    user_id, method, arguments, timeout=self.settings.bridge_timeout)
        except BridgeProtocolError as exc:
            decision = "error" if exc.code == CODE_INTERNAL else "deny"
            await self._audit(user_id, name, req_path, decision, exc.code, exc.message,
                              started, session.client_id)
            # Surface client-side denials as isError content (tool failure),
            # and routing/protocol failures as MCP protocol errors.
            if exc.code in (CODE_INTERNAL,):
                raise
            return self._error_result(self._enrich_error(exc.message))

        rendered = self._cap(name, self._render(name, result))
        await self._audit(user_id, name, req_path, "allow", 0, "", started, session.client_id)
        return rendered

    async def _transfer_tool(self, user_id: str, pair_id: str, name: str, arguments: dict[str, Any],
                             req_path: str, started: float, client_id: str) -> dict[str, Any]:
        """fetch_to_cloud / deliver_to_local / transfer_status. The reply is
        always a few lines of status text — never file content."""
        tm = self.transfers
        if tm is None:
            return self._error_result("file transfer is not configured on this server")
        try:
            if name == M_TRANSFER_STATUS:
                t = tm.get_for_user(user_id, str(arguments.get("transfer_id", "")))
            elif name == M_FETCH_TO_CLOUD:
                path = arguments.get("path")
                if not isinstance(path, str) or not path:
                    raise BridgeProtocolError(CODE_INVALID_PARAMS, "fetch_to_cloud requires 'path'")
                t = await tm.start_upload(user_id, pair_id, path, force=bool(arguments.get("force")))
            else:
                cloud_path = arguments.get("cloud_path")
                if not isinstance(cloud_path, str) or not cloud_path:
                    raise BridgeProtocolError(CODE_INVALID_PARAMS, "deliver_to_local requires 'cloud_path'")
                t = await tm.start_download(user_id, pair_id, cloud_path, str(arguments.get("path") or ""),
                                            bool(arguments.get("overwrite")))
            # Whatever starting the transfer already cost (e.g. hashing a big
            # cloud file) comes out of the wait, so the whole call stays in budget.
            await tm.wait(t, max(1.0, TRANSFER_WAIT_SECONDS - (time.monotonic() - started)))
        except BridgeProtocolError as exc:
            await self._audit(user_id, name, req_path, "deny", exc.code, exc.message, started, client_id)
            return self._error_result(self._enrich_error(exc.message))
        text = tm.describe(t)
        await self._audit(user_id, name, req_path or t.local_path, "error" if t.state == "failed" else "allow",
                          0, f"{t.direction} {t.state} {t.received}/{t.size}", started, client_id)
        # A limit advisory is a normal answer with a way forward, not an error —
        # and so is a folder fetch that only partly succeeded (its text carries
        # the failures and the way to continue).
        return {"content": [{"type": "text", "text": text}], "isError": t.is_error()}

    def _cap(self, name: str, rendered: dict[str, Any]) -> dict[str, Any]:
        """Last line of defence: no tool result larger than the model can
        reasonably take, and no embedded binary, whatever the bridge sent.
        Hitting a limit is NOT an error: the answer is a normal result that
        keeps what fits and explains the way forward."""
        total = 0
        for block in rendered.get("content", []):
            if block.get("type") != "text":
                return {"content": [{"type": "text", "text": (
                    f"{name} produced binary content, which cannot be shown in the conversation. "
                    "Use fetch_to_cloud to copy the file to the cloud machine and process it there "
                    "with your own file and command-line tools.")}], "isError": False}
            total += len(str(block.get("text", "")).encode("utf-8", "replace"))
        if total <= MODEL_RESULT_CAP_BYTES:
            return rendered
        # Keep the head that fits: cut on a character boundary (never half a
        # multi-byte character) and then on a line boundary, with a closing
        # note saying how much was dropped and how to narrow the request.
        budget = MODEL_RESULT_CAP_BYTES - 512
        out_blocks: list[dict[str, Any]] = []
        kept = 0
        for block in rendered.get("content", []):
            text = str(block.get("text", ""))
            data = text.encode("utf-8", "replace")
            if kept + len(data) > budget:
                take = max(budget - kept, 0)
                part = data[:take].decode("utf-8", "ignore")
                # Drop the last, possibly partial line so nothing shown is cut mid-line.
                nl = part.rfind("\n")
                if nl >= 0:
                    part = part[:nl]
                else:
                    part = ""
                if part:
                    out_blocks.append({"type": "text", "text": part})
                    kept += len(part.encode("utf-8"))
                break
            out_blocks.append(block)
            kept += len(data)
        if not out_blocks:
            out_blocks.append({"type": "text", "text": ""})
        # The "next step" depends on what the tool was showing: a listing,
        # a search or a tree is narrowed by scoping; edit_file's outcome
        # (applied / failed to match) is stated by the result itself, so the
        # note only says the output was cut — it must not claim success or
        # failure; anything else gets the generic narrowing advice. None of
        # these call the shown part the complete result.
        if name in (M_LIST_DIRECTORY, M_LIST_DIRECTORY_WITH_SIZES, M_SEARCH_FILES, M_DIRECTORY_TREE):
            hint = ("Narrow the request: point at a sub-directory, lower depth/limit, use a more "
                    "specific pattern or add excludePatterns.")
        elif name == M_EDIT_FILE:
            hint = "The output was too long and only the first part is shown."
        else:
            hint = "The output was too long and only the first part is shown; narrow the request."
        # Two numbers, always: how big the full answer was AND how much of it
        # is actually shown above (the kept head, in bytes) — "the first part"
        # alone leaves the model guessing how much it is missing.
        note = (f"[result too large to show in full: {total:,} bytes in total, "
                f"{kept:,} bytes shown above. {hint}]")
        out_blocks.append({"type": "text", "text": note})
        return {"content": out_blocks, "isError": False}

    # --- rendering ---------------------------------------------------------

    def _render(self, name: str, result: Any) -> dict[str, Any]:
        """Convert a bridge result payload into MCP content blocks."""
        if not isinstance(result, dict):
            raise BridgeProtocolError(CODE_INTERNAL, f"bridge returned non-object result for {name}")

        if name == M_READ_FILE:
            return self._render_read(result)
        if name == M_READ_MEDIA_FILE:
            return self._render_media(result)
        if name == M_ZIP_FILES:
            return self._render_zip(result)
        if name == M_READ_MULTIPLE_FILES:
            return self._render_multi(result)
        if name == M_EDIT_FILE:
            return self._render_edit(result)
        if name == M_UNZIP_FILE:
            return self._render_unzip(result)
        if name in (M_LIST_DIRECTORY, M_LIST_DIRECTORY_WITH_SIZES):
            return self._render_listing(result)
        if name == M_SEARCH_FILES:
            return self._render_search(result)
        if name == M_DIRECTORY_TREE:
            return self._render_tree(result)
        return self._render_json(result)

    # Listings are rendered one entry per line (a quarter of the size of the
    # indented JSON) and cut at the budget with an explicit "N more not
    # shown" — a big folder gives a useful partial answer, not a refusal.
    def _lines_result(self, header: str, lines: list[str], hint: str) -> dict[str, Any]:
        budget = MODEL_RESULT_CAP_BYTES - 1024
        out, used = [header], len(header.encode("utf-8")) + 1
        shown = 0
        for line in lines:
            size = len(line.encode("utf-8", "replace")) + 1
            if used + size > budget:
                break
            out.append(line)
            used += size
            shown += 1
        if shown < len(lines):
            out.append(f"[… {len(lines) - shown} more not shown (showing the first {shown} of {len(lines)}). {hint}]")
        elif not lines:
            out.append("(nothing found)")
        return {"content": [{"type": "text", "text": "\n".join(out)}], "isError": False}

    @staticmethod
    def _entry_line(e: dict[str, Any], name_key: str = "name") -> str:
        is_dir = str(e.get("type", "")).startswith("dir")
        size = "-" if is_dir else f"{int(e.get('size', 0)):,}"
        mtime = str(e.get("mtime", ""))[:16].replace("T", " ")
        return f"{'d' if is_dir else 'f'}  {size:>15}  {mtime}  {e.get(name_key, '')}{'/' if is_dir else ''}"

    def _render_listing(self, result: dict[str, Any]) -> dict[str, Any]:
        entries = [e for e in result.get("entries", []) if isinstance(e, dict)]
        head = f"== {result.get('path', '')}: {len(entries)} entries (type, size in bytes, modified UTC, name) =="
        truncated_note = ""
        if "total_bytes" in result:
            # list_directory_with_sizes. T5-4: when the walk was cut at the
            # internal cap, the totals count only what was LISTED — quoting
            # them as the folder's totals is exactly the defect the tester
            # hit ("totals: 5000 files" for a 6000-file folder).
            head += (f"\ntotals of the {len(entries)} listed entries: "
                     f"{result.get('total_files', 0)} files, {result.get('total_dirs', 0)} folders, "
                     f"{int(result.get('total_bytes', 0)):,} bytes")
            if result.get("truncated") or (result.get("totals_count_all") is False):
                seen = result.get("total_entries_seen") or len(entries)
                truncated_note = (f"[NOT the whole folder: only the first {len(entries)} entries are "
                                  f"listed and counted; the folder holds more than {seen} entries in "
                                  f"total. Next step: list a sub-folder, or use search_files with a "
                                  f"pattern to find what you need.]")
            elif result.get("totals_count_all"):
                head = f"== {result.get('path', '')}: {len(entries)} entries (type, size in bytes, modified UTC, name) ==" + \
                       (f"\ntotals: {result.get('total_files', 0)} files, {result.get('total_dirs', 0)} folders, "
                        f"{int(result.get('total_bytes', 0)):,} bytes")
        else:
            # list_directory. T5-4: truncation must be stated, with the exact
            # total when the client counted it, a lower bound otherwise; and
            # with an OLD client (no truncation fields at all) a count equal
            # to a round cap must read as "maybe incomplete", never "all".
            if "truncated" in result or "total_known" in result:
                if result.get("truncated"):
                    if result.get("total_known"):
                        more = f"the folder holds {result.get('total_entries', 0):,} entries in total"
                    else:
                        more = (f"the folder holds at least {int(result.get('total_entries', 0)):,} entries "
                                f"(the full count was not taken)")
                    truncated_note = (f"[NOT the whole listing: only the first {len(entries)} entries are "
                                      f"shown; {more}. Next step: list a sub-folder, lower depth, or use "
                                      f"search_files with a pattern.]")
            else:
                # Old client: no truncation fields at all. The count hitting
                # a plausible cap (the tool's default 500 or the 2000 max) is
                # the only signal left — take it, and say "may" not "is".
                lim = result.get("limit") or 0
                at_cap = len(entries) >= lim if lim else len(entries) in (500, 1000, 2000)
                if at_cap and len(entries) > 0:
                    cap_word = lim or len(entries)
                    truncated_note = (f"[This may NOT be the whole listing: the entry count reached "
                                      f"{cap_word}, and this version of the localoctop program does "
                                      f"not say whether there are more. Next step: list a sub-folder, or "
                                      f"use search_files with a pattern.]")
        out = self._lines_result(head, [self._entry_line(e) for e in entries],
                                 "List a sub-folder, or use search_files with a pattern.")
        if truncated_note:
            out["content"].append({"type": "text", "text": truncated_note})
        return out

    def _render_search(self, result: dict[str, Any]) -> dict[str, Any]:
        lines = []
        for m in result.get("matches", []):
            if not isinstance(m, dict):
                continue
            line = self._entry_line({**m, "type": "file"}, "path")
            if m.get("line"):
                line += f"\n      L{m['line']}: {str(m.get('preview', ''))[:200]}"
            lines.append(line)
        head = f"== search {result.get('pattern', '')!r} in {result.get('path', '')}: {len(lines)} match(es) =="
        notes: list[str] = []
        if result.get("truncated"):
            notes.append("the search stopped at its match limit — there may be more")
        # T5-4: content search silently skipping very large files made a
        # real "0 matches" answer indistinguishable from "the file with the
        # match was never opened". Own up to every skip.
        skipped = int(result.get("skipped_large") or 0)
        if skipped:
            names = [str(n) for n in (result.get("skipped_large_names") or [])][:10]
            skip_limit = int(result.get("skipped_large_limit") or 0)
            if skip_limit > 0:
                # Name the real line the client skipped at (its MaxReadBytes),
                # so the model never has to guess the size limit.
                limit_txt = f"{skip_limit / (1024 * 1024):g} MiB ({skip_limit:,} bytes)"
            else:
                # Older clients do not report the limit; stay truthful.
                limit_txt = "the client's read limit"
            note = (f"{skipped} file(s) were NOT searched inside because they are larger than "
                    f"{limit_txt}")
            if names:
                note += ": " + ", ".join(names) + (" …" if skipped > len(names) else "")
            note += (". To search inside them, fetch_to_cloud the file(s) and search with "
                     "command-line tools (execute) in the cloud.")
            notes.append(note)
            if not lines:
                # "0 matches" is only honest when everything was searched.
                head += "\n(matches were NOT ruled out in the skipped file(s))"
        # T5: files/folders that could not be read were never searched; a
        # "0 matches" answer must not imply they were.
        unreadable = int(result.get("unreadable") or 0)
        if unreadable:
            unames = [str(n) for n in (result.get("unreadable_names") or [])][:10]
            unote = f"{unreadable} file(s)/folder(s) could not be read and were NOT searched"
            if unames:
                unote += ": " + ", ".join(unames) + (" …" if unreadable > len(unames) else "")
            notes.append(unote)
            if not lines:
                head += "\n(matches were NOT ruled out in the unreadable file(s))"
        if notes:
            head += "\n(" + "; ".join(notes) + ")"
        return self._lines_result(head, lines, "Use a more specific pattern or search a sub-folder.")

    def _render_tree(self, result: dict[str, Any]) -> dict[str, Any]:
        lines: list[str] = []

        def walk(nodes: Any, depth: int) -> None:
            for n in nodes or []:
                if not isinstance(n, dict):
                    continue
                is_dir = str(n.get("type", "")).startswith("dir")
                lines.append(f"{'  ' * depth}{n.get('name', '')}{'/' if is_dir else ''}")
                walk(n.get("children"), depth + 1)

        walk(result.get("tree"), 0)
        head = f"== tree of {result.get('path', '')}: {len(lines)} entries =="
        if result.get("truncated"):
            head += "\n(the tree was cut at its node limit)"
        return self._lines_result(head, lines, "Ask for the tree of a sub-folder, or add excludePatterns.")

    def _b64_blob(self, result: dict[str, Any], field: str = "base64") -> str:
        b64 = result.get(field, "")
        if not isinstance(b64, str):
            raise BridgeProtocolError(CODE_INTERNAL, f"bad {field} field from bridge")
        try:
            raw = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise BridgeProtocolError(CODE_INTERNAL, f"bridge sent invalid base64: {exc}") from exc
        if len(raw) > SERVER_MAX_RESULT_BYTES:
            raise BridgeProtocolError(CODE_TOO_LARGE, "bridge result exceeds server size ceiling")
        return b64

    def _render_media(self, result: dict[str, Any]) -> dict[str, Any]:
        """read_media_file: base64 + MIME go back as an embedded resource."""
        b64 = self._b64_blob(result)
        mime = str(result.get("mime") or "application/octet-stream")
        uri = "file:///" + str(result.get("path", "blob")).lstrip("/")
        return {
            "content": [
                {"type": "resource", "resource": {"uri": uri, "mimeType": mime, "blob": b64}},
                {"type": "text", "text": f"media file: {result.get('path', '')} ({result.get('size', 0)} bytes, {mime})"},
            ],
            "isError": False,
        }

    def _render_zip(self, result: dict[str, Any]) -> dict[str, Any]:
        """zip_files: the archive comes back base64'd as a resource blob."""
        b64 = self._b64_blob(result)
        note = f"zip archive: {result.get('entries', 0)} entries, {result.get('size', 0)} bytes"
        if result.get("skipped"):
            note += f", {result['skipped']} skipped"
        if result.get("truncated"):
            note += " (truncated by caps)"
        archive = str(result.get("archive") or "").strip("/")
        if not archive:
            archive = "bundle.zip"
        uri = "file:///" + archive
        return {
            "content": [
                {"type": "resource", "resource": {"uri": uri, "mimeType": "application/zip", "blob": b64}},
                {"type": "text", "text": note},
            ],
            "isError": False,
        }

    def _render_multi(self, result: dict[str, Any]) -> dict[str, Any]:
        """read_multiple_files: one text block per file (official style),
        failures and truncation summarised at the end."""
        blocks: list[dict[str, Any]] = []
        for f in result.get("files", []):
            if not isinstance(f, dict):
                continue
            if f.get("error"):
                blocks.append({"type": "text", "text": f"== {f.get('path', '')} — ERROR: {f['error']} =="})
                continue
            if f.get("encoding") == "base64":
                b64 = str(f.get("base64", ""))
                if len(base64.b64decode(b64, validate=False) or b"") > SERVER_MAX_RESULT_BYTES:
                    raise BridgeProtocolError(CODE_TOO_LARGE, "bridge result exceeds server size ceiling")
                blocks.append({"type": "resource", "resource": {
                    "uri": "file:///" + str(f.get("path", "blob")).lstrip("/"),
                    "mimeType": "application/octet-stream", "blob": b64}})
            else:
                text = str(f.get("text", ""))
                if len(text.encode("utf-8", "replace")) > SERVER_MAX_RESULT_BYTES:
                    raise BridgeProtocolError(CODE_TOO_LARGE, "bridge result exceeds server size ceiling")
                blocks.append({"type": "text", "text": f"== {f.get('path', '')} ==\n{text}"})
        tail = []
        if result.get("failed"):
            tail.append(f"{result['failed']} file(s) failed")
        if result.get("truncated"):
            tail.append("combined size cap reached — remaining files omitted")
        if tail:
            blocks.append({"type": "text", "text": "note: " + "; ".join(tail)})
        if not blocks:
            blocks.append({"type": "text", "text": "(no files returned)"})
        return {"content": blocks, "isError": False}

    def _render_edit(self, result: dict[str, Any]) -> dict[str, Any]:
        """edit_file: the unified diff is the human-consumable core."""
        head = ("[dry run] " if result.get("dry_run") else "") + \
               f"edit_file {result.get('path', '')}: " + \
               f"{result.get('edits_applied', 0)} edit(s), {result.get('matches', 0)} match(es), " + \
               f"{result.get('size_before', 0)} -> {result.get('size_after', 0)} bytes"
        diff = str(result.get("diff", ""))
        text = head + "\n" + diff
        if len(text.encode("utf-8", "replace")) > SERVER_MAX_RESULT_BYTES:
            raise BridgeProtocolError(CODE_TOO_LARGE, "bridge result exceeds server size ceiling")
        return {"content": [{"type": "text", "text": text}], "isError": False}

    def _render_read(self, result: dict[str, Any]) -> dict[str, Any]:
        """read_file: a window of whole lines plus an explicit 'what next'.
        A file that is not readable text is a normal answer with the way
        forward (fetch_to_cloud), never an error."""
        not_text = result.get("not_text")
        if not_text:
            path = str(result.get("path", ""))
            size = int(result.get("size", 0))
            if not_text == "binary":
                why = "it is a binary file (it contains NUL bytes, like a PDF, image, Office document or archive)"
            else:
                # not_utf8: could be text in another encoding, but just as
                # often a binary format whose head simply has no NUL bytes
                # (a small PDF is the common case). Naming "a different
                # character encoding" would send the model off trying to
                # transcode a PDF — stay neutral.
                why = ("it is not directly readable text (a binary format such as PDF, Office, "
                       "image or archive, or text in an encoding other than UTF-8)")
            text = (f"== {path} ({size:,} bytes): cannot be shown as text — {why}. ==\n"
                    f"Nothing was read. Next step: call fetch_to_cloud with path={path!r} to copy the "
                    "file to the cloud machine, then process it there with your own file and "
                    "command-line tools (execute).")
            return {"content": [{"type": "text", "text": text}], "isError": False}
        text = result.get("text", "")
        if not isinstance(text, str):
            raise BridgeProtocolError(CODE_INTERNAL, "bad text field from bridge")
        path = result.get("path", "")
        start, end = int(result.get("start_line", 1)), int(result.get("end_line", 0))
        total = int(result.get("total_lines", -1))
        size = int(result.get("size", 0))
        # A text file over the platform's 10 MB line is not paged: the bridge
        # flags it large_file and only ever delivers the first screen. Later
        # windows arrive with no content — say so and point at fetch_to_cloud
        # (a normal answer, never an error).
        if result.get("large_file") and start > 1:
            big_text = (f"== {path} ({size:,} bytes): this file is larger than 10 MB, and read_file "
                        f"does not page files this big, so nothing was read. Next step: call "
                        f"fetch_to_cloud with path={path!r} to copy the file to the cloud machine, "
                        "then process it there with your own file and command-line tools (execute). ==")
            return {"content": [{"type": "text", "text": big_text}], "isError": False}
        of = f" of {total}" if total >= 0 else ""
        if end < start:
            head = f"== {path} ({size:,} bytes): no lines at {start}{of} =="
        else:
            head = f"== {path} ({size:,} bytes): lines {start}-{end}{of} =="
        if result.get("eof"):
            tail = "[end of file]"
        elif result.get("large_file"):
            tail = (f"[large file: this file is larger than 10 MB, so only this beginning part is "
                    f"shown and read_file will not page further into it. To work with the rest of "
                    f"the file, call fetch_to_cloud with path={path!r}, then process it on the "
                    "cloud machine with your own file and command-line tools.]")
        else:
            tail = (f"[not the whole file — next part: read_file with start_line={end + 1}. "
                    "To process the whole file, use fetch_to_cloud instead of paging.]")
        if result.get("clipped_lines"):
            tail += f" [{result['clipped_lines']} very long line(s) were clipped]"
        if text and not text.endswith(chr(10)):
            text += chr(10)
        return {"content": [{"type": "text", "text": head + chr(10) + text + tail}], "isError": False}

    def _render_unzip(self, result: dict[str, Any]) -> dict[str, Any]:
        """unzip_file: the plain summary PLUS, when members overwrote existing
        files, an explicit line saying their old versions went to the recycle
        bin (T5-5b — write_file/edit_file/delete_file all say this; unzip was
        the silent one). An old client sends no `recycled` field: then nothing
        is claimed either way."""
        blocks: list[dict[str, Any]] = []
        head = (f"unzip_file: extracted {result.get('extracted', 0)} file(s), "
                f"{int(result.get('total_bytes', 0)):,} bytes, into {result.get('dest', '')}")
        blocks.append({"type": "text", "text": head})
        recycled = [str(p) for p in (result.get("recycled") or [])][:20]
        if recycled:
            blocks.append({"type": "text", "text": (
                f"{len(recycled)} existing file(s) were overwritten; their previous versions were "
                f"moved to the recycle bin (recoverable by the user): " + ", ".join(recycled))})
        skipped = [str(s) for s in (result.get("skipped") or [])]
        if skipped:
            blocks.append({"type": "text", "text": (
                f"{len(skipped)} member(s) were NOT extracted (their originals are untouched): "
                + ", ".join(skipped[:20]) + (" …" if len(skipped) > 20 else ""))})
        return {"content": blocks, "isError": False}

    def _render_json(self, result: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(result, ensure_ascii=False, indent=1)
        if len(text.encode("utf-8", "replace")) > SERVER_MAX_RESULT_BYTES:
            raise BridgeProtocolError(CODE_TOO_LARGE, "bridge result exceeds server size ceiling")
        return {"content": [{"type": "text", "text": text}], "isError": False}

    def _enrich_error(self, message: str) -> str:
        """One place every client-produced error message passes through before
        reaching the model: absolute machine paths are scrubbed (T5-3) and a
        concrete next step is appended when the message lacks one (T5-2)."""
        roots: list[str] = []
        try:
            for s in getattr(self.registry, "_sessions", {}).values():
                roots.extend(getattr(s, "allowed_dirs", []) or [])
        except Exception:  # noqa: BLE001 - scrubbing is best effort
            pass
        return _next_step_for_error(_strip_machine_paths(message, roots))

    def _error_result(self, message: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": message}], "isError": True}

    async def _audit(self, user_id: str, method: str, path: str, decision: str,
                     code: int, detail: str, started: float, client_id: str = "") -> None:
        await self.audit.record(
            user_id=user_id,
            method=method,
            path=path,
            decision=decision,
            code=code,
            detail=detail,
            duration_ms=(time.monotonic() - started) * 1000,
            client_id=client_id,
        )


__all__ = [
    "ToolService",
    "SERVER_MAX_RESULT_BYTES",
    "READ_ONLY_TOOLS",
    "WRITE_TOOLS",
]
