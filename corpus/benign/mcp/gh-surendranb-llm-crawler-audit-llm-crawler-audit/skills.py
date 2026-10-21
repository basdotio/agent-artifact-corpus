# SPDX-License-Identifier: MIT
"""Dynamic skills loader for llm-crawler-audit.

Fetches up-to-date guidance, playbooks, and diagnostic strategies from GitHub at runtime
with automatic fallback to local bundled skills.
"""
from __future__ import annotations
import json
import time
import urllib.request
from pathlib import Path
from typing import List, Optional
from llm_crawler_audit.telemetry import track_tool_call

SKILLS_URL = "https://raw.githubusercontent.com/surendranb/llm-crawler-audit/main/skills"

BUILTIN_SKILLS = [
    "ai-robots-txt-playbook",
    "llms-txt-authoring",
    "markdown-mirror-setup",
]

def _get_local_skills_dir() -> Path:
    # Check parent hierarchy (src/llm_crawler_audit -> repo root / skills)
    cand = Path(__file__).resolve().parent.parent.parent / "skills"
    if cand.is_dir():
        return cand
    # Fallback to adjacent skills folder
    cand2 = Path(__file__).resolve().parent / "skills"
    return cand2

def list_available_skills() -> List[str]:
    local_dir = _get_local_skills_dir()
    found: set[str] = set()
    if local_dir.is_dir():
        for p in local_dir.glob("*.md"):
            found.add(p.stem)
    found.update(BUILTIN_SKILLS)
    return sorted(found)

def skills_list() -> str:
    """List available skills (dynamic, GitHub-first with local fallback)."""
    t0 = time.perf_counter()
    names = list_available_skills()
    out = json.dumps({"skills": names, "source": "github+local"}, indent=2)
    track_tool_call("skills_list", (time.perf_counter() - t0) * 1000, "success", len(names), len(out))
    return out

def skill_read(name: str) -> str:
    """Fetch SKILL.md by name from GitHub, with local fallback and error absorption."""
    t0 = time.perf_counter()
    safe = "".join(c for c in name.strip() if c.isalnum() or c in ("_", "-"))
    if not safe:
        avail = ", ".join(list_available_skills())
        out = f"[INPUT_FIXABLE] Empty skill name provided. Available skills: {avail}. Call skills_list to view all available skills."
        track_tool_call("skill_read", (time.perf_counter() - t0) * 1000, "error", 0, len(out), cat="ValidationError", msg=out)
        return out

    # 1. Try remote GitHub fetch
    try:
        url = f"{SKILLS_URL}/{safe}.md"
        req = urllib.request.Request(url, headers={"User-Agent": "llm-crawler-audit-skills"})
        with urllib.request.urlopen(req, timeout=4.0) as r:
            text = r.read().decode("utf-8", "replace")
            track_tool_call("skill_read", (time.perf_counter() - t0) * 1000, "success", 1, len(text))
            return text
    except Exception:
        pass

    # 2. Local fallback
    local_dir = _get_local_skills_dir()
    local_file = local_dir / f"{safe}.md"
    if local_file.is_file():
        text = local_file.read_text(encoding="utf-8")
        track_tool_call("skill_read", (time.perf_counter() - t0) * 1000, "success", 1, len(text))
        return text

    # 3. Not found - error absorption with candidates
    avail = ", ".join(list_available_skills())
    out = (
        f"[INPUT_FIXABLE] Unknown skill '{name}'. Available skills: {avail}. "
        f"If network is blocked: [TRANSIENT] retry, or [ENVIRONMENT_FIXABLE: STOP & ASK HUMAN] if GitHub raw content is blocked by network proxy."
    )
    track_tool_call("skill_read", (time.perf_counter() - t0) * 1000, "error", 0, len(out), cat="NotFoundError", msg=out)
    return out
