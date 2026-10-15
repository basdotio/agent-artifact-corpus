# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""A local, append-only record of the writes made through the server.

Each applied operation is one JSON line holding identifiers: which transaction
moved from which category to which. A budget change or a move also keeps the
amounts assigned before and after, a flag change the colours, and a target the
one to restore, which undo restores. Undoing an operation appends a line that
marks it undone. A transaction's amount, payee and memo are never stored.

A payee rename is the one operation whose undo needs a name: its line keeps the
payee's name before and after, and nothing else of the transactions naming it.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    ValidationError,
)

from avenir_mcp.model import Model


class Move(Model):
    """One transaction's category before and after an operation."""

    transaction_id: str
    """YNAB id of the transaction."""
    from_category_id: str | None
    """Category before the operation; null for none."""
    to_category_id: str | None
    """Category after the operation; null for none."""


class Entry(Model):
    """An operation as recorded in the journal."""

    # A line written by a later version may carry fields this one does not know.
    model_config = ConfigDict(extra="ignore")

    operation_id: str
    """Random id of the operation."""
    # Lines written before YNAB named budgets "plans" say budget_id.
    plan_id: str = Field(validation_alias=AliasChoices("plan_id", "budget_id"))
    """Plan the operation changed."""
    kind: str
    """categorize, reconcile, budget, move, create, flag, target or payee."""
    applied_at: str
    """When it was applied, ISO 8601 in UTC."""
    moves: list[Move]
    """Category changes (categorize operations)."""
    details: dict[str, Any] = {}
    """What undoing other kinds needs, as identifiers."""


def default_path() -> Path:
    """Locate the journal.

    Returns:
        AVENIR_MCP_JOURNAL when set, otherwise journal.jsonl in the XDG state directory.
    """
    configured = os.getenv("AVENIR_MCP_JOURNAL")
    if configured:
        return Path(configured)
    state_home = os.getenv("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_home) / "avenir-mcp" / "journal.jsonl"


class Journal:
    """Operations applied through the server, newest last."""

    def __init__(self, path: Path) -> None:
        """Open the journal at a path; the file is created on the first write.

        Args:
            path: The JSON Lines file.
        """
        self._path = path

    def _append(self, line: dict[str, Any]) -> None:
        """Append one line, creating the file readable by its owner only.

        Args:
            line: The JSON object to write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as file:
            file.write(json.dumps(line, separators=(",", ":")) + "\n")

    def _lines(self) -> tuple[list[Entry], set[str]]:
        """Read the journal.

        Returns:
            The operations recorded, oldest first, and the ids marked undone.

        Raises:
            ValueError: If a line is neither an operation nor an undo mark, naming the
                file and the line.
        """
        entries: list[Entry] = []
        undone: set[str] = set()
        if not self._path.exists():
            return entries, undone
        with self._path.open("rb") as file:
            for number, raw in enumerate(file, start=1):
                if not raw.strip():
                    continue
                try:
                    data = json.loads(raw.decode("utf-8"))
                    if isinstance(data, dict) and isinstance(data.get("undone"), str):
                        undone.add(data["undone"])
                    else:
                        entries.append(Entry.model_validate(data))
                except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
                    raise ValueError(
                        f"{self._path}, line {number}, is not a journal entry: fix or remove "
                        "that line, or move the file aside to start a new journal."
                    ) from error
        return entries, undone

    def record(
        self,
        plan_id: str,
        kind: str,
        moves: list[Move],
        details: dict[str, Any] | None = None,
    ) -> str:
        """Append an applied operation.

        Args:
            plan_id: The plan it changed.
            kind: categorize, reconcile, budget, move, create, flag, target or payee.
            moves: Category changes, for a recategorisation.
            details: What undoing another kind needs: identifiers, a budget
                change's amounts before and after, and a payee rename's names.

        Returns:
            The new operation's id.
        """
        operation_id = secrets.token_hex(6)
        entry = Entry(
            operation_id=operation_id,
            plan_id=plan_id,
            kind=kind,
            applied_at=datetime.now(UTC).isoformat(timespec="seconds"),
            moves=moves,
            details=details or {},
        )
        self._append(entry.model_dump(mode="json"))
        return operation_id

    def mark_undone(self, operation_id: str) -> None:
        """Record that an operation has been undone.

        Args:
            operation_id: The operation undone.
        """
        self._append({"undone": operation_id})

    def find(self, plan_id: str, operation_id: str | None = None) -> Entry | None:
        """Find an operation of this plan still in effect.

        Args:
            plan_id: The plan the operation changed.
            operation_id: The operation wanted; None for the most recent one.

        Returns:
            The operation, or None if there is none.

        Raises:
            ValueError: If a line of the journal is damaged.
        """
        entries, undone = self._lines()
        for entry in reversed(entries):
            if entry.operation_id in undone or entry.plan_id != plan_id:
                continue
            if operation_id is None or entry.operation_id == operation_id:
                return entry
        return None
