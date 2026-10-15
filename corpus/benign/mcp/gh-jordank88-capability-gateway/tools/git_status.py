#!/usr/bin/env python3
"""
git_status — Current working tree status (branch, staged, unstaged, untracked).

Usage:
    python tools/git_status.py '{"repo": "."}'
    echo '{}' | python tools/git_status.py

Args:
    repo  str  Path to git repo (default: ".")

Returns:
    success     bool
    branch      str   Current branch name (or "(detached)" / "(none)")
    head_sha    str   Short SHA of HEAD (empty if no commits)
    clean       bool  True when nothing staged/unstaged/untracked
    staged      list  Files with staged changes  [{status, path}]
    unstaged    list  Files with unstaged changes [{status, path}]
    untracked   list  Untracked file paths
    ahead       int   Commits ahead of upstream (0 if no upstream)
    behind      int   Commits behind upstream   (0 if no upstream)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for _utils
from _utils import read_args, emit, ok, fail, run_cmd, resolve_path

_STATUS_MAP = {
    "M": "modified",
    "A": "added",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
    "?": "untracked",
    "!": "ignored",
}


def _parse_porcelain(output: str) -> tuple[list, list, list]:
    staged, unstaged, untracked = [], [], []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        xy, path = line[:2], line[3:]
        # Handle renames: "old -> new"
        if " -> " in path:
            path = path.split(" -> ")[-1]
        x, y = xy[0], xy[1]

        if x != " " and x != "?":
            staged.append({"status": _STATUS_MAP.get(x, x), "path": path})
        if y == "?":
            untracked.append(path)
        elif y != " ":
            unstaged.append({"status": _STATUS_MAP.get(y, y), "path": path})

    return staged, unstaged, untracked


def run(args: dict) -> dict:
    repo = args.get("repo", ".")

    try:
        repo_path = resolve_path(repo)
    except FileNotFoundError as e:
        return fail(str(e), "PathNotFound")

    # --- branch ---
    branch_r = run_cmd(["git", "branch", "--show-current"], cwd=repo_path, timeout=10)
    branch = branch_r["stdout"].strip() or "(detached)"

    # --- HEAD sha ---
    sha_r = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10)
    head_sha = sha_r["stdout"].strip() if sha_r["returncode"] == 0 else ""

    # --- porcelain status ---
    status_r = run_cmd(
        ["git", "status", "--porcelain=v1"], cwd=repo_path, timeout=15
    )
    if status_r["returncode"] not in (0, 1):
        return fail(
            status_r["stderr"].strip() or "git status failed",
            "GitError",
            returncode=status_r["returncode"],
        )

    staged, unstaged, untracked = _parse_porcelain(status_r["stdout"])

    # --- ahead/behind upstream ---
    ahead, behind = 0, 0
    ab_r = run_cmd(
        ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"],
        cwd=repo_path,
        timeout=10,
    )
    if ab_r["returncode"] == 0:
        parts = ab_r["stdout"].strip().split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])

    clean = not staged and not unstaged and not untracked

    return ok(
        branch=branch,
        head_sha=head_sha,
        clean=clean,
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        ahead=ahead,
        behind=behind,
    )


if __name__ == "__main__":
    emit(run(read_args()))
