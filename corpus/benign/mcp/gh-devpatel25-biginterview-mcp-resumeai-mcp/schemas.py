"""Pydantic v2 models for every tool input/output (PLAN.md §8). Phases 1/2."""

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel

Medal = Literal["gold", "silver", "bronze"]
MEDALS = get_args(Medal)

# §13 error catalog.
ErrorCode = Literal[
    "auth_expired", "limit_reached", "scan_failed", "scan_timeout", "unknown_state", "not_found",
    "site_changed", "invalid_input", "storage_error", "profile_in_use", "network_error", "internal_error",
]


class ToolError(Exception):
    """A §13 error; server.py (Phase 4) turns it into the §7.0 error envelope."""

    def __init__(self, code: ErrorCode, message: str, hint: str):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint


class AuthStatus(BaseModel):
    logged_in: bool
    scans_remaining: int | None
    account_email: str | None
    checked_at: datetime


class ScanSummary(BaseModel):
    scan_id: str
    role_title: str
    company: str | None
    scoring_guide: str | None
    scanned_at: datetime | None
    medal: Medal | None
    resume_filename: str
    resume_sha256: str | None  # ledger-only (§7.2)
    jd_sha256: str | None  # ledger-only (§7.2)


class ScanList(BaseModel):
    scans: list[ScanSummary]
    next_cursor: str | None


# §8 ScanFeedback. Status amendment 2026-09-28: site labels gold "Good Work!" → perfect, bronze "Needs Work!" →
# needs_work, silver "Almost There" (not a §8 label, and flagged by the site) → warning; `meets` unused so far.
Status = Literal["perfect", "meets", "needs_work", "warning"]
CategoryName = Literal["readability", "credibility", "ats_fit", "format"]


class Criterion(BaseModel):
    name: str
    status: Status
    detail: str
    suggestion: str | None


class Category(BaseModel):
    badge: Medal | None  # null only when the site gives no badge; the loop treats it as "cannot evaluate"
    criteria: list[Criterion]


class AtsFitCategory(Category):
    keywords_matched: list[str]
    keywords_unmatched: list[str]


class Categories(BaseModel):
    readability: Category
    credibility: Category
    ats_fit: AtsFitCategory
    format: Category


class ActionItem(BaseModel):
    category: CategoryName
    item: str
    priority: Literal["high", "medium", "low"]


class ScanFeedback(BaseModel):
    scan_id: str
    resume_filename: str
    resume_sha256: str | None  # ledger-only
    role_title: str
    company: str | None
    scoring_guide: str | None
    scanned_at: datetime | None
    medal: Medal | None
    partial: bool
    categories: Categories
    action_items: list[ActionItem]


ScanState = Literal["queued", "scanning", "complete", "failed", "unknown"]


class ScanStatus(BaseModel):  # §7.4
    scan_id: str
    state: ScanState
    scans_remaining: int | None
    checked_at: datetime
    hint: str | None = None  # §7.4 amendment 2026-09-28: set only for state=unknown (names the snapshot)


class StartScanResult(BaseModel):  # §7.3
    scan_id: str
    reused: bool
    state: Literal["queued", "scanning", "complete"]
    scans_remaining: int | None


class DeleteResult(BaseModel):  # §7.6
    deleted: bool
    backup_path: str
    scans_remaining: int | None
    allowance_restored: bool | None  # informational only; the loop must not depend on it
