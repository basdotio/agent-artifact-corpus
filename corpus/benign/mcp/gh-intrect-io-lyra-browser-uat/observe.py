"""What the page did on the wire and in its console while the persona drove it.

Written as JSON lines in the run directory so the report can count failed
requests and console errors, and so a step can be judged by the request that
actually left the browser — an analytics hit after a purchase, say — rather
than by what the page claimed. Requests matching the target's
``network_capture`` patterns are kept whole (query string, POST body); every
other request is a summary with query values stripped, because a URL can
carry a token and this file outlives the run.

Known limit (measured on the previous harness, 2026-10-04): in automated
Chrome a page reached by in-tab navigation often sends no analytics hit at all
and the previous page's pending hit is aborted. An absent event after a
navigation proves nothing; only events fired on the first page of a session
are reliable evidence of absence.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..origin import loggable_url

MAX_POST_CHARS = 4096
MAX_TEXT_CHARS = 500
_FLUSH_EVERY = 50


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class PageObservers:
    """Listeners for every tab of a run. ``attach`` goes on
    ``BrowserSession.page_observers``; the session calls it for each tab it adopts."""

    def __init__(self, run_dir: Path, *, capture_patterns: Iterable[str] = ()) -> None:
        self.network_path = run_dir / "network.jsonl"
        self.console_path = run_dir / "console.jsonl"
        self._patterns = [re.compile(p) for p in capture_patterns]
        self.counts: Counter[str] = Counter()
        self.matched: Counter[str] = Counter()
        self._pending: list[tuple[Path, dict[str, Any]]] = []
        self.attached_pages = 0

    # --- wiring -----------------------------------------------------------------

    def attach(self, page: Any) -> None:
        """Listen on one tab. Best effort: a fake without ``on`` is skipped."""
        handlers = {
            "request": self._on_request,
            "response": self._on_response,
            "requestfailed": self._on_request_failed,
            "console": self._on_console,
            "pageerror": self._on_page_error,
        }
        try:
            for event, handler in handlers.items():
                page.on(event, handler)
        except Exception:  # noqa: BLE001 — a page already gone, a test double
            return
        self.attached_pages += 1

    def _match(self, url: str) -> str | None:
        for pattern in self._patterns:
            if pattern.search(url):
                return pattern.pattern
        return None

    # --- handlers (Playwright calls these on the event loop; no awaits, no I/O) ---

    def _on_request(self, request: Any) -> None:
        url = str(getattr(request, "url", ""))
        pattern = self._match(url)
        row: dict[str, Any] = {
            "kind": "request",
            "method": getattr(request, "method", ""),
            "url": url if pattern else loggable_url(url),
            "resource_type": getattr(request, "resource_type", ""),
        }
        if pattern:
            row["matched"] = pattern
            self.matched[pattern] += 1
            post = getattr(request, "post_data", None)
            if isinstance(post, str) and post:
                row["post_data"] = post[:MAX_POST_CHARS]
        self.counts["requests"] += 1
        self._queue(self.network_path, row)

    def _on_response(self, response: Any) -> None:
        request = getattr(response, "request", None)
        url = str(getattr(response, "url", ""))
        resource_type = getattr(request, "resource_type", "") if request else ""
        pattern = self._match(url)
        status = getattr(response, "status", None)
        # Documents and matched requests only: an asset's 200 is noise, its 5xx is not.
        if not (
            pattern or resource_type == "document" or (isinstance(status, int) and status >= 400)
        ):
            return
        row = {
            "kind": "response",
            "url": url if pattern else loggable_url(url),
            "status": status,
            "resource_type": resource_type,
        }
        if isinstance(status, int) and status >= 400:
            self.counts["http_errors"] += 1
        self._queue(self.network_path, row)

    def _on_request_failed(self, request: Any) -> None:
        url = str(getattr(request, "url", ""))
        failure = getattr(request, "failure", None)
        self.counts["failed"] += 1
        self._queue(
            self.network_path,
            {
                "kind": "failed",
                "method": getattr(request, "method", ""),
                "url": url if self._match(url) else loggable_url(url),
                "resource_type": getattr(request, "resource_type", ""),
                "failure": str(failure)[:MAX_TEXT_CHARS] if failure else "",
            },
        )

    def _on_console(self, message: Any) -> None:
        level = str(getattr(message, "type", "log"))
        location = getattr(message, "location", None) or {}
        if level == "error":
            self.counts["console_errors"] += 1
        elif level == "warning":
            self.counts["console_warnings"] += 1
        self._queue(
            self.console_path,
            {
                "kind": "console",
                "level": level,
                "text": str(getattr(message, "text", ""))[:MAX_TEXT_CHARS],
                "url": loggable_url(str(location.get("url", "")))
                if isinstance(location, dict)
                else "",
            },
        )

    def _on_page_error(self, error: Any) -> None:
        self.counts["page_errors"] += 1
        self._queue(
            self.console_path,
            {
                "kind": "pageerror",
                "message": str(getattr(error, "message", error))[:MAX_TEXT_CHARS],
            },
        )

    # --- persistence --------------------------------------------------------------

    def _queue(self, path: Path, row: dict[str, Any]) -> None:
        self._pending.append((path, {"ts": _now(), **row}))
        if len(self._pending) >= _FLUSH_EVERY:
            self.flush()

    def flush(self) -> None:
        """Write what is queued. Called after each step and when the run ends."""
        if not self._pending:
            return
        pending, self._pending = self._pending, []
        by_path: dict[Path, list[str]] = {}
        for path, row in pending:
            by_path.setdefault(path, []).append(json.dumps(row, ensure_ascii=False, default=str))
        for path, lines in by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")

    def summary(self) -> dict[str, Any]:
        self.flush()
        return {
            "network_file": str(self.network_path) if self.network_path.exists() else None,
            "console_file": str(self.console_path) if self.console_path.exists() else None,
            "counts": {
                "requests": self.counts["requests"],
                "failed": self.counts["failed"],
                "http_errors": self.counts["http_errors"],
                "console_errors": self.counts["console_errors"],
                "console_warnings": self.counts["console_warnings"],
                "page_errors": self.counts["page_errors"],
            },
            "matched": [{"pattern": p, "count": c} for p, c in sorted(self.matched.items())],
            "pages": self.attached_pages,
        }
