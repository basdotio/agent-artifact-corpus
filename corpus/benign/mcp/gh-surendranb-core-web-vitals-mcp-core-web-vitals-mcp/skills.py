# SPDX-License-Identifier: MIT
"""Dynamic skills layer for core-web-vitals-mcp: fetches from GitHub raw with local fallback."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

SKILLS_REPO_URL = "https://raw.githubusercontent.com/surendranb/core-web-vitals-mcp/main/skills"

_BUNDLED_SKILLS: Dict[str, str] = {
    "google-api-setup": "Google API Setup & Free Quota Guide: How to obtain a free Google Cloud API key, enable CrUX/PageSpeed APIs, and resolve 400/403/429 limits per official docs.",
    "lcp-optimization": "Largest Contentful Paint Optimization: Resource priorities, preloads, modern formats, and render delay elimination.",
    "inp-debugging": "Interaction to Next Paint Debugging: Long task decomposition, scheduler.yield, event handler profiling, and presentation delay mitigation.",
    "cls-remediation": "Cumulative Layout Shift Remediation: Aspect-ratio reservation, font metric overrides, and dynamic element stabilization.",
}


def get_local_skills_dir() -> Path:
    """Find the local skills directory."""
    candidates = [
        Path(__file__).parent / "skills",
        Path(__file__).parent.parent.parent / "skills",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return Path(__file__).parent / "skills"


def list_available_skills() -> List[str]:
    """Return sorted list of available skill names."""
    skills = set(_BUNDLED_SKILLS.keys())
    local_dir = get_local_skills_dir()
    if local_dir.exists():
        try:
            # Handle both pathlib.Path and zipfile._PortablePosixPath traversables
            if hasattr(local_dir, "iterdir"):
                for p in local_dir.iterdir():
                    name = getattr(p, "name", "")
                    if name.endswith(".md"):
                        skills.add(name[:-3])
            elif hasattr(local_dir, "glob"):
                for p in local_dir.glob("*.md"):
                    skills.add(p.stem)
        except Exception:
            pass
    return sorted(skills)


def read_skill_content(name: str) -> Tuple[str, bool]:
    """Read a skill by name, trying GitHub raw first then local fallback.

    Returns:
        (content, success)
    """
    safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
    if not safe_name:
        return "[INPUT_FIXABLE] Skill name cannot be empty. Call skills_list to view available skills.", False

    # 1. Try remote GitHub fetch
    remote_url = f"{SKILLS_REPO_URL}/{safe_name}.md"
    try:
        req = urllib.request.Request(
            remote_url,
            headers={"User-Agent": "core-web-vitals-mcp/0.1.0"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", "replace"), True
    except Exception:
        pass

    # 2. Local fallback
    local_path = get_local_skills_dir() / f"{safe_name}.md"
    if local_path.exists():
        try:
            if hasattr(local_path, "read_text"):
                return local_path.read_text(encoding="utf-8"), True
            with local_path.open(encoding="utf-8") as f:
                return f.read(), True
        except Exception as exc:
            return f"[INPUT_FIXABLE] Failed to read local skill '{safe_name}': {exc}", False

    available = ", ".join(list_available_skills())
    return (
        f"[INPUT_FIXABLE] Unknown skill '{name}'. Available skills: {available}. "
        "Call skills_list() to see descriptions.",
        False,
    )


def skills_list() -> str:
    """List available skills as JSON string."""
    skills_data = []
    for s in list_available_skills():
        desc = _BUNDLED_SKILLS.get(s, "Core Web Vitals diagnostic playbook.")
        skills_data.append({"name": s, "description": desc})
    return json.dumps({
        "skills": skills_data,
        "source": "github+local",
        "description": "Call skill_read(name='<skill_name>') to load any playbook."
    }, indent=2)


def skill_read(name: str) -> str:
    """Read a skill and return its text content directly."""
    content, _ = read_skill_content(name)
    return content
