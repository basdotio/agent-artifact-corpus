"""Git history analysis for extraction insights.

Examines git history to understand:
- Hot files (frequently changed)
- Stable files (rarely changed, good extraction candidates)
- Contributor patterns
- Module evolution
- Coupling between files

Uses deterministic git parsing with unambiguous field separators to avoid
author attribution corruption from paths containing special characters.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from ..core.output import to_jsonable
from ..core.registry import AnalysisContext, Option

__all__ = ["GitHistoryAnalyzer"]


class GitHistoryAnalyzer:
    """Analyzes git history for extraction readiness insights.

    Reports file stability, author involvement, coupling, and activity trends
    to help identify components safe for extraction.
    """

    name = "git"
    summary = "Analyze git history for extraction stability and risk"
    description = (
        "Examines git commit history to identify which files are stable "
        "(rarely changed, safe to extract), which are hot (actively developed), "
        "and which files are commonly changed together (coupled). Reports "
        "contributor patterns, directory activity, and recent commits. "
        "Helps identify which modules are mature enough for extraction and "
        "which are still evolving. Uses deterministic git parsing to handle "
        "paths with special characters correctly."
    )

    options = (
        Option(
            name="days",
            type=int,
            default=365,
            help="Number of days of history to analyze",
        ),
        Option(
            name="top_n",
            type=int,
            default=15,
            help="Maximum number of items to report in ranked lists",
        ),
        Option(
            name="coupling_threshold",
            type=int,
            default=3,
            help="Minimum co-change count for files to be considered coupled",
        ),
        Option(
            name="max_commit_files",
            type=int,
            default=10,
            help="Exclude commits touching more than this many files (noise filtering)",
        ),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Run git history analysis."""
        days: int = opts.get("days", 365)
        top_n: int = opts.get("top_n", 15)
        coupling_threshold: int = opts.get("coupling_threshold", 3)
        max_commit_files: int = opts.get("max_commit_files", 10)

        # Check git prerequisites
        git_status = self._check_git(ctx)
        if git_status["status"] != "ok":
            return {
                "status": git_status["status"],
                "error": git_status["error"],
                "meta": ctx.meta(),
            }

        ctx.reporter.step("Analyzing git history")

        # Gather statistics
        ctx.reporter.sub("collecting file changes")
        file_changes = self._get_file_changes(ctx, days)

        ctx.reporter.sub("analyzing author involvement")
        file_authors = self._get_file_authors(ctx, days)

        ctx.reporter.sub("categorizing files by stability")
        categories = self._categorize_files(file_changes, file_authors)

        ctx.reporter.sub("aggregating directory activity")
        dir_activity = self._get_directory_activity(file_changes, top_n)

        ctx.reporter.sub("identifying top contributors")
        contributors = self._get_top_contributors(ctx, days, top_n)

        ctx.reporter.sub("detecting file coupling")
        coupling = self._get_coupling(
            ctx, days, coupling_threshold, max_commit_files, top_n
        )

        ctx.reporter.sub("fetching recent commits")
        recent_commits = self._get_recent_commits(ctx, top_n)

        return {
            "status": "ok",
            "summary": {
                "analysis_days": days,
                "files_with_history": len(file_changes),
                "total_file_changes": sum(file_changes.values()),
                "distinct_authors": len(set().union(*file_authors.values())),
                "coupling_pairs": len(coupling),
                "hot_files": len(categories["hot"]),
                "stable_files": len(categories["stable"]),
                "volatile_files": len(categories["volatile"]),
                "single_owner_files": len(categories["single_owner"]),
            },
            "file_changes": file_changes,
            "file_authors": file_authors,
            "categories": categories,
            "directory_activity": dir_activity,
            "top_contributors": contributors,
            "coupling": coupling,
            "recent_commits": recent_commits,
            "options": {
                "days": days,
                "top_n": top_n,
                "coupling_threshold": coupling_threshold,
                "max_commit_files": max_commit_files,
            },
            "meta": ctx.meta(),
        }

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render analysis result as markdown."""
        lines = [
            f"# Git History Analysis: {result['meta']['project']}",
            "",
        ]

        status = result.get("status")
        if status != "ok":
            lines.extend([
                "## Status",
                "",
                f"**Error:** {status}",
                "",
                result.get("error", "Unknown error"),
                "",
            ])
            return "\n".join(lines)

        lines.extend([
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ])

        s = result["summary"]
        lines.extend([
            f"| Analysis Period | {s['analysis_days']} days |",
            f"| Files with History | {s['files_with_history']} |",
            f"| Total File Changes | {s['total_file_changes']} |",
            f"| Distinct Authors | {s['distinct_authors']} |",
            f"| Coupled File Pairs | {s['coupling_pairs']} |",
            f"| Hot Files | {s['hot_files']} |",
            f"| Stable Files | {s['stable_files']} |",
            f"| Volatile Files | {s['volatile_files']} |",
            f"| Single-Owner Files | {s['single_owner_files']} |",
            "",
        ])

        # Stable files section
        stable = result["categories"].get("stable", [])
        if stable:
            lines.extend([
                "## Stable Files (Good Extraction Candidates)",
                "",
                "Low change frequency = stable interfaces, safe to extract:",
                "",
                "| File | Changes | Authors |",
                "|------|---------|---------|",
            ])
            for filepath, changes, author_count in stable[:10]:
                lines.append(f"| `{filepath}` | {changes} | {author_count} |")
            lines.append("")

        # Hot files section
        hot = result["categories"].get("hot", [])
        if hot:
            lines.extend([
                "## Hot Files (Avoid Extracting)",
                "",
                "High change frequency, many contributors = still evolving:",
                "",
                "| File | Changes | Authors |",
                "|------|---------|---------|",
            ])
            for filepath, changes, author_count in hot[:10]:
                lines.append(f"| `{filepath}` | {changes} | {author_count} |")
            lines.append("")

        # Volatile files section
        volatile = result["categories"].get("volatile", [])
        if volatile:
            lines.extend([
                "## Volatile Files (Risky for Extraction)",
                "",
                "High change frequency with few authors = concentrated risk:",
                "",
                "| File | Changes | Authors |",
                "|------|---------|---------|",
            ])
            for filepath, changes, author_count in volatile[:10]:
                lines.append(f"| `{filepath}` | {changes} | {author_count} |")
            lines.append("")

        # Single-owner section
        single = result["categories"].get("single_owner", [])
        if single:
            lines.extend([
                "## Single-Owner Files",
                "",
                "Maintained by one contributor - may have hidden knowledge:",
                "",
                "| File | Changes | Author |",
                "|------|---------|--------|",
            ])
            for filepath, changes, author in single[:10]:
                lines.append(f"| `{filepath}` | {changes} | {author or 'unknown'} |")
            lines.append("")

        # Directory activity
        dir_activity = result.get("directory_activity", {})
        if dir_activity:
            lines.extend([
                "## Directory Activity",
                "",
                "Aggregate change frequency by directory:",
                "",
                "| Directory | Changes |",
                "|-----------|---------|",
            ])
            for dirname, changes in list(dir_activity.items())[:15]:
                lines.append(f"| `{dirname}/` | {changes} |")
            lines.append("")

        # Top contributors
        contributors = result.get("top_contributors", [])
        if contributors:
            lines.extend([
                "## Top Contributors",
                "",
                "| Contributor | Commits |",
                "|-------------|---------|",
            ])
            for name, count in contributors[:10]:
                lines.append(f"| {name} | {count} |")
            lines.append("")

        # Coupling section
        coupling = result.get("coupling", [])
        if coupling:
            lines.extend([
                "## File Coupling (Changed Together)",
                "",
                "Files often modified in the same commit - may need to extract together:",
                "",
                "| File 1 | File 2 | Co-changes |",
                "|--------|--------|------------|",
            ])
            for f1, f2, count in coupling[:10]:
                lines.append(f"| `{f1}` | `{f2}` | {count} |")
            lines.append("")

        # Recent commits
        recent = result.get("recent_commits", [])
        if recent:
            lines.extend([
                "## Recent Commits",
                "",
                "| Date | Author | Message |",
                "|------|--------|---------|",
            ])
            for commit in recent[:10]:
                date = commit.get("date", "unknown")
                author = commit.get("author", "unknown")
                message = commit.get("message", "")[:60]
                lines.append(f"| {date} | {author} | {message} |")
            lines.append("")

        # Options and recommendations
        lines.extend([
            "## Analysis Configuration",
            "",
            f"- Analysis period: {result['options']['days']} days",
            f"- Top N limit: {result['options']['top_n']}",
            f"- Coupling threshold: {result['options']['coupling_threshold']} co-changes",
            f"- Max files per commit (noise filter): {result['options']['max_commit_files']}",
            "",
            "## Extraction Recommendations",
            "",
            "1. **Safe to Extract:** Files in 'Stable Files' section with low change count",
            "2. **Extract Together:** Check 'File Coupling' section for dependencies",
            "3. **Avoid/Delay:** Files in 'Hot Files' or 'Volatile Files' are still actively developed",
            "4. **Watch Out:** Single-owner files may have hidden knowledge - ensure knowledge transfer before extracting",
            "",
        ])

        return "\n".join(lines)

    # ---- Internal methods ----

    def _check_git(self, ctx: AnalysisContext) -> dict[str, Any]:
        """Check if git is available and repo is valid."""
        # Check git is installed
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return {
                    "status": "git_not_installed",
                    "error": "git command not found or failed",
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {
                "status": "git_not_installed",
                "error": "git command not found",
            }

        # Check if it's a git repository
        git_dir = ctx.root / ".git"
        if not git_dir.exists():
            return {
                "status": "not_a_repository",
                "error": f"Not a git repository (no .git found at {ctx.root})",
            }

        # Check for shallow clone
        shallow_file = git_dir / "shallow"
        if shallow_file.exists():
            return {
                "status": "shallow_clone",
                "error": (
                    "This is a shallow clone (limited history). "
                    "Git statistics may be incomplete. "
                    "Consider cloning with --unshallow for full analysis."
                ),
            }

        # Check if there are any commits
        result = self._run_git(ctx, ["rev-list", "--count", "HEAD"])
        if result is None:
            return {
                "status": "empty_history",
                "error": "Repository has no commits yet",
            }
        try:
            commit_count = int(result.strip())
            if commit_count == 0:
                return {
                    "status": "empty_history",
                    "error": "Repository has no commits",
                }
        except ValueError:
            return {
                "status": "empty_history",
                "error": "Could not count commits",
            }

        return {"status": "ok"}

    def _run_git(self, ctx: AnalysisContext, args: list[str]) -> str | None:
        """Run a git command with proper error handling.

        Uses -z output format to avoid ambiguity with paths containing newlines
        or special characters. Returns None only on actual failures.
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return result.stdout
            ctx.reporter.warn(f"git command failed: {' '.join(args)}")
            return None
        except subprocess.TimeoutExpired:
            ctx.reporter.warn(f"git command timed out: {' '.join(args)}")
            return None
        except Exception as e:
            ctx.reporter.warn(f"git command error: {e}")
            return None

    def _get_file_changes(self, ctx: AnalysisContext, days: int) -> dict[str, int]:
        """Get per-file change counts using deterministic parsing.

        Uses null-byte separator (-z) to ensure paths with newlines/special
        characters don't corrupt the parse.
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        output = self._run_git(
            ctx,
            [
                "log",
                f"--since={since_date}",
                "--name-only",
                "--pretty=format:",
                "--no-merges",
                "-z",
            ],
        )

        if not output:
            return {}

        file_changes: dict[str, int] = defaultdict(int)
        # Split on null bytes
        for filepath in output.split("\0"):
            filepath = filepath.strip()
            if filepath:
                file_changes[filepath] += 1

        return dict(sorted(file_changes.items()))

    def _get_file_authors(self, ctx: AnalysisContext, days: int) -> dict[str, set[str]]:
        """Get distinct author set per file.

        Uses %x01 (ASCII SOH) as an unambiguous sentinel to separate authors
        from paths. Paths never contain SOH, so this is immune to paths with
        @ symbols or other special characters.
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        output = self._run_git(
            ctx,
            [
                "log",
                f"--since={since_date}",
                "--name-only",
                "--pretty=format:%x01%ae",  # SOH + author email
                "--no-merges",
            ],
        )

        if not output:
            return {}

        file_authors: dict[str, set[str]] = defaultdict(set)
        current_author = None

        for line in output.split("\n"):
            if line.startswith("\x01"):
                # This is an author line
                current_author = line[1:]
            elif line.strip() and current_author:
                # This is a file path
                file_authors[line.strip()].add(current_author)

        return {f: authors for f, authors in sorted(file_authors.items())}

    def _categorize_files(
        self,
        file_changes: dict[str, int],
        file_authors: dict[str, set[str]],
    ) -> dict[str, list[tuple[str, int, int]]]:
        """Categorize files by stability and ownership.

        Categories:
        - hot: high change frequency, many authors
        - stable: low change frequency (good extraction candidates)
        - volatile: high changes, few authors (concentrated risk)
        - single_owner: maintained by exactly one author
        """
        if not file_changes:
            return {
                "hot": [],
                "stable": [],
                "volatile": [],
                "single_owner": [],
            }

        max_changes = max(file_changes.values())

        categories: dict[str, list[tuple]] = {
            "hot": [],
            "stable": [],
            "volatile": [],
            "single_owner": [],
        }

        for filepath, changes in file_changes.items():
            # Count distinct authors; unknown = 0
            author_count = len(file_authors.get(filepath, set()))
            change_ratio = changes / max_changes

            # Categorization logic
            if change_ratio > 0.3 and author_count > 2:
                # High changes, many authors
                categories["hot"].append((filepath, changes, author_count))
            elif change_ratio < 0.1:
                # Low changes = stable for extraction
                categories["stable"].append((filepath, changes, author_count))
            elif change_ratio > 0.3 and author_count <= 2:
                # High changes, few authors = risky
                categories["volatile"].append((filepath, changes, author_count))

            # Single-owner tracking (orthogonal to above)
            if author_count == 1:
                author = next(iter(file_authors.get(filepath, set())), None)
                categories["single_owner"].append((filepath, changes, author))

        # Sort each category by change count
        for key in categories:
            categories[key].sort(key=lambda x: x[1], reverse=True)

        return categories

    def _get_directory_activity(
        self, file_changes: dict[str, int], top_n: int
    ) -> dict[str, int]:
        """Aggregate change counts by directory."""
        dir_changes: dict[str, int] = defaultdict(int)

        for filepath, count in file_changes.items():
            parts = filepath.split("/")
            if len(parts) > 1:
                # Top-level directory
                dir_changes[parts[0]] += count
                # Second-level if it exists
                if len(parts) > 2:
                    dir_changes[f"{parts[0]}/{parts[1]}"] += count

        # Sort by activity and limit
        sorted_dirs = sorted(dir_changes.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_dirs[:top_n])

    def _get_top_contributors(
        self, ctx: AnalysisContext, days: int, top_n: int
    ) -> list[tuple[str, int]]:
        """Get top contributors by commit count."""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        output = self._run_git(
            ctx,
            [
                "shortlog",
                "-sne",
                f"--since={since_date}",
                "--no-merges",
                "HEAD",
            ],
        )

        if not output:
            return []

        contributors: list[tuple[str, int]] = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Format: "    123  Name <email>"
            parts = line.split("\t", 1)
            if len(parts) == 2:
                try:
                    count = int(parts[0].strip())
                    # Extract just the name, removing email
                    name = parts[1].split("<")[0].strip()
                    contributors.append((name, count))
                except ValueError:
                    continue

        return sorted(contributors, key=lambda x: x[1], reverse=True)[:top_n]

    def _get_coupling(
        self,
        ctx: AnalysisContext,
        days: int,
        threshold: int,
        max_files: int,
        top_n: int,
    ) -> list[tuple[str, str, int]]:
        """Find files that are commonly changed together.

        Uses a sentinel-based format to separate commits, avoiding issues with
        file paths that might contain "COMMIT" as a substring.
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        output = self._run_git(
            ctx,
            [
                "log",
                f"--since={since_date}",
                "--name-only",
                "--pretty=format:%x01COMMIT%x01",  # Use SOH as delimiter
                "--no-merges",
            ],
        )

        if not output:
            return []

        # Group files by commit
        commits: list[list[str]] = []
        current_commit: list[str] = []

        for line in output.split("\n"):
            if line.startswith("\x01COMMIT\x01"):
                if current_commit:
                    commits.append(current_commit)
                current_commit = []
            elif line.strip():
                current_commit.append(line.strip())

        if current_commit:
            commits.append(current_commit)

        # Count co-occurrences
        from itertools import combinations

        coupling: dict[tuple[str, str], int] = defaultdict(int)

        for commit_files in commits:
            # Skip huge commits (noise) and single-file commits
            if 2 <= len(commit_files) <= max_files:
                for f1, f2 in combinations(sorted(commit_files), 2):
                    coupling[(f1, f2)] += 1

        # Filter by threshold and sort
        coupled = [
            (f1, f2, count)
            for (f1, f2), count in coupling.items()
            if count >= threshold
        ]
        coupled.sort(key=lambda x: x[2], reverse=True)

        return coupled[:top_n]

    def _get_recent_commits(
        self, ctx: AnalysisContext, top_n: int
    ) -> list[dict[str, str]]:
        """Get recent commits with metadata."""
        output = self._run_git(
            ctx,
            [
                "log",
                f"-{top_n}",
                "--pretty=format:%H%x01%ae%x01%ad%x01%s",
                "--date=short",
                "--no-merges",
            ],
        )

        if not output:
            return []

        commits: list[dict[str, str]] = []
        for line in output.strip().split("\n"):
            parts = line.split("\x01")
            if len(parts) >= 4:
                commit_hash = parts[0][:8]
                author = parts[1].split("@")[0]  # Use local part only
                date = parts[2]
                message = parts[3][:60]
                commits.append(
                    {
                        "hash": commit_hash,
                        "author": author,
                        "date": date,
                        "message": message,
                    }
                )

        return commits
