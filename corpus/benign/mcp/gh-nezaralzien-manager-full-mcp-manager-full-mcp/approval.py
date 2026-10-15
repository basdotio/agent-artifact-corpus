"""Ask-first enforcement: a real dialog on the user's screen, not a prompt.

A resource/operation set to "ask" is not refused and not waved through — the
server stops and puts a native confirmation box in front of the user, with the
business, the operation and a summary of what is about to be written. No answer
within the timeout means no.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

TIMEOUT_SECONDS = 120
REMEMBER_SECONDS = 15 * 60

DENY = "deny"
ONCE = "once"
REMEMBER = "remember"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ApprovalRequest:
    business: str
    resource_label: str
    resource: str
    operation: str
    details: str
    risk_note: str = ""

    def title(self) -> str:
        return f"Claude wants to {self.operation} in {self.business}"

    def message(self) -> str:
        lines = [
            f"Business:  {self.business}",
            f"Action:    {self.operation.upper()}  {self.resource_label} ({self.resource})",
            "",
            self.details.strip() or "(no details)",
        ]
        if self.risk_note:
            lines += ["", f"HIGH RISK: {self.risk_note}"]
        lines += ["", "Manager has no undo. Allow this?"]
        return "\n".join(lines)


def _applescript() -> str:
    """Plain `display dialog`.

    Deliberately not routed through System Events: that needs macOS automation
    consent, and an unanswered consent prompt would hang the approval instead of
    showing it. `activate` is enough to bring this dialog forward.
    """
    return "\n".join(
        [
            "on run argv",
            "  set msg to item 1 of argv",
            "  set ttl to item 2 of argv",
            "  activate",
            "  set answer to display dialog msg with title ttl "
            'buttons {"Deny", "Allow once", "Allow 15 min"} default button "Deny" '
            f"with icon caution giving up after {TIMEOUT_SECONDS}",
            '  if gave up of answer then return "deny"',
            "  set b to button returned of answer",
            '  if b is "Allow once" then return "once"',
            '  if b is "Allow 15 min" then return "remember"',
            '  return "deny"',
            "end run",
        ]
    )


def _ask_macos(request: ApprovalRequest) -> str:
    result = subprocess.run(
        ["osascript", "-e", _applescript(), request.message(), request.title()],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS + 15,
    )
    answer = (result.stdout or "").strip().casefold()
    return answer if answer in {ONCE, REMEMBER} else DENY


def _ask_windows(request: ApprovalRequest) -> str:
    script = (
        "Add-Type -AssemblyName PresentationFramework;"
        "$r=[System.Windows.MessageBox]::Show($env:MFM_MSG,$env:MFM_TITLE,"
        "'YesNo','Warning','No');"
        "if($r -eq 'Yes'){Write-Output 'once'}else{Write-Output 'deny'}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS + 15,
        env={"MFM_MSG": request.message(), "MFM_TITLE": request.title()},
    )
    return ONCE if (result.stdout or "").strip().casefold() == ONCE else DENY


def _ask_linux(request: ApprovalRequest) -> str:
    if shutil.which("zenity"):
        command = [
            "zenity", "--question", "--title", request.title(),
            "--text", request.message(), "--ok-label", "Allow once",
            "--cancel-label", "Deny", f"--timeout={TIMEOUT_SECONDS}",
        ]
    elif shutil.which("kdialog"):
        command = ["kdialog", "--title", request.title(), "--warningyesno", request.message()]
    else:
        return UNAVAILABLE
    result = subprocess.run(command, capture_output=True, timeout=TIMEOUT_SECONDS + 15)
    return ONCE if result.returncode == 0 else DENY


def _ask_blocking(request: ApprovalRequest) -> str:
    try:
        if sys.platform == "darwin":
            return _ask_macos(request)
        if sys.platform.startswith("win"):
            return _ask_windows(request)
        return _ask_linux(request)
    except FileNotFoundError:
        return UNAVAILABLE
    except subprocess.TimeoutExpired:
        return DENY
    except Exception:
        return UNAVAILABLE


async def ask(request: ApprovalRequest) -> str:
    """Show the dialog off the event loop; returns once / remember / deny / unavailable."""
    return await asyncio.to_thread(_ask_blocking, request)


class GrantCache:
    """Short-lived 'Allow 15 min' grants, kept in memory only."""

    def __init__(self) -> None:
        self._until: dict[tuple[str, str, str], float] = {}

    def remember(self, business: str, resource: str, op: str) -> None:
        self._until[(business, resource, op)] = time.time() + REMEMBER_SECONDS

    def is_granted(self, business: str, resource: str, op: str) -> bool:
        expiry = self._until.get((business, resource, op))
        if expiry is None:
            return False
        if expiry < time.time():
            del self._until[(business, resource, op)]
            return False
        return True

    def clear(self) -> None:
        self._until.clear()


GRANTS = GrantCache()
