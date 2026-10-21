"""Framework version and update checking.

Single source of truth for the framework's own version, plus an opt-in,
network-gated check for newer published versions.

Design notes:
- The check is OPT-IN and network-gated. It only runs when the operator has
  explicitly enabled update checks (see ``update_check_opted_in``) AND their
  network permission is "allow" (see scripts/messaging.py). Anything else =
  no egress, ever. Allowing network egress for agent work is not consent to
  version checks; the two permissions are separate on purpose.
- It reads the public CHANGELOG.md on the main branch — the project's
  version record — and compares its latest ``## [x.y.z]`` heading against
  ``CURRENT_VERSION``. Nothing is sent anywhere; no telemetry.
- Results are cached under ``runs/`` (gitignored) with a 24h TTL so
  repeated calls don't hammer the network.
- Every failure mode returns a dict with ``checked: False`` and a reason.
  The check never raises and never blocks framework operation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

# Single source of truth for the framework version. Keep in sync with the
# newest "## [x.y.z]" heading in CHANGELOG.md (enforced by tests).
CURRENT_VERSION = "1.2.2"

REPO_SLUG = "paulthorson/agentic-governance"
REMOTE_CHANGELOG_URL = (
    f"https://raw.githubusercontent.com/{REPO_SLUG}/main/CHANGELOG.md"
)
CHANGELOG_URL = f"https://github.com/{REPO_SLUG}/blob/main/CHANGELOG.md"
RELEASES_URL = f"https://github.com/{REPO_SLUG}/releases"

CACHE_TTL_SECONDS = 24 * 3600
FETCH_TIMEOUT_SECONDS = 15

_VERSION_HEADING = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def _repo_root(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        return repo_root
    return Path(
        os.environ.get("ADVERSARIAL_ROOT", Path(__file__).resolve().parents[2])
    )


def _load_messaging():
    """Load scripts/messaging.py by path (scripts/ is not a package).

    Resolved from this module's own location, not from the repo_root
    argument: the code lives with the framework, while repo_root points at
    the operator's checkout (config + cache).
    """
    path = Path(__file__).resolve().parents[2] / "scripts" / "messaging.py"
    spec = importlib.util.spec_from_file_location("ag_update_messaging", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load messaging module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def network_allows_update_check(repo_root: Path | None = None) -> bool:
    """True only when the operator explicitly allows network egress."""
    root = _repo_root(repo_root)
    try:
        messaging = _load_messaging()
        return bool(messaging.network_permits_egress(root))
    except Exception:
        return False


def update_check_opted_in(repo_root: Path | None = None) -> bool:
    """True only when the operator explicitly opted in to update checks.

    Two ways to opt in (either one counts):
    - environment: AG_UPDATE_CHECK=allow (also accepts 1/true/yes)
    - config: a "## Update checks" section in config/setup.md containing
      a "- allow" bullet (same shape as the "## Network permission" section)

    Default is off. This is separate from the network permission on
    purpose: allowing egress for agent work is not consent to version
    checks.
    """
    env = os.environ.get("AG_UPDATE_CHECK", "").strip().lower()
    if env in ("allow", "1", "true", "yes"):
        return True
    root = _repo_root(repo_root)
    setup = root / "config" / "setup.md"
    try:
        lines = setup.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    section = ""
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            section = s[3:].strip().lower()
            continue
        if section == "update checks" and s.startswith("- "):
            if s[2:].strip().lower() == "allow":
                return True
    return False


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Parse "x.y.z" into a comparable tuple; None when not a plain version."""
    parts = text.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def latest_version_in_changelog(text: str) -> str | None:
    """Return the newest version heading ("## [x.y.z]") in a changelog."""
    m = _VERSION_HEADING.search(text)
    return m.group(1) if m else None


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "runs" / "update-check.json"


def _read_cache(repo_root: Path) -> dict[str, Any] | None:
    path = _cache_path(repo_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("checked"):
        return None
    checked_at = data.get("checked_at")
    if not isinstance(checked_at, (int, float)):
        return None
    age_ms = int(time.time() * 1000) - int(checked_at)
    if age_ms > CACHE_TTL_SECONDS * 1000:
        return None
    data = dict(data)
    data["cached"] = True
    return data


def _write_cache(repo_root: Path, payload: dict[str, Any]) -> None:
    try:
        runs = repo_root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        _cache_path(repo_root).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # cache is best-effort; the check result still stands


def _default_fetcher(url: str) -> str:
    # No custom User-Agent: privacy by default means not fingerprinting
    # installs to the remote host. urllib's generic UA is enough.
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _not_checked(
    reason: str, repo_root: Path, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "checked": False,
        "current_version": CURRENT_VERSION,
        "latest_version": None,
        "update_available": False,
        "changelog_url": CHANGELOG_URL,
        "releases_url": RELEASES_URL,
        "checked_at": int(time.time() * 1000),
        "reason": reason,
    }
    if extra:
        payload.update(extra)
    return payload


def check_for_updates(
    *,
    force: bool = False,
    repo_root: Path | None = None,
    _fetcher: Callable[[str], str] | None = None,
    _network_ok: bool | None = None,
    _opted_in: bool | None = None,
) -> dict[str, Any]:
    """Check whether a newer framework version is published.

    Opt-in + network-gated: returns checked=False with a reason unless the
    operator explicitly enabled update checks AND allows network egress.
    Returns a status dict; never raises. ``_fetcher``, ``_network_ok`` and
    ``_opted_in`` are test seams (not part of the public contract).
    """
    root = _repo_root(repo_root)

    if not force:
        cached = _read_cache(root)
        if cached is not None:
            return cached

    opted_in = (
        _opted_in if _opted_in is not None else update_check_opted_in(root)
    )
    if not opted_in:
        return _not_checked(
            "Update checks are opt-in and currently off. To enable: set "
            "AG_UPDATE_CHECK=allow, or add a '## Update checks' section with "
            "'- allow' to config/setup.md.",
            root,
        )

    network_ok = (
        _network_ok
        if _network_ok is not None
        else network_allows_update_check(root)
    )
    if not network_ok:
        return _not_checked(
            "Network egress is not allowed by the operator's network "
            "permission (config/setup.md). Set it to 'allow' to check for "
            "updates, or pull the repo manually.",
            root,
        )

    fetcher = _fetcher or _default_fetcher
    try:
        remote_text = fetcher(REMOTE_CHANGELOG_URL)
    except Exception as exc:
        return _not_checked(f"Could not reach the published changelog: {exc}", root)

    latest = latest_version_in_changelog(remote_text)
    if latest is None:
        return _not_checked(
            "The published changelog has no recognizable version heading.",
            root,
        )

    current = parse_version(CURRENT_VERSION)
    newest = parse_version(latest)
    update_available = (
        current is not None and newest is not None and newest > current
    )

    payload: dict[str, Any] = {
        "checked": True,
        "current_version": CURRENT_VERSION,
        "latest_version": latest,
        "update_available": update_available,
        "changelog_url": CHANGELOG_URL,
        "releases_url": RELEASES_URL,
        "checked_at": int(time.time() * 1000),
        "cached": False,
    }
    _write_cache(root, payload)
    return payload
