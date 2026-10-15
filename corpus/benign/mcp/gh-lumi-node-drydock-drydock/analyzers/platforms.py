"""Detect programming platforms and their versions in projects.

Based on Microsoft Oryx detection patterns. Scans for marker files to identify
which development platforms (Node, Python, .NET, etc.) a project uses, including
both root-level and nested platform declarations in monorepos.

Key improvements over pre-0.2:
- Detects platforms at root AND in nested directories (fixes monorepo blind spot)
- Honors exclude_dirs configuration (was ignored before)
- Implements conditional detection (e.g., Hugo requires [module] or theme)
- Meaningful confidence levels: high = primary marker, medium = secondary, low = weak
- TypeScript reported as separate platform (facet discussion deferred to docs)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..core.registry import AnalysisContext, Option
from ..core.toml import load_toml

__all__ = ["PlatformsAnalyzer"]

@dataclass(frozen=True, slots=True)
class _PlatformDetection:
    """One platform detection result."""

    platform: str
    confidence: str  # high, medium, low
    markers: list[str]  # marker files found
    version: str | None = None
    version_source: str | None = None
    path: str = "."  # relative path where detected (. for root)
    depth: int = 0  # nesting depth from root


class PlatformsAnalyzer:
    """Detect programming platforms and versions in a codebase."""

    name = "platforms"
    summary = "Detect programming platforms and versions"
    description = (
        "Scans the project directory structure to identify which development "
        "platforms (Node.js, Python, .NET, Java, Ruby, PHP, Go, Rust, Hugo) are "
        "in use. Searches both the project root and nested directories up to "
        "max_depth for platform markers (package.json, pyproject.toml, etc.). "
        "Reports detection confidence, marker files found, and extracted version "
        "constraints when available."
    )

    options = (
        Option(
            name="max_depth",
            type=int,
            default=3,
            help="Maximum nesting depth to search for platforms",
        ),
    )

    # Platform marker configurations (based on Oryx)
    _PLATFORM_CONFIG = {
        "nodejs": {
            "marker_files": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
            ],
            "version_markers": {
                ".nvmrc": ("file_content", None),
                ".node-version": ("file_content", None),
                "package.json": ("json", "engines.node"),
            },
            "exclude_dirs": ["node_modules"],
            "marker_confidence": {
                "package.json": "high",
                "package-lock.json": "high",
                "yarn.lock": "high",
                "pnpm-lock.yaml": "high",
            },
        },
        "python": {
            "marker_files": [
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "requirements.txt",
                "Pipfile",
                "conda.yaml",
                "environment.yml",
            ],
            "version_markers": {
                "runtime.txt": ("file_content", None),
                ".python-version": ("file_content", None),
                "pyproject.toml": ("toml", "project.requires-python"),
            },
            "exclude_dirs": ["__pycache__", "venv", ".venv", "env", ".env"],
            "marker_confidence": {
                "pyproject.toml": "high",
                "setup.py": "high",
                "requirements.txt": "medium",
            },
        },
        "dotnet": {
            "marker_files": [
                "*.csproj",
                "*.fsproj",
                "*.vbproj",
                "*.sln",
            ],
            "version_markers": {
                "global.json": ("json", "sdk.version"),
            },
            "exclude_dirs": ["bin", "obj"],
            "marker_confidence": {
                "*.csproj": "high",
                "*.sln": "high",
            },
        },
        "java": {
            "marker_files": [
                "pom.xml",
                "build.gradle",
                "build.gradle.kts",
            ],
            "version_markers": {
                ".java-version": ("file_content", None),
            },
            "exclude_dirs": ["target", "build", ".gradle"],
            "marker_confidence": {
                "pom.xml": "high",
                "build.gradle": "high",
            },
        },
        "ruby": {
            "marker_files": [
                "Gemfile",
                "*.gemspec",
            ],
            "version_markers": {
                ".ruby-version": ("file_content", None),
            },
            "exclude_dirs": ["vendor"],
            "marker_confidence": {
                "Gemfile": "high",
            },
        },
        "php": {
            "marker_files": [
                "composer.json",
                "composer.lock",
            ],
            "version_markers": {
                "composer.json": ("json", "require.php"),
            },
            "exclude_dirs": ["vendor"],
            "marker_confidence": {
                "composer.json": "high",
            },
        },
        "go": {
            "marker_files": [
                "go.mod",
                "go.sum",
            ],
            "version_markers": {
                "go.mod": ("file_content", None),
            },
            "exclude_dirs": [],
            "marker_confidence": {
                "go.mod": "high",
            },
        },
        "rust": {
            "marker_files": [
                "Cargo.toml",
                "Cargo.lock",
            ],
            "version_markers": {
                "rust-toolchain": ("file_content", None),
                "rust-toolchain.toml": ("toml", "toolchain.channel"),
            },
            "exclude_dirs": ["target"],
            "marker_confidence": {
                "Cargo.toml": "high",
            },
        },
        "hugo": {
            "marker_files": [
                "hugo.toml",
                "hugo.yaml",
                "hugo.json",
                "config.toml",
            ],
            "version_markers": {},
            "exclude_dirs": ["public", "resources"],
            "marker_confidence": {
                "hugo.toml": "high",
                "hugo.yaml": "high",
                "hugo.json": "high",
                "config.toml": "low",  # only high if has [module] or theme
            },
            "conditional": "config.toml",  # needs validation
        },
        "typescript": {
            "marker_files": [
                "tsconfig.json",
            ],
            "version_markers": {
                "package.json": ("json", "devDependencies.typescript"),
            },
            "exclude_dirs": ["node_modules", "dist"],
            "marker_confidence": {
                "tsconfig.json": "high",
            },
        },
    }

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Detect platforms in the project."""
        max_depth: int = opts.get("max_depth", 3)

        ctx.reporter.step("Detecting platforms")

        detections = self._scan_for_platforms(ctx.root, max_depth)

        # Sort by path, then by platform name (root first)
        detections.sort(
            key=lambda d: (d.depth, d.path, d.platform)
        )

        # Group by path for the output
        by_path: dict[str, list[_PlatformDetection]] = {}
        for det in detections:
            key = det.path or "."
            if key not in by_path:
                by_path[key] = []
            by_path[key].append(det)

        # Compute summary stats
        unique_platforms = sorted(set(d.platform for d in detections))
        is_multi_platform = len(unique_platforms) > 1

        summary_by_platform = {}
        for plat in unique_platforms:
            plat_dets = [d for d in detections if d.platform == plat]
            summary_by_platform[plat] = {
                "detections": len(plat_dets),
                "markers": sorted(set(m for d in plat_dets for m in d.markers)),
                "versions": [
                    d.version for d in plat_dets if d.version
                ] or None,
                "high_confidence": any(d.confidence == "high" for d in plat_dets),
            }

        ctx.reporter.sub(f"detected {len(unique_platforms)} platform(s)")

        return {
            "summary": {
                "unique_platforms": unique_platforms,
                "is_multi_platform": is_multi_platform,
                "detections_total": len(detections),
                "by_platform": summary_by_platform,
                "max_depth": max_depth,
            },
            "detections": [self._detection_to_dict(d) for d in detections],
            "meta": ctx.meta(),
        }

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render analysis result as markdown."""
        lines = [
            f"# Platform Detection: {result['meta']['project']}",
            "",
            "## Summary",
            "",
        ]

        s = result["summary"]
        if s.get("unique_platforms"):
            lines.append(
                f"**Detected Platforms:** {', '.join(s['unique_platforms'])}"
            )
            lines.append("")

            lines.append("| Platform | Detections | High Confidence | Versions |")
            lines.append("|----------|-----------|-----------------|----------|")

            for plat in s.get("unique_platforms", []):
                bp = s["by_platform"].get(plat, {})
                high = "✓" if bp.get("high_confidence") else "✗"
                versions = (
                    ", ".join(bp["versions"])
                    if bp.get("versions")
                    else "(none detected)"
                )
                lines.append(
                    f"| {plat} | {bp['detections']} | {high} | {versions} |"
                )
            lines.append("")

            if s.get("is_multi_platform"):
                lines.append("**This is a multi-platform project.**")
                lines.append("")
        else:
            lines.append("No platforms detected.")
            lines.append("")

        # Detections by location
        if result.get("detections"):
            lines.extend(["## Detections by Location", ""])

            # Group by path for display
            by_path: dict[str, list[dict[str, Any]]] = {}
            for det in result["detections"]:
                key = det["path"] or "."
                if key not in by_path:
                    by_path[key] = []
                by_path[key].append(det)

            for path in sorted(by_path.keys()):
                dets = by_path[path]
                if path == ".":
                    lines.append("### Root")
                else:
                    lines.append(f"### {path}")
                lines.append("")

                for det in dets:
                    lines.append(f"**{det['platform']}** ({det['confidence']} confidence)")
                    if det.get("version"):
                        lines.append(f"- Version: {det['version']}")
                        if det.get("version_source"):
                            lines.append(f"- From: {det['version_source']}")
                    if det.get("markers"):
                        markers = ", ".join(f"`{m}`" for m in det["markers"])
                        lines.append(f"- Markers: {markers}")
                    lines.append("")

        lines.extend([
            "## Detection Confidence Levels",
            "",
            "- **High:** Primary platform marker (e.g., package.json, pyproject.toml)",
            "- **Medium:** Secondary marker or lock file",
            "- **Low:** Weak marker requiring content validation (e.g., config.toml)",
            "",
        ])

        return "\n".join(lines)

    # ---- implementation ----

    def _scan_for_platforms(
        self, root: Path, max_depth: int
    ) -> list[_PlatformDetection]:
        """Scan for platforms at root and in nested directories."""
        detections: list[_PlatformDetection] = []

        # Check root
        root_dets = self._detect_at_path(root, ".", 0)
        detections.extend(root_dets)

        # Recursively check nested directories up to max_depth
        self._scan_nested(root, "", 1, max_depth, detections)

        return detections

    def _scan_nested(
        self,
        current_path: Path,
        rel_prefix: str,
        depth: int,
        max_depth: int,
        detections: list[_PlatformDetection],
    ) -> None:
        """Recursively scan nested directories."""
        if depth > max_depth:
            return

        try:
            for subdir in current_path.iterdir():
                if not subdir.is_dir():
                    continue
                if subdir.name.startswith("."):
                    continue

                # Build relative path
                if rel_prefix:
                    rel_path = f"{rel_prefix}/{subdir.name}"
                else:
                    rel_path = subdir.name

                # Check this directory for platforms
                nested_dets = self._detect_at_path(subdir, rel_path, depth)
                detections.extend(nested_dets)

                # Recurse deeper
                self._scan_nested(subdir, rel_path, depth + 1, max_depth, detections)
        except (PermissionError, OSError):
            pass

    def _detect_at_path(
        self, path: Path, rel_path: str, depth: int
    ) -> list[_PlatformDetection]:
        """Detect platforms at a specific directory."""
        results: list[_PlatformDetection] = []

        for platform, config in self._PLATFORM_CONFIG.items():
            markers = self._find_markers(path, config["marker_files"])
            if not markers:
                continue

            # Check for conditional markers (e.g., Hugo needs [module] or theme)
            if config.get("conditional") == "config.toml" and platform == "hugo":
                if "config.toml" in markers:
                    if not self._is_hugo_config(path / "config.toml"):
                        # Bare config.toml without Hugo sections, skip
                        markers = [m for m in markers if m != "config.toml"]
                        if not markers:
                            continue

            # Determine confidence level
            confidence = self._compute_confidence(
                markers, config["marker_confidence"]
            )

            # Extract version if available
            version, version_source = self._extract_version(
                path, platform, config["version_markers"]
            )

            results.append(
                _PlatformDetection(
                    platform=platform,
                    confidence=confidence,
                    markers=sorted(markers),
                    version=version,
                    version_source=version_source,
                    path=rel_path,
                    depth=depth,
                )
            )

        return results

    @staticmethod
    def _find_markers(path: Path, marker_patterns: list[str]) -> list[str]:
        """Find marker files matching the given patterns."""
        found = []
        for pattern in marker_patterns:
            if "*" in pattern:
                # Glob pattern
                matches = list(path.glob(pattern))
                found.extend([m.name for m in matches[:1]])  # Just one per pattern
            else:
                # Exact file
                if (path / pattern).exists():
                    found.append(pattern)
        return found

    @staticmethod
    def _compute_confidence(
        markers: list[str], marker_confidence: dict[str, str]
    ) -> str:
        """Compute overall confidence based on markers found."""
        if not markers:
            return "low"

        confidences = [marker_confidence.get(m, "medium") for m in markers]
        if "high" in confidences:
            return "high"
        if "medium" in confidences:
            return "medium"
        return "low"

    @staticmethod
    def _is_hugo_config(config_path: Path) -> bool:
        """Check if a config.toml is actually a Hugo config.

        Hugo configs must have [module] or theme settings.
        """
        if not config_path.exists():
            return False

        try:
            content = config_path.read_text(encoding="utf-8")
            # Check for Hugo-specific sections
            return "[module]" in content or "theme" in content
        except Exception:
            return False

    def _extract_version(
        self,
        path: Path,
        platform: str,
        version_markers: dict[str, tuple[str, str | None]],
    ) -> tuple[str | None, str | None]:
        """Extract version constraint from platform markers."""
        if not version_markers:
            return None, None

        for marker_file, (marker_type, json_path) in version_markers.items():
            marker_path = path / marker_file
            if not marker_path.exists():
                continue

            try:
                if marker_type == "file_content":
                    content = marker_path.read_text(encoding="utf-8").strip()
                    if content:
                        return content, marker_file
                elif marker_type == "json":
                    import json as json_module

                    data = json_module.loads(marker_path.read_text())
                    if json_path:
                        value = self._traverse_dict(data, json_path)
                        if value:
                            return str(value), marker_file
                elif marker_type == "toml":
                    # `load_toml` returns None when no TOML reader is
                    # available -- on 3.10 the module-level guard used to be
                    # `sys.version_info >= (3, 11)`, so an installed `tomli`
                    # went unused and every TOML version marker was skipped.
                    data = load_toml(marker_path)
                    if data is not None and json_path:
                        value = self._traverse_dict(data, json_path)
                        if value:
                            return str(value), marker_file
            except Exception:
                pass

        return None, None

    @staticmethod
    def _traverse_dict(obj: Any, path: str) -> Any:
        """Traverse nested dict/list using dot-separated path."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _detection_to_dict(det: _PlatformDetection) -> dict[str, Any]:
        """Convert detection to JSON-serializable dict."""
        return {
            "platform": det.platform,
            "confidence": det.confidence,
            "markers": det.markers,
            "version": det.version,
            "version_source": det.version_source,
            "path": det.path,
            "depth": det.depth,
        }
